#!/usr/bin/env python3
"""
ベースライン SBOM と PR 生成 SBOM をマージするスクリプト

SKILL-DESIGN.md の「ベースライン SBOM マージルール」に基づき、
Dependency-Track から取得したベースライン SBOM の人手情報を
PR で自動生成した SBOM に引き継ぐ。

使い方:
  python3 merge_baseline_sbom.py <pr-sbom> <baseline-sbom> [options]

オプション:
  --config <path>        .sbom-config.json のパス
  --output-sbom <path>   マージ結果の出力先（デフォルト: pr-sbom を上書き）
  --output-report <path> マージレポート JSON の出力先（デフォルト: merge-report.json）
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from analyze_copyright_holders import load_config


# --- デフォルトルール定義 ---

# (B) PR 優先のコンポーネント属性（それ以外は (A) fallback）
DEFAULT_PR_COMPONENT_ATTRS = {"licenses", "hashes"}

# (B) PR 優先の BOM 属性（それ以外は (A) fallback）
DEFAULT_PR_BOM_ATTRS = {"metadata.component", "metadata.tools", "dependencies"}

# 常に引き継がない属性
NEVER_INHERIT = {"vulnerabilities"}


def normalize_name(name: str) -> str:
    """コンポーネント名を正規化して比較用文字列を返す"""
    s = name.lower()
    s = re.sub(r"[-_\s]+", "", s)
    return s


def strip_purl_version(purl: str) -> str:
    """PURL からバージョン部分を除去して比較用文字列を返す

    例: pkg:generic/cjson@1.7.15 → pkg:generic/cjson
    """
    return re.sub(r"@[^?#]*", "", purl)


def build_rule_table(config: Dict) -> Tuple[Dict[str, str], Dict[str, str]]:
    """merge_overrides から属性ごとのルールテーブルを構築する

    Returns:
        (component_rules, bom_rules) - 各属性名 → "pr" or "baseline"
    """
    component_rules: Dict[str, str] = {}
    bom_rules: Dict[str, str] = {}

    overrides = config.get("merge_overrides", {})
    for attr, value in overrides.get("component_attributes", {}).items():
        if value in ("pr", "baseline"):
            component_rules[attr] = value
    for attr, value in overrides.get("bom_attributes", {}).items():
        if value in ("pr", "baseline"):
            bom_rules[attr] = value

    return component_rules, bom_rules


def get_component_rule(attr: str, component_rules: Dict[str, str]) -> str:
    """コンポーネント属性のマージルールを返す"""
    if attr in component_rules:
        return component_rules[attr]
    if attr in DEFAULT_PR_COMPONENT_ATTRS:
        return "pr"
    return "baseline"


def get_bom_rule(attr: str, bom_rules: Dict[str, str]) -> str:
    """BOM 属性のマージルールを返す"""
    if attr in NEVER_INHERIT:
        return "pr"
    if attr in bom_rules:
        return bom_rules[attr]
    if attr in DEFAULT_PR_BOM_ATTRS:
        return "pr"
    return "baseline"


def is_empty_value(value: Any) -> bool:
    """SBOM 属性値が「空」とみなせるか判定する

    NOASSERTION、空文字列、None、空リスト/辞書 を空とみなす。
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() in ("", "NOASSERTION"):
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def match_components(
    pr_components: List[Dict],
    baseline_components: List[Dict],
    config: Dict
) -> List[Tuple[Dict, Optional[Dict], str]]:
    """PR コンポーネントとベースラインコンポーネントを突合する

    Returns:
        (pr_comp, baseline_comp_or_None, match_method) のリスト
        + ベースラインのみのコンポーネントは含まない（呼び出し元で処理）
    """
    # ベースラインのインデックスを構築
    bl_by_purl: Dict[str, Dict] = {}
    bl_by_name: Dict[str, Dict] = {}
    bl_matched: set = set()

    for i, bl_comp in enumerate(baseline_components):
        purl = bl_comp.get("purl", "")
        if purl:
            bl_by_purl[strip_purl_version(purl)] = (i, bl_comp)
        name = bl_comp.get("name", "")
        if name:
            normalized = normalize_name(name)
            bl_by_name[normalized] = (i, bl_comp)

    # component_overrides から name マッピングを構築（優先度3）
    # パスのベース名（例: "third-party/mbedtls" → "mbedtls"）を正規化して
    # config の canonical name にマッピングする
    config_name_map: Dict[str, str] = {}
    for path, overrides in config.get("component_overrides", {}).items():
        if "name" in overrides:
            base_name = os.path.basename(path.rstrip("/"))
            config_name_map[normalize_name(base_name)] = overrides["name"]

    results: List[Tuple[Dict, Optional[Dict], str]] = []

    for pr_comp in pr_components:
        matched = None
        method = "none"

        # 優先度1: purl 一致
        pr_purl = pr_comp.get("purl", "")
        if pr_purl:
            key = strip_purl_version(pr_purl)
            if key in bl_by_purl:
                idx, bl_comp = bl_by_purl[key]
                if idx not in bl_matched:
                    matched = bl_comp
                    method = "purl"
                    bl_matched.add(idx)

        # 優先度2: name 正規化比較
        if matched is None:
            pr_name = normalize_name(pr_comp.get("name", ""))
            if pr_name and pr_name in bl_by_name:
                idx, bl_comp = bl_by_name[pr_name]
                if idx not in bl_matched:
                    matched = bl_comp
                    method = "name_normalized"
                    bl_matched.add(idx)

        # 優先度3: config の component_overrides 経由
        if matched is None:
            pr_name_norm = normalize_name(pr_comp.get("name", ""))
            if pr_name_norm in config_name_map:
                config_canonical = config_name_map[pr_name_norm]
                bl_key = normalize_name(config_canonical)
                if bl_key in bl_by_name:
                    idx, bl_comp = bl_by_name[bl_key]
                    if idx not in bl_matched:
                        matched = bl_comp
                        method = "config_bridge"
                        bl_matched.add(idx)

        results.append((pr_comp, matched, method))

    return results, bl_matched


def merge_component_attributes(
    pr_comp: Dict,
    bl_comp: Dict,
    component_rules: Dict[str, str]
) -> Tuple[Dict, List[Dict], List[Dict]]:
    """マッチしたコンポーネントの属性をマージする

    Returns:
        (merged_comp, overwritten_list, inherited_list)
    """
    merged = dict(pr_comp)
    overwritten = []
    inherited = []

    # マージ対象の属性一覧
    merge_attrs = [
        "name", "version", "licenses", "purl", "cpe",
        "supplier", "author", "description", "hashes",
        "externalReferences", "properties"
    ]

    for attr in merge_attrs:
        rule = get_component_rule(attr, component_rules)
        pr_val = pr_comp.get(attr)
        bl_val = bl_comp.get(attr)

        if rule == "pr":
            # (B) PR 優先: PR の値を使う。ベースラインと異なる場合は通知
            if not is_empty_value(bl_val) and not is_empty_value(pr_val):
                if pr_val != bl_val:
                    overwritten.append({
                        "attribute": attr,
                        "baseline_value": bl_val,
                        "pr_value": pr_val,
                        "rule": "pr"
                    })
            elif is_empty_value(pr_val) and not is_empty_value(bl_val):
                # PR が空でも (B) なので PR を優先（空のまま）
                # ただし通知はしない（PR が検出しなかっただけ）
                pass
        else:
            # (A) fallback: PR が空の場合のみベースラインから引き継ぐ
            if is_empty_value(pr_val) and not is_empty_value(bl_val):
                merged[attr] = bl_val
                inherited.append({
                    "attribute": attr,
                    "baseline_value": bl_val,
                    "rule": "baseline"
                })

    return merged, overwritten, inherited


def merge_bom_attributes(
    pr_sbom: Dict,
    bl_sbom: Dict,
    bom_rules: Dict[str, str]
) -> Tuple[Dict, List[Dict]]:
    """コンポーネント以外の BOM レベル属性をマージする

    Returns:
        (merged_sbom, bom_changes)
    """
    merged = dict(pr_sbom)
    changes = []

    # metadata 内の属性
    pr_meta = pr_sbom.get("metadata", {})
    bl_meta = bl_sbom.get("metadata", {})

    metadata_attrs = {
        "metadata.component": "component",
        "metadata.tools": "tools",
        "metadata.authors": "authors",
        "metadata.supplier": "supplier",
        "metadata.properties": "properties",
    }

    for attr_path, meta_key in metadata_attrs.items():
        rule = get_bom_rule(attr_path, bom_rules)
        pr_val = pr_meta.get(meta_key)
        bl_val = bl_meta.get(meta_key)

        if rule == "pr":
            if not is_empty_value(bl_val) and not is_empty_value(pr_val) and pr_val != bl_val:
                changes.append({"path": attr_path, "action": "overwritten_by_pr"})
        else:
            if is_empty_value(pr_val) and not is_empty_value(bl_val):
                if "metadata" not in merged:
                    merged["metadata"] = {}
                merged["metadata"][meta_key] = bl_val
                changes.append({"path": attr_path, "action": "inherited_from_baseline"})

    # トップレベル属性
    top_level_attrs = {
        "dependencies": "dependencies",
        "services": "services",
    }

    for attr_path, key in top_level_attrs.items():
        rule = get_bom_rule(attr_path, bom_rules)
        pr_val = pr_sbom.get(key)
        bl_val = bl_sbom.get(key)

        if rule == "pr":
            if not is_empty_value(bl_val) and not is_empty_value(pr_val) and pr_val != bl_val:
                changes.append({"path": attr_path, "action": "overwritten_by_pr"})
        else:
            if is_empty_value(pr_val) and not is_empty_value(bl_val):
                merged[key] = bl_val
                changes.append({"path": attr_path, "action": "inherited_from_baseline"})

    # vulnerabilities は常に引き継がない
    merged.pop("vulnerabilities", None)

    return merged, changes


def merge_sboms(
    pr_sbom: Dict,
    baseline_sbom: Dict,
    config: Dict
) -> Tuple[Dict, Dict]:
    """PR SBOM とベースライン SBOM をマージする

    Returns:
        (merged_sbom, merge_report)
    """
    component_rules, bom_rules = build_rule_table(config)

    pr_components = pr_sbom.get("components", [])
    bl_components = baseline_sbom.get("components", [])

    # コンポーネントマッチング
    match_results, bl_matched_indices = match_components(
        pr_components, bl_components, config
    )

    # マッチ結果の処理
    merged_components = []
    matches_report = []
    new_components = []

    for pr_comp, bl_comp, method in match_results:
        if bl_comp is not None:
            merged_comp, overwritten, inherited = merge_component_attributes(
                pr_comp, bl_comp, component_rules
            )
            merged_components.append(merged_comp)
            matches_report.append({
                "pr_name": pr_comp.get("name", ""),
                "baseline_name": bl_comp.get("name", ""),
                "match_method": method,
                "overwritten_attributes": overwritten,
                "inherited_attributes": inherited,
            })
        else:
            merged_components.append(pr_comp)
            new_components.append(pr_comp.get("name", "unknown"))

    # ベースラインのみのコンポーネント（削除扱い）
    removed_components = []
    for i, bl_comp in enumerate(bl_components):
        if i not in bl_matched_indices:
            removed_components.append(bl_comp.get("name", "unknown"))

    # BOM レベル属性のマージ
    merged_sbom, bom_changes = merge_bom_attributes(pr_sbom, baseline_sbom, bom_rules)
    merged_sbom["components"] = merged_components

    # レポート生成
    report = {
        "summary": {
            "total_baseline": len(bl_components),
            "total_pr": len(pr_components),
            "matched": len(matches_report),
            "new_in_pr": len(new_components),
            "removed_from_baseline": len(removed_components),
        },
        "matches": matches_report,
        "new_components": new_components,
        "removed_components": removed_components,
        "bom_attribute_changes": bom_changes,
    }

    return merged_sbom, report


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ベースライン SBOM と PR SBOM をマージする"
    )
    parser.add_argument("pr_sbom", help="PR 生成 CycloneDX JSON のパス")
    parser.add_argument("baseline_sbom", help="ベースライン CycloneDX JSON のパス")
    parser.add_argument("--config", default=None, help=".sbom-config.json のパス")
    parser.add_argument("--output-sbom", default=None,
                        help="マージ結果の出力先（デフォルト: pr_sbom を上書き）")
    parser.add_argument("--output-report", default="merge-report.json",
                        help="マージレポート JSON の出力先")

    args = parser.parse_args()

    # 入力読み込み
    with open(args.pr_sbom, "r", encoding="utf-8") as f:
        pr_sbom = json.load(f)

    with open(args.baseline_sbom, "r", encoding="utf-8") as f:
        baseline_sbom = json.load(f)

    config = load_config(args.config)

    # ベースラインが空の場合はスキップ
    bl_components = baseline_sbom.get("components", [])
    if not bl_components:
        print("Baseline SBOM has no components. Skipping merge.")
        output_path = args.output_sbom or args.pr_sbom
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(pr_sbom, f, indent=2, ensure_ascii=False)
        report = {
            "summary": {
                "total_baseline": 0,
                "total_pr": len(pr_sbom.get("components", [])),
                "matched": 0,
                "new_in_pr": len(pr_sbom.get("components", [])),
                "removed_from_baseline": 0,
            },
            "matches": [],
            "new_components": [c.get("name", "") for c in pr_sbom.get("components", [])],
            "removed_components": [],
            "bom_attribute_changes": [],
        }
        with open(args.output_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return

    # マージ実行
    merged_sbom, report = merge_sboms(pr_sbom, baseline_sbom, config)

    # 出力
    output_path = args.output_sbom or args.pr_sbom
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_sbom, f, indent=2, ensure_ascii=False)

    with open(args.output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # サマリー表示
    s = report["summary"]
    print(f"Merge complete:")
    print(f"  Baseline: {s['total_baseline']} components")
    print(f"  PR:       {s['total_pr']} components")
    print(f"  Matched:  {s['matched']}")
    print(f"  New:      {s['new_in_pr']}")
    print(f"  Removed:  {s['removed_from_baseline']}")

    overwrite_count = sum(
        len(m["overwritten_attributes"]) for m in report["matches"]
    )
    inherit_count = sum(
        len(m["inherited_attributes"]) for m in report["matches"]
    )
    print(f"  Attributes overwritten by PR: {overwrite_count}")
    print(f"  Attributes inherited from baseline: {inherit_count}")


if __name__ == "__main__":
    main()

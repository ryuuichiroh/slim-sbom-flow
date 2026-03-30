#!/usr/bin/env python3
"""
ScanCode JSON から著作権者を集計・正規化し、主要著作権者を自動判定する

出力:
  - holders-analysis.json: 著作権者ごとの統計、正規化、主要著作権者の判定結果

使い方:
  python3 analyze_copyright_holders.py <scancode-json-pp.json> [options]

オプション:
  --config <path>   .sbom-config.json のパス（著作権者エイリアス等を読み込む）
  --output <path>   出力 JSON のパス（デフォルト: holders-analysis.json）
  --threshold <n>   主要著作権者と判定する閾値（%、デフォルト: 30）
"""

import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# 法人格接尾辞のパターン（正規化時に除去）
LEGAL_SUFFIXES = re.compile(
    r",?\s*("
    r"Co\.,?\s*Ltd\.?|Company,?\s*Ltd\.?|Corp\.?|Corporation|"
    r"Inc\.?|Incorporated|LLC|L\.L\.C\.|LLP|"
    r"Mfg\.?|Manufacturing|"
    r"GmbH|AG|S\.A\.|B\.V\.|N\.V\.|"
    r"Pty\.?\s*Ltd\.?|PLC|plc"
    r")\s*$",
    re.IGNORECASE
)


def normalize_holder(holder: str) -> Optional[str]:
    """
    著作権者名を正規化する

    1. 法人格接尾辞の除去
    2. 余分な空白・記号の除去
    3. 小文字化（比較用）
    """
    if not holder or len(holder) < 2:
        return None

    normalized = LEGAL_SUFFIXES.sub("", holder)
    normalized = normalized.strip().strip(",").strip(".")
    normalized = re.sub(r"\s+", " ", normalized)

    if len(normalized) < 2:
        return None

    return normalized.lower()


def is_likely_false_positive(holder: str) -> bool:
    """
    ScanCode の誤検出（文字化け、変数名等）をフィルタリング
    """
    if not holder:
        return True

    stripped = holder.strip()

    # 極端に短い（2文字以下）
    if len(stripped) <= 2:
        return True

    # 文字化けパターン（非ASCII文字が多い場合は除外しない — 日本語等はOK）
    # ただし意味不明な記号列は除外
    if re.match(r'^[^\w\s]{3,}', stripped):
        return True

    # 非ASCII かつ日本語/中国語/韓国語でない文字化けパターン
    # 1/2, 1/4 等のエンコーディング不良を検出
    if re.search(r'[^\x00-\x7F]', stripped):
        # 日本語・中国語・韓国語の正規文字を含まない場合は文字化けとみなす
        has_cjk = bool(re.search(r'[\u3000-\u9FFF\uF900-\uFAFF]', stripped))
        has_fraction = bool(re.search(r'1/[24]|a\?|e\?|a\(r\)', stripped))
        if has_fraction and not has_cjk:
            return True

    # エンコーディング不良のASCIIテキスト検出
    # ScanCode が Shift-JIS や EUC-JP を誤デコードすると、1文字のアルファベットと
    # 記号（?, |, ", (, )）が交互に並ぶパターンになる
    # 例: e"a(r)a?a1/4a?e, e?1/2ae|e|? P2P Group
    if re.search(r'(?:[a-z][\?\|"()\[\]]{1,2}){2,}', stripped, re.IGNORECASE):
        return True
    # 分数パターンが文字列の一部に混在（例: a1/4a, 1/2ae）
    if re.search(r'[a-z]1/[234][a-z]', stripped, re.IGNORECASE):
        return True
    if re.search(r'1/[234][a-z]{1,2}[|?\"]', stripped, re.IGNORECASE):
        return True

    # C言語の型名・変数名パターン
    c_keywords = {"ULONG", "UINT", "CHAR", "VOID", "INT", "LONG", "SHORT", "BYTE",
                  "UCHAR", "USHORT", "DWORD", "WORD", "BOOL", "TRUE", "FALSE"}
    if stripped in c_keywords:
        return True

    # "U-2019" パターン（Unicode の Right Single Quotation Mark の誤パース）
    if re.match(r'^U-[0-9]{4}\b', stripped):
        return True

    return False


def load_config(config_path: Optional[str]) -> Dict:
    """
    .sbom-config.json を読み込む（存在すれば）
    """
    if config_path and os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def apply_aliases(holder: str, aliases: Dict[str, List[str]]) -> str:
    """
    著作権者名のエイリアスを適用して正規名に変換する
    """
    for canonical, alias_list in aliases.items():
        if holder == canonical:
            return canonical
        for alias in alias_list:
            if holder.lower() == alias.lower():
                return canonical
    return holder


def analyze_holders(
    scan_data: Dict,
    config: Dict,
    threshold: float = 30.0
) -> Dict:
    """
    ScanCode の files 配列から著作権者を集計・分析する

    Returns:
        {
            "primary_holder": "Ricoh Co., Ltd." or null,
            "primary_holder_percentage": 45.2,
            "total_files": 384,
            "files_with_copyright": 271,
            "files_without_copyright": 113,
            "holders": [
                {
                    "canonical_name": "Express Logic Inc.",
                    "variants": ["Express Logic Inc.", "Express Logic, Inc."],
                    "file_count": 215,
                    "percentage": 56.0,
                    "directories": {"base": 215},
                    "is_primary": false
                },
                ...
            ],
            "false_positives": [...],
            "config_overrides_applied": true/false
        }
    """
    aliases = config.get("copyright_holder_aliases", {})
    deps_dirs = config.get("deps_directories", [
        "deps/", "third_party/", "vendor/", "external/"
    ])
    config_primary = config.get("primary_copyright_holder")

    # 著作権者の集計
    holder_data = defaultdict(lambda: {
        "variants": defaultdict(int),
        "files": [],
        "directories": defaultdict(int)
    })
    false_positives = []
    total_files = 0
    files_without_copyright = 0

    for file_obj in scan_data.get("files", []):
        if file_obj.get("type") != "file":
            continue

        total_files += 1
        path = file_obj.get("path", "")
        top_dir = path.split("/")[0] if "/" in path else "root"
        holders = file_obj.get("holders", [])

        if not holders:
            files_without_copyright += 1
            continue

        for h in holders:
            raw_holder = h.get("holder", "")
            if not raw_holder:
                continue

            if is_likely_false_positive(raw_holder):
                false_positives.append({"holder": raw_holder, "file": path})
                continue

            # エイリアス適用
            resolved = apply_aliases(raw_holder, aliases)
            norm = normalize_holder(resolved)
            if not norm:
                continue

            holder_data[norm]["variants"][resolved] += 1
            holder_data[norm]["files"].append(path)
            holder_data[norm]["directories"][top_dir] += 1

    # deps ディレクトリを除外した集計（主要著作権者判定用）
    holder_non_deps = defaultdict(int)
    non_deps_total = 0

    for file_obj in scan_data.get("files", []):
        if file_obj.get("type") != "file":
            continue

        path = file_obj.get("path", "")
        in_deps = any(path.startswith(d.rstrip("/")) for d in deps_dirs)
        if in_deps:
            continue

        non_deps_total += 1
        holders = file_obj.get("holders", [])
        for h in holders:
            raw_holder = h.get("holder", "")
            if not raw_holder or is_likely_false_positive(raw_holder):
                continue
            resolved = apply_aliases(raw_holder, aliases)
            norm = normalize_holder(resolved)
            if norm:
                holder_non_deps[norm] += 1

    # 結果の整形
    holders_list = []
    for norm, data in sorted(holder_data.items(), key=lambda x: len(x[1]["files"]), reverse=True):
        most_common_raw = max(data["variants"].items(), key=lambda x: x[1])[0]
        file_count = len(data["files"])
        pct = (file_count / total_files * 100) if total_files > 0 else 0

        holders_list.append({
            "canonical_name": most_common_raw,
            "normalized": norm,
            "variants": list(data["variants"].keys()),
            "file_count": file_count,
            "percentage": round(pct, 1),
            "directories": dict(data["directories"]),
            "is_primary": False  # 後で設定
        })

    # 主要著作権者の判定
    primary_holder = None
    primary_pct = 0.0

    if config_primary:
        # config 指定がある場合はそれを使用
        primary_holder = config_primary
        for h in holders_list:
            if h["canonical_name"] == config_primary or h["normalized"] == normalize_holder(config_primary):
                h["is_primary"] = True
                primary_pct = h["percentage"]
                break
    else:
        # deps 除外後の集計で閾値以上を検索
        if non_deps_total > 0:
            for norm, count in sorted(holder_non_deps.items(), key=lambda x: x[1], reverse=True):
                pct = count / non_deps_total * 100
                if pct >= threshold:
                    for h in holders_list:
                        if h["normalized"] == norm:
                            primary_holder = h["canonical_name"]
                            primary_pct = round(pct, 1)
                            h["is_primary"] = True
                            break
                    break

    return {
        "primary_holder": primary_holder,
        "primary_holder_percentage": primary_pct,
        "threshold_used": threshold,
        "total_files": total_files,
        "files_with_copyright": total_files - files_without_copyright,
        "files_without_copyright": files_without_copyright,
        "holders": holders_list,
        "false_positives": false_positives,
        "config_overrides_applied": bool(config_primary or aliases)
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ScanCode JSON から著作権者を集計・分析する"
    )
    parser.add_argument("scancode_json", help="scancode-json-pp.json のパス")
    parser.add_argument("--config", help=".sbom-config.json のパス", default=None)
    parser.add_argument("--output", help="出力 JSON のパス", default="holders-analysis.json")
    parser.add_argument("--threshold", type=float, default=30.0,
                        help="主要著作権者の閾値（%%、デフォルト: 30）")

    args = parser.parse_args()

    # 入力ファイルの読み込み
    with open(args.scancode_json, "r", encoding="utf-8") as f:
        scan_data = json.load(f)

    config = load_config(args.config)

    # 分析の実行
    result = analyze_holders(scan_data, config, args.threshold)

    # 出力
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # サマリー表示
    print(f"✓ Copyright holder analysis complete: {output_path}")
    print(f"\n  Total files: {result['total_files']}")
    print(f"  Files with copyright: {result['files_with_copyright']}")
    print(f"  Files without copyright: {result['files_without_copyright']}")
    print(f"\n  Primary holder: {result['primary_holder'] or 'UNDETERMINED'}"
          f" ({result['primary_holder_percentage']:.1f}%)")
    print(f"\n  Holders detected: {len(result['holders'])}")
    for h in result["holders"][:10]:
        marker = " ★" if h["is_primary"] else ""
        print(f"    - {h['canonical_name']}: {h['file_count']} files ({h['percentage']}%){marker}")

    if result["false_positives"]:
        print(f"\n  False positives filtered: {len(result['false_positives'])}")


if __name__ == "__main__":
    main()

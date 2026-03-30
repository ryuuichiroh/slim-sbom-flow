#!/usr/bin/env python3
"""
SPDX 2.3 + CycloneDX 1.5 + 分析レポートを一括生成するスクリプト

Claude が作成した components.json を入力として受け取り、
SPDX / CycloneDX / Markdown レポートを生成する。

使い方:
  python3 generate_sbom.py <scancode-json-pp.json> --components <components.json> [options]

オプション:
  --components <path>  components.json のパス（必須）
  --config <path>      .sbom-config.json のパス
  --format <f>         出力形式: spdx, cyclonedx, both（デフォルト: both）
  --output-dir <path>  出力ディレクトリ（デフォルト: カレント）
  --no-report          分析レポートを生成しない
"""

import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

# 同ディレクトリの関連モジュールをインポート
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from analyze_copyright_holders import load_config


def generate_spdx(
    root_component: Dict,
    components: Dict,
    config: Dict,
    creation_date: str
) -> Dict:
    """SPDX 2.3 JSON を生成する"""
    doc_uuid = str(uuid.uuid4())
    project_name = root_component.get("name", "Unknown")

    spdx = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{project_name} SBOM",
        "documentNamespace": f"https://spdx.org/spdxdocs/{project_name}-{doc_uuid}",
        "creationInfo": {
            "created": creation_date,
            "creators": [
                "Tool: ScanCode-Toolkit",
                "Tool: sbom-master"
            ],
            "licenseListVersion": "3.27"
        },
        "packages": [],
        "relationships": [],
        "hasExtractedLicensingInfos": []
    }

    # ルートパッケージ
    root_spdx_id = "SPDXRef-Package-Root"
    root_pkg = {
        "SPDXID": root_spdx_id,
        "name": root_component["name"],
        "versionInfo": root_component.get("version", "NOASSERTION"),
        "supplier": root_component.get("supplier", "NOASSERTION"),
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "licenseConcluded": root_component.get("license", "NOASSERTION"),
        "licenseDeclared": root_component.get("license", "NOASSERTION"),
        "copyrightText": root_component.get("copyright", "NOASSERTION"),
    }
    if root_component.get("description"):
        root_pkg["description"] = root_component["description"]
    spdx["packages"].append(root_pkg)

    # DESCRIBES relationship
    spdx["relationships"].append({
        "spdxElementId": "SPDXRef-DOCUMENT",
        "relationshipType": "DESCRIBES",
        "relatedSpdxElement": root_spdx_id
    })

    # 子コンポーネント
    license_refs_seen = set()
    for comp_id, comp in components.items():
        safe_id = re.sub(r"[^a-zA-Z0-9._-]", "-", comp_id)
        spdx_id = f"SPDXRef-Package-{safe_id}"

        pkg = {
            "SPDXID": spdx_id,
            "name": comp["name"],
            "versionInfo": comp.get("version", "NOASSERTION"),
            "supplier": comp.get("supplier", "NOASSERTION"),
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": comp.get("license", "NOASSERTION"),
            "licenseDeclared": comp.get("license", "NOASSERTION"),
            "copyrightText": comp.get("copyright", "NOASSERTION"),
        }

        # externalRefs (PURL)
        purl = comp.get("purl")
        if purl:
            pkg["externalRefs"] = [{
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": purl
            }]

        spdx["packages"].append(pkg)

        # CONTAINS relationship
        spdx["relationships"].append({
            "spdxElementId": root_spdx_id,
            "relationshipType": "CONTAINS",
            "relatedSpdxElement": spdx_id
        })

        # LicenseRef 収集
        lic = comp.get("license", "")
        if lic.startswith("LicenseRef-") and lic not in license_refs_seen:
            license_refs_seen.add(lic)
            spdx["hasExtractedLicensingInfos"].append({
                "licenseId": lic,
                "extractedText": f"Proprietary license. See {comp['name']} license agreement.",
                "name": f"{comp['name']} License"
            })

    # ルートの LicenseRef
    root_lic = root_component.get("license", "")
    if root_lic.startswith("LicenseRef-") and root_lic not in license_refs_seen:
        spdx["hasExtractedLicensingInfos"].append({
            "licenseId": root_lic,
            "extractedText": f"Proprietary license. See {root_component['name']} license agreement.",
            "name": f"{root_component['name']} License"
        })

    if not spdx["hasExtractedLicensingInfos"]:
        del spdx["hasExtractedLicensingInfos"]

    return spdx


def generate_cyclonedx(
    root_component: Dict,
    components: Dict,
    config: Dict,
    creation_date: str
) -> Dict:
    """CycloneDX 1.5 JSON を生成する"""
    bom_uuid = str(uuid.uuid4())

    # ルートコンポーネントのタイプをマッピング
    type_map = {"firmware": "firmware", "application": "application", "library": "library"}
    root_type = type_map.get(root_component.get("type", ""), "application")

    cdx = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{bom_uuid}",
        "version": 1,
        "metadata": {
            "timestamp": creation_date,
            "tools": [
                {"vendor": "nexB Inc.", "name": "ScanCode Toolkit"},
                {"name": "sbom-master"}
            ],
            "component": {
                "type": root_type,
                "bom-ref": "root-component",
                "name": root_component["name"],
            }
        },
        "components": [],
        "dependencies": []
    }

    # ルートにオプションフィールドを追加
    root_meta = cdx["metadata"]["component"]
    if root_component.get("version") and root_component["version"] != "NOASSERTION":
        root_meta["version"] = root_component["version"]
    if root_component.get("supplier") and root_component["supplier"] != "NOASSERTION":
        supplier_name = root_component["supplier"].replace("Organization: ", "")
        root_meta["supplier"] = {"name": supplier_name}
    if root_component.get("license") and root_component["license"] != "NOASSERTION":
        root_meta["licenses"] = [{"expression": root_component["license"]}]
    if root_component.get("copyright") and root_component["copyright"] != "NOASSERTION":
        root_meta["copyright"] = root_component["copyright"]

    # 子コンポーネント
    dep_refs = []
    for comp_id, comp in components.items():
        safe_ref = re.sub(r"[^a-zA-Z0-9._-]", "-", comp_id).lower()

        cdx_comp = {
            "bom-ref": safe_ref,
            "type": comp.get("type", "library"),
            "name": comp["name"],
        }

        if comp.get("version") and comp["version"] != "NOASSERTION":
            cdx_comp["version"] = comp["version"]
        if comp.get("supplier") and comp["supplier"] != "NOASSERTION":
            supplier_name = comp["supplier"].replace("Organization: ", "")
            cdx_comp["supplier"] = {"name": supplier_name}
        if comp.get("license") and comp["license"] != "NOASSERTION":
            # SPDX 標準 ID の場合は id を使用、LicenseRef は expression
            lic = comp["license"]
            if lic.startswith("LicenseRef-"):
                cdx_comp["licenses"] = [{"expression": lic}]
            else:
                cdx_comp["licenses"] = [{"license": {"id": lic}}]
        if comp.get("copyright") and comp["copyright"] != "NOASSERTION":
            cdx_comp["copyright"] = comp["copyright"]
        if comp.get("author"):
            cdx_comp["author"] = comp["author"]
        if comp.get("description"):
            cdx_comp["description"] = comp["description"]
        if comp.get("purl"):
            cdx_comp["purl"] = comp["purl"]
        if comp.get("cpe"):
            cdx_comp["cpe"] = comp["cpe"]
        if comp.get("externalReferences"):
            cdx_comp["externalReferences"] = comp["externalReferences"]
        if comp.get("properties"):
            cdx_comp["properties"] = comp["properties"]

        cdx["components"].append(cdx_comp)
        dep_refs.append(safe_ref)

    # dependencies
    cdx["dependencies"] = [
        {"ref": "root-component", "dependsOn": dep_refs}
    ]
    for ref in dep_refs:
        cdx["dependencies"].append({"ref": ref, "dependsOn": []})

    # compositions
    completeness = config.get("sbom_completeness", "unknown")
    comp_note = config.get("completeness_note", "")
    aggregate_map = {
        "complete": "complete",
        "incomplete": "incomplete",
        "unknown": "unknown"
    }
    cdx["compositions"] = [{
        "aggregate": aggregate_map.get(completeness, "unknown"),
        "assemblies": ["root-component"] + dep_refs
    }]

    return cdx


def generate_report(
    root_component: Dict,
    components: Dict,
    holders_analysis: Dict,
    comp_result: Dict,
    config: Dict
) -> str:
    """Markdown 形式の分析レポートを生成する"""
    lines = []
    lines.append("=" * 80)
    lines.append("  SBOM GENERATION REPORT")
    lines.append(f"  {root_component['name']}")
    lines.append("=" * 80)
    lines.append("")

    # 1. 著作権者の統計
    lines.append("## 1. 著作権者の統計")
    lines.append("")
    lines.append("| 著作権者 | ファイル数 | 割合 |")
    lines.append("|---------|-----------|------|")
    for h in holders_analysis.get("holders", [])[:10]:
        marker = " ★" if h.get("is_primary") else ""
        lines.append(f"| {h['canonical_name']}{marker} | {h['file_count']} | {h['percentage']}% |")
    no_cr = holders_analysis.get("files_without_copyright", 0)
    total = holders_analysis.get("total_files", 1)
    no_cr_pct = round(no_cr / total * 100, 1) if total > 0 else 0
    lines.append(f"| （著作権表示なし） | {no_cr} | {no_cr_pct}% |")
    lines.append("")
    primary = holders_analysis.get("primary_holder", "UNDETERMINED")
    lines.append(f"**主要著作権者**: {primary} ({holders_analysis.get('primary_holder_percentage', 0)}%)")
    lines.append("")

    # 2. コンポーネント一覧
    lines.append("## 2. 検出されたコンポーネント")
    lines.append("")
    lines.append("| コンポーネント | バージョン | ライセンス | サプライヤー | ファイル数 | 検出方法 |")
    lines.append("|--------------|----------|-----------|------------|-----------|---------|")
    lines.append(f"| **{root_component['name']}** (root) | {root_component.get('version', 'N/A')} | "
                 f"{root_component.get('license', 'N/A')} | {root_component.get('supplier', 'N/A')} | "
                 f"{root_component.get('file_count', 0)} | root |")
    for comp_id, comp in sorted(components.items()):
        lines.append(f"| {comp['name']} | {comp.get('version', 'N/A')} | "
                     f"{comp.get('license', 'N/A')} | {comp.get('supplier', 'N/A')} | "
                     f"{comp.get('file_count', 0)} | {comp.get('detection_method', 'N/A')} |")
    lines.append("")

    # 3. 信頼度の低い項目
    lines.append("## 3. 信頼度の低い項目（手動確認推奨）")
    lines.append("")
    noassert_items = []
    for comp_id, comp in components.items():
        issues = []
        if comp.get("version") == "NOASSERTION":
            issues.append("バージョン不明")
        if comp.get("license") == "NOASSERTION":
            issues.append("ライセンス不明")
        if comp.get("supplier") == "NOASSERTION":
            issues.append("サプライヤー不明")
        if issues:
            noassert_items.append(f"- **{comp['name']}**: {', '.join(issues)}")
    if noassert_items:
        for item in noassert_items:
            lines.append(item)
    else:
        lines.append("すべてのコンポーネントの情報が揃っています。")
    lines.append("")

    # 4. 除外ファイル（file_count を合算して算出）
    total_in = (
        sum(c.get("file_count", 0) for c in components.values())
        + root_component.get("file_count", 0)
    )
    total_scanned = comp_result.get("total_scanned", total_in)
    excluded = total_scanned - total_in
    lines.append("## 4. 除外ファイルの概要")
    lines.append("")
    lines.append(f"- スキャン対象: **{total_scanned} ファイル**")
    lines.append(f"- SBOM に含まれる: **{total_in} ファイル**")
    lines.append(f"- 除外された: **{excluded} ファイル**")
    lines.append("")

    # 5. 著作権表示なしファイル
    if no_cr > 0:
        lines.append("## 5. 著作権表示のないファイル")
        lines.append("")
        lines.append(f"**{no_cr} ファイル ({no_cr_pct}%)** に著作権表示がありません。")
        lines.append("推奨対応: ソースファイルに著作権ヘッダーを追加してください。")
        lines.append("")

    # 6. 完全性
    lines.append("## 6. 完全性表明")
    lines.append("")
    completeness = config.get("sbom_completeness", "unknown")
    note = config.get("completeness_note", "")
    lines.append(f"**CycloneDX `compositions.aggregate`**: `{completeness}`")
    if note:
        lines.append(f"補足: {note}")
    lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SPDX 2.3 + CycloneDX 1.5 + レポートを一括生成する"
    )
    parser.add_argument("scancode_json", help="scancode-json-pp.json のパス")
    parser.add_argument("--components", required=True, help="components.json のパス（Claude が生成）")
    parser.add_argument("--config", default=None, help=".sbom-config.json のパス")
    parser.add_argument("--format", choices=["spdx", "cyclonedx", "both"],
                        default="both", help="出力形式（デフォルト: both）")
    parser.add_argument("--output-dir", default=".", help="出力ディレクトリ")
    parser.add_argument("--no-report", action="store_true", help="レポートを生成しない")

    args = parser.parse_args()

    # 入力の読み込み
    config = load_config(args.config)

    with open(args.components, "r", encoding="utf-8") as f:
        comp_result = json.load(f)

    root_component = comp_result["root_component"]
    components = comp_result["components"]
    creation_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    os.makedirs(args.output_dir, exist_ok=True)

    # Step 1: SBOM 生成
    print("[1/2] Generating SBOM files...")
    generated = []

    if args.format in ("spdx", "both"):
        spdx = generate_spdx(root_component, components, config, creation_date)
        spdx_path = os.path.join(args.output_dir, "sbom-spdx.json")
        with open(spdx_path, "w", encoding="utf-8") as f:
            json.dump(spdx, f, indent=2, ensure_ascii=False)
        generated.append(f"sbom-spdx.json ({os.path.getsize(spdx_path)} bytes)")

    if args.format in ("cyclonedx", "both"):
        cdx = generate_cyclonedx(root_component, components, config, creation_date)
        cdx_path = os.path.join(args.output_dir, "sbom-cyclonedx.json")
        with open(cdx_path, "w", encoding="utf-8") as f:
            json.dump(cdx, f, indent=2, ensure_ascii=False)
        generated.append(f"sbom-cyclonedx.json ({os.path.getsize(cdx_path)} bytes)")

    # Step 2: レポート生成
    if not args.no_report:
        # holders-analysis.json があれば読み込む（レポート用）
        holders_result = comp_result.get("holders_analysis", {
            "holders": [], "total_files": 0, "files_without_copyright": 0,
            "primary_holder": root_component.get("supplier", "NOASSERTION").replace("Organization: ", ""),
            "primary_holder_percentage": 0
        })
        print("[2/2] Generating analysis report...")
        report = generate_report(root_component, components, holders_result, comp_result, config)
        report_path = os.path.join(args.output_dir, "sbom-analysis-report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        generated.append(f"sbom-analysis-report.md ({os.path.getsize(report_path)} bytes)")
    else:
        print("[2/2] Report generation skipped.")

    # 完了メッセージ
    print(f"\n✓ SBOM generation complete!")
    print(f"\nGenerated files:")
    for g in generated:
        print(f"  - {g}")

    print(f"\nRoot: {root_component['name']} ({root_component.get('version', 'N/A')})")
    print(f"Components: {len(components)}")
    for comp_id, comp in sorted(components.items()):
        print(f"  - {comp['name']} ({comp.get('version', 'N/A')})")


if __name__ == "__main__":
    main()

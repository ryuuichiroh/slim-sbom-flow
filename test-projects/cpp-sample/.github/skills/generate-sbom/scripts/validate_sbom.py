#!/usr/bin/env python3
"""
生成された SBOM ファイルを検証する

検証項目:
1. JSON の構文チェック
2. 形式の自動判定（SPDX / CycloneDX）
3. 必須フィールドの存在チェック
4. SPDXID / bom-ref の一意性チェック
5. リレーションシップの整合性チェック
6. ライセンス ID の妥当性チェック（既知の SPDX ID かどうか）

使い方:
  python3 validate_sbom.py <sbom-file.json> [options]

オプション:
  --format <auto|spdx|cyclonedx>  形式を指定（デフォルト: auto）
  --strict                         警告もエラーとして扱う
"""

import json
import re
import sys
from typing import Dict, List, Tuple


# よく使われる SPDX ライセンス識別子（抜粋）
KNOWN_SPDX_LICENSES = {
    "MIT", "Apache-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
    "GPL-3.0-only", "GPL-3.0-or-later", "LGPL-2.1-only", "LGPL-2.1-or-later",
    "LGPL-3.0-only", "LGPL-3.0-or-later", "BSD-2-Clause", "BSD-3-Clause",
    "BSD-4-Clause", "BSD-4-Clause-UC", "ISC", "MPL-2.0", "CDDL-1.0",
    "EPL-2.0", "Unlicense", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0",
    "Zlib", "BSL-1.0", "PostgreSQL", "NOASSERTION", "NONE"
}


class ValidationResult:
    """検証結果を格納するクラス"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def add_info(self, msg: str):
        self.info.append(msg)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self, strict: bool = False) -> str:
        lines = []
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARN:  {w}")
        for i in self.info:
            lines.append(f"  INFO:  {i}")

        total_issues = len(self.errors) + (len(self.warnings) if strict else 0)
        if total_issues == 0:
            lines.append("\n  ✓ Validation PASSED")
        else:
            lines.append(f"\n  ✗ Validation FAILED ({len(self.errors)} errors, {len(self.warnings)} warnings)")

        return "\n".join(lines)


def detect_format(data: Dict) -> str:
    """SBOM の形式を自動判定する"""
    if "spdxVersion" in data:
        return "spdx"
    if "bomFormat" in data and data["bomFormat"] == "CycloneDX":
        return "cyclonedx"
    return "unknown"


def is_valid_license_id(license_id: str) -> bool:
    """ライセンス ID が既知のものか LicenseRef- 形式か"""
    if not license_id:
        return False
    if license_id in KNOWN_SPDX_LICENSES:
        return True
    if license_id.startswith("LicenseRef-"):
        return True
    # SPDX 式（AND, OR, WITH を含む場合）
    if any(op in license_id for op in [" AND ", " OR ", " WITH "]):
        parts = re.split(r"\s+(?:AND|OR|WITH)\s+", license_id)
        return all(is_valid_license_id(p.strip("()")) for p in parts)
    return False


def validate_spdx(data: Dict, result: ValidationResult):
    """SPDX 2.3 の検証"""

    # spdxVersion
    version = data.get("spdxVersion")
    if not version:
        result.error("Missing required field: spdxVersion")
    elif version != "SPDX-2.3":
        result.warn(f"spdxVersion is '{version}', expected 'SPDX-2.3'")
    else:
        result.add_info(f"SPDX version: {version}")

    # dataLicense
    dl = data.get("dataLicense")
    if dl != "CC0-1.0":
        result.error(f"dataLicense must be 'CC0-1.0', got '{dl}'")

    # SPDXID
    doc_id = data.get("SPDXID")
    if doc_id != "SPDXRef-DOCUMENT":
        result.error(f"Document SPDXID must be 'SPDXRef-DOCUMENT', got '{doc_id}'")

    # name
    if not data.get("name"):
        result.error("Missing required field: name")

    # documentNamespace
    ns = data.get("documentNamespace", "")
    if not ns:
        result.error("Missing required field: documentNamespace")
    elif not ns.startswith("https://"):
        result.warn(f"documentNamespace should start with 'https://', got '{ns[:50]}'")

    # creationInfo
    ci = data.get("creationInfo", {})
    if not ci.get("created"):
        result.error("Missing creationInfo.created")
    if not ci.get("creators"):
        result.error("Missing creationInfo.creators")

    # packages
    packages = data.get("packages", [])
    if not packages:
        result.error("No packages found")

    spdx_ids = set()
    for i, pkg in enumerate(packages):
        pkg_id = pkg.get("SPDXID", "")
        if not pkg_id:
            result.error(f"Package [{i}] missing SPDXID")
        elif not pkg_id.startswith("SPDXRef-"):
            result.error(f"Package [{i}] SPDXID must start with 'SPDXRef-': {pkg_id}")
        elif not re.match(r'^SPDXRef-[a-zA-Z0-9._-]+$', pkg_id):
            result.error(f"Package [{i}] SPDXID contains invalid characters: {pkg_id}")
        elif pkg_id in spdx_ids:
            result.error(f"Duplicate SPDXID: {pkg_id}")
        else:
            spdx_ids.add(pkg_id)

        if not pkg.get("name"):
            result.error(f"Package '{pkg_id}' missing name")
        if not pkg.get("downloadLocation"):
            result.warn(f"Package '{pkg_id}' missing downloadLocation")

        # ライセンス ID の検証
        for field in ["licenseConcluded", "licenseDeclared"]:
            lic = pkg.get(field, "")
            if lic and not is_valid_license_id(lic):
                result.warn(f"Package '{pkg_id}' {field} is not a known SPDX ID: '{lic}'")

    # relationships
    rels = data.get("relationships", [])
    has_describes = False
    for rel in rels:
        if rel.get("relationshipType") == "DESCRIBES":
            has_describes = True
            break
    if not has_describes:
        result.error("Missing DESCRIBES relationship from DOCUMENT")

    # リレーションシップの参照先が存在するか
    all_ids = spdx_ids | {"SPDXRef-DOCUMENT"}
    for rel in rels:
        src = rel.get("spdxElementId", "")
        dst = rel.get("relatedSpdxElement", "")
        if src not in all_ids:
            result.warn(f"Relationship references unknown element: {src}")
        if dst not in all_ids:
            result.warn(f"Relationship references unknown element: {dst}")

    result.add_info(f"Packages: {len(packages)}, Relationships: {len(rels)}")


def validate_cyclonedx(data: Dict, result: ValidationResult):
    """CycloneDX 1.5 の検証"""

    # bomFormat
    if data.get("bomFormat") != "CycloneDX":
        result.error(f"bomFormat must be 'CycloneDX', got '{data.get('bomFormat')}'")

    # specVersion
    spec = data.get("specVersion", "")
    if not spec:
        result.error("Missing required field: specVersion")
    elif spec != "1.5":
        result.warn(f"specVersion is '{spec}', expected '1.5'")
    else:
        result.add_info(f"CycloneDX version: {spec}")

    # serialNumber
    sn = data.get("serialNumber", "")
    if not sn:
        result.error("Missing required field: serialNumber")
    elif not sn.startswith("urn:uuid:"):
        result.error(f"serialNumber must start with 'urn:uuid:', got '{sn}'")

    # metadata
    meta = data.get("metadata", {})
    if not meta.get("timestamp"):
        result.warn("Missing metadata.timestamp")
    if not meta.get("component"):
        result.error("Missing metadata.component (root component)")
    else:
        root = meta["component"]
        if not root.get("type"):
            result.error("Root component missing type")
        if not root.get("name"):
            result.error("Root component missing name")

    # components
    components = data.get("components", [])
    if not components:
        result.warn("No components found")

    bom_refs = set()
    for i, comp in enumerate(components):
        ref = comp.get("bom-ref", "")
        if not ref:
            result.warn(f"Component [{i}] missing bom-ref")
        elif ref in bom_refs:
            result.error(f"Duplicate bom-ref: {ref}")
        else:
            bom_refs.add(ref)

        if not comp.get("name"):
            result.error(f"Component [{i}] (bom-ref={ref}) missing name")
        if not comp.get("type"):
            result.error(f"Component '{ref}' missing type")

    # dependencies
    deps = data.get("dependencies", [])
    all_refs = bom_refs.copy()
    if meta.get("component", {}).get("bom-ref"):
        all_refs.add(meta["component"]["bom-ref"])

    for dep in deps:
        ref = dep.get("ref", "")
        if ref and ref not in all_refs:
            result.warn(f"Dependency references unknown bom-ref: {ref}")

    # compositions
    compositions = data.get("compositions", [])
    valid_aggregates = {
        "complete", "incomplete", "incomplete_first_party_only",
        "incomplete_first_party_proprietary_only",
        "incomplete_third_party_only", "unknown", "not_specified"
    }
    for comp_entry in compositions:
        agg = comp_entry.get("aggregate", "")
        if agg and agg not in valid_aggregates:
            result.warn(f"Unknown compositions.aggregate value: '{agg}'")

    result.add_info(f"Components: {len(components)}, Dependencies: {len(deps)}")


def validate_sbom(sbom_path: str, fmt: str = "auto", strict: bool = False) -> ValidationResult:
    """
    SBOM ファイルを検証する

    Returns:
        ValidationResult オブジェクト
    """
    result = ValidationResult()

    # JSON 読み込み
    try:
        with open(sbom_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.error(f"Invalid JSON: {e}")
        return result
    except FileNotFoundError:
        result.error(f"File not found: {sbom_path}")
        return result

    # 形式判定
    if fmt == "auto":
        fmt = detect_format(data)

    if fmt == "spdx":
        result.add_info("Format: SPDX")
        validate_spdx(data, result)
    elif fmt == "cyclonedx":
        result.add_info("Format: CycloneDX")
        validate_cyclonedx(data, result)
    else:
        result.error("Unable to detect SBOM format. Specify --format spdx or --format cyclonedx")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SBOM ファイルを検証する")
    parser.add_argument("sbom_file", help="検証する SBOM ファイルのパス")
    parser.add_argument("--format", choices=["auto", "spdx", "cyclonedx"],
                        default="auto", help="SBOM 形式（デフォルト: auto）")
    parser.add_argument("--strict", action="store_true",
                        help="警告もエラーとして扱う")

    args = parser.parse_args()

    result = validate_sbom(args.sbom_file, args.format, args.strict)

    print(f"Validating: {args.sbom_file}")
    print(result.summary(strict=args.strict))

    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()

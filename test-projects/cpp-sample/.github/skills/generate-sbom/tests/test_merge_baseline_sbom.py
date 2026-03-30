#!/usr/bin/env python3
"""merge_baseline_sbom.py のテスト"""

import json
import os
import sys
import tempfile
import unittest

# テスト対象モジュールのパスを追加
SCRIPT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "scripts"
)
sys.path.insert(0, SCRIPT_DIR)

from merge_baseline_sbom import (
    normalize_name,
    strip_purl_version,
    build_rule_table,
    get_component_rule,
    get_bom_rule,
    is_empty_value,
    match_components,
    merge_component_attributes,
    merge_bom_attributes,
    merge_sboms,
)


# --- ヘルパー ---

def make_component(name, version=None, licenses=None, purl=None,
                   supplier=None, hashes=None, **kwargs):
    """テスト用コンポーネントを生成する"""
    comp = {"name": name}
    if version is not None:
        comp["version"] = version
    if licenses is not None:
        comp["licenses"] = licenses
    if purl is not None:
        comp["purl"] = purl
    if supplier is not None:
        comp["supplier"] = supplier
    if hashes is not None:
        comp["hashes"] = hashes
    comp.update(kwargs)
    return comp


def make_cdx_sbom(components=None, metadata=None, dependencies=None,
                  vulnerabilities=None, services=None):
    """テスト用 CycloneDX SBOM を生成する"""
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "components": components or [],
    }
    if metadata is not None:
        sbom["metadata"] = metadata
    if dependencies is not None:
        sbom["dependencies"] = dependencies
    if vulnerabilities is not None:
        sbom["vulnerabilities"] = vulnerabilities
    if services is not None:
        sbom["services"] = services
    return sbom


# === ユーティリティ関数テスト ===

class TestNormalizeName(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize_name("Mbed TLS"), "mbedtls")

    def test_hyphens_underscores(self):
        self.assertEqual(normalize_name("mbed-tls"), "mbedtls")
        self.assertEqual(normalize_name("mbed_tls"), "mbedtls")

    def test_mixed(self):
        self.assertEqual(normalize_name("My-Lib_Name Test"), "mylibname test"
                         .replace(" ", ""))
        # "mylibnametest"
        self.assertEqual(normalize_name("My-Lib_Name Test"), "mylibnametest")

    def test_already_normalized(self):
        self.assertEqual(normalize_name("cjson"), "cjson")


class TestStripPurlVersion(unittest.TestCase):
    def test_with_version(self):
        self.assertEqual(
            strip_purl_version("pkg:generic/cjson@1.7.15"),
            "pkg:generic/cjson"
        )

    def test_without_version(self):
        self.assertEqual(
            strip_purl_version("pkg:generic/cjson"),
            "pkg:generic/cjson"
        )

    def test_with_qualifiers(self):
        self.assertEqual(
            strip_purl_version("pkg:npm/lodash@4.17.21?vcs_url=github.com/lodash"),
            "pkg:npm/lodash?vcs_url=github.com/lodash"
        )


class TestIsEmptyValue(unittest.TestCase):
    def test_none(self):
        self.assertTrue(is_empty_value(None))

    def test_noassertion(self):
        self.assertTrue(is_empty_value("NOASSERTION"))
        self.assertTrue(is_empty_value(" NOASSERTION "))

    def test_empty_string(self):
        self.assertTrue(is_empty_value(""))
        self.assertTrue(is_empty_value("  "))

    def test_empty_collections(self):
        self.assertTrue(is_empty_value([]))
        self.assertTrue(is_empty_value({}))

    def test_non_empty(self):
        self.assertFalse(is_empty_value("MIT"))
        self.assertFalse(is_empty_value(["item"]))
        self.assertFalse(is_empty_value({"key": "val"}))
        self.assertFalse(is_empty_value(0))


# === ルールテーブルテスト ===

class TestBuildRuleTable(unittest.TestCase):
    def test_empty_config(self):
        comp_rules, bom_rules = build_rule_table({})
        self.assertEqual(comp_rules, {})
        self.assertEqual(bom_rules, {})

    def test_with_overrides(self):
        config = {
            "merge_overrides": {
                "component_attributes": {"version": "pr", "description": "pr"},
                "bom_attributes": {"metadata.authors": "pr"}
            }
        }
        comp_rules, bom_rules = build_rule_table(config)
        self.assertEqual(comp_rules, {"version": "pr", "description": "pr"})
        self.assertEqual(bom_rules, {"metadata.authors": "pr"})

    def test_invalid_values_ignored(self):
        config = {
            "merge_overrides": {
                "component_attributes": {"version": "invalid", "name": "baseline"}
            }
        }
        comp_rules, _ = build_rule_table(config)
        self.assertNotIn("version", comp_rules)
        self.assertEqual(comp_rules["name"], "baseline")


class TestGetComponentRule(unittest.TestCase):
    def test_default_pr_attrs(self):
        self.assertEqual(get_component_rule("licenses", {}), "pr")
        self.assertEqual(get_component_rule("hashes", {}), "pr")

    def test_default_baseline_attrs(self):
        self.assertEqual(get_component_rule("name", {}), "baseline")
        self.assertEqual(get_component_rule("version", {}), "baseline")
        self.assertEqual(get_component_rule("purl", {}), "baseline")

    def test_override(self):
        rules = {"version": "pr"}
        self.assertEqual(get_component_rule("version", rules), "pr")

    def test_override_reversal(self):
        rules = {"licenses": "baseline"}
        self.assertEqual(get_component_rule("licenses", rules), "baseline")


class TestGetBomRule(unittest.TestCase):
    def test_default_pr_attrs(self):
        self.assertEqual(get_bom_rule("metadata.component", {}), "pr")
        self.assertEqual(get_bom_rule("metadata.tools", {}), "pr")
        self.assertEqual(get_bom_rule("dependencies", {}), "pr")

    def test_default_baseline_attrs(self):
        self.assertEqual(get_bom_rule("metadata.authors", {}), "baseline")
        self.assertEqual(get_bom_rule("services", {}), "baseline")

    def test_vulnerabilities_always_pr(self):
        # vulnerabilities は常に引き継がない（override 不可）
        self.assertEqual(get_bom_rule("vulnerabilities", {}), "pr")
        self.assertEqual(
            get_bom_rule("vulnerabilities", {"vulnerabilities": "baseline"}),
            "pr"
        )

    def test_override(self):
        rules = {"services": "pr"}
        self.assertEqual(get_bom_rule("services", rules), "pr")


# === コンポーネントマッチングテスト ===

class TestMatchComponents(unittest.TestCase):
    def test_purl_match(self):
        pr = [make_component("cJSON", purl="pkg:generic/cjson@1.7.15")]
        bl = [make_component("cJSON", purl="pkg:generic/cjson@1.7.14")]
        results, matched = match_components(pr, bl, {})
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0][1])
        self.assertEqual(results[0][2], "purl")

    def test_name_normalized_match(self):
        pr = [make_component("mbedtls")]
        bl = [make_component("Mbed TLS")]
        results, matched = match_components(pr, bl, {})
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0][1])
        self.assertEqual(results[0][2], "name_normalized")

    def test_config_bridge_match(self):
        """component_overrides 経由のマッチング（優先度3）"""
        pr = [make_component("mbedtls")]
        bl = [make_component("Mbed-TLS-Library")]  # 正規化しても一致しない
        config = {
            "component_overrides": {
                "third-party/mbedtls": {"name": "Mbed-TLS-Library"}
            }
        }
        results, matched = match_components(pr, bl, config)
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0][1])
        self.assertEqual(results[0][2], "config_bridge")

    def test_no_match(self):
        pr = [make_component("new-lib")]
        bl = [make_component("old-lib")]
        results, matched = match_components(pr, bl, {})
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0][1])
        self.assertEqual(results[0][2], "none")

    def test_multiple_components(self):
        pr = [
            make_component("cJSON", purl="pkg:generic/cjson@1.7.15"),
            make_component("zlib"),
            make_component("new-lib"),
        ]
        bl = [
            make_component("cJSON", purl="pkg:generic/cjson@1.7.14"),
            make_component("Zlib"),
            make_component("removed-lib"),
        ]
        results, bl_matched = match_components(pr, bl, {})
        self.assertEqual(len(results), 3)

        # cJSON: purl match
        self.assertEqual(results[0][2], "purl")
        # zlib: name match
        self.assertEqual(results[1][2], "name_normalized")
        # new-lib: no match
        self.assertIsNone(results[2][1])

        # removed-lib はマッチされていない
        self.assertEqual(len(bl_matched), 2)

    def test_purl_priority_over_name(self):
        """purl が一致すれば name の正規化マッチより優先"""
        pr = [make_component("cjson-fork", purl="pkg:generic/cjson@2.0")]
        bl = [
            make_component("cJSON", purl="pkg:generic/cjson@1.7"),
            make_component("cjson-fork"),  # name では一致するが purl 優先
        ]
        results, matched = match_components(pr, bl, {})
        self.assertEqual(results[0][2], "purl")
        self.assertEqual(results[0][1]["name"], "cJSON")

    def test_no_duplicate_match(self):
        """同じベースラインコンポーネントが複数回マッチしない"""
        pr = [
            make_component("zlib", purl="pkg:generic/zlib@1.2.11"),
            make_component("Zlib"),  # name でも一致するが既にマッチ済み
        ]
        bl = [make_component("zlib", purl="pkg:generic/zlib@1.2.10")]
        results, matched = match_components(pr, bl, {})
        # 1つ目は purl マッチ
        self.assertIsNotNone(results[0][1])
        # 2つ目はマッチなし（既に使用済み）
        self.assertIsNone(results[1][1])


# === 属性マージテスト ===

class TestMergeComponentAttributes(unittest.TestCase):
    def test_fallback_fills_empty(self):
        """(A) fallback: PR が空→ベースラインから引き継ぐ"""
        pr = make_component("cJSON")
        bl = make_component("cJSON", version="1.7.15",
                            supplier={"name": "Dave Gamble"})
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(merged["version"], "1.7.15")
        self.assertEqual(merged["supplier"], {"name": "Dave Gamble"})
        self.assertEqual(len(inherited), 2)
        self.assertEqual(len(overwritten), 0)

    def test_fallback_keeps_pr_when_present(self):
        """(A) fallback: PR に値がある場合は PR を保持"""
        pr = make_component("cJSON", version="1.8.0")
        bl = make_component("cJSON", version="1.7.15")
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(merged["version"], "1.8.0")
        self.assertEqual(len(inherited), 0)

    def test_pr_priority_overwrites(self):
        """(B) PR 優先: licenses は PR が優先、差分がある場合は通知"""
        pr = make_component("cJSON", licenses=[{"license": {"id": "MIT"}}])
        bl = make_component("cJSON", licenses=[{"expression": "Apache-2.0"}])
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(merged["licenses"], [{"license": {"id": "MIT"}}])
        self.assertEqual(len(overwritten), 1)
        self.assertEqual(overwritten[0]["attribute"], "licenses")

    def test_pr_priority_no_notification_when_same(self):
        """(B) PR 優先: 値が同じなら通知なし"""
        lic = [{"license": {"id": "MIT"}}]
        pr = make_component("cJSON", licenses=lic)
        bl = make_component("cJSON", licenses=lic)
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(len(overwritten), 0)

    def test_noassertion_triggers_fallback(self):
        """NOASSERTION は空値として fallback を発動"""
        pr = make_component("zlib", version="NOASSERTION")
        bl = make_component("zlib", version="1.2.11")
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(merged["version"], "1.2.11")

    def test_override_version_to_pr(self):
        """merge_overrides で version を PR 優先に変更"""
        pr = make_component("lib", version="2.0")
        bl = make_component("lib", version="1.0")
        rules = {"version": "pr"}
        merged, overwritten, inherited = merge_component_attributes(pr, bl, rules)
        self.assertEqual(merged["version"], "2.0")
        self.assertEqual(len(overwritten), 1)

    def test_override_licenses_to_baseline(self):
        """merge_overrides で licenses を baseline 優先に変更"""
        pr = make_component("lib")  # licenses なし
        bl = make_component("lib", licenses=[{"license": {"id": "MIT"}}])
        rules = {"licenses": "baseline"}
        merged, overwritten, inherited = merge_component_attributes(pr, bl, rules)
        self.assertEqual(merged["licenses"], [{"license": {"id": "MIT"}}])
        self.assertEqual(len(inherited), 1)

    def test_hashes_pr_priority(self):
        """hashes はデフォルト (B) PR 優先"""
        pr_hashes = [{"alg": "SHA-256", "content": "abc123"}]
        bl_hashes = [{"alg": "SHA-256", "content": "old456"}]
        pr = make_component("lib", hashes=pr_hashes)
        bl = make_component("lib", hashes=bl_hashes)
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})
        self.assertEqual(merged["hashes"], pr_hashes)
        self.assertEqual(len(overwritten), 1)


# === BOM レベル属性マージテスト ===

class TestMergeBomAttributes(unittest.TestCase):
    def test_metadata_authors_fallback(self):
        """metadata.authors は (A) fallback"""
        pr = make_cdx_sbom(metadata={"tools": [{"name": "scancode"}]})
        bl = make_cdx_sbom(metadata={
            "tools": [{"name": "old-tool"}],
            "authors": [{"name": "Author A"}],
        })
        merged, changes = merge_bom_attributes(pr, bl, {})
        self.assertEqual(merged["metadata"]["authors"], [{"name": "Author A"}])
        inherited = [c for c in changes if c["action"] == "inherited_from_baseline"]
        self.assertTrue(any(c["path"] == "metadata.authors" for c in inherited))

    def test_metadata_tools_pr_priority(self):
        """metadata.tools は (B) PR 優先"""
        pr = make_cdx_sbom(metadata={"tools": [{"name": "new-tool"}]})
        bl = make_cdx_sbom(metadata={"tools": [{"name": "old-tool"}]})
        merged, changes = merge_bom_attributes(pr, bl, {})
        self.assertEqual(merged["metadata"]["tools"], [{"name": "new-tool"}])

    def test_dependencies_pr_priority(self):
        """dependencies は (B) PR 優先"""
        pr_deps = [{"ref": "root", "dependsOn": ["a", "b"]}]
        bl_deps = [{"ref": "root", "dependsOn": ["a"]}]
        pr = make_cdx_sbom(dependencies=pr_deps)
        bl = make_cdx_sbom(dependencies=bl_deps)
        merged, changes = merge_bom_attributes(pr, bl, {})
        self.assertEqual(merged["dependencies"], pr_deps)

    def test_vulnerabilities_stripped(self):
        """vulnerabilities は常に除去"""
        pr = make_cdx_sbom()
        bl = make_cdx_sbom(vulnerabilities=[{"id": "CVE-2024-1234"}])
        # PR に vulnerabilities があっても除去
        pr["vulnerabilities"] = [{"id": "CVE-2024-5678"}]
        merged, changes = merge_bom_attributes(pr, bl, {})
        self.assertNotIn("vulnerabilities", merged)

    def test_services_fallback(self):
        """services は (A) fallback"""
        pr = make_cdx_sbom()
        bl = make_cdx_sbom(services=[{"name": "api-server"}])
        merged, changes = merge_bom_attributes(pr, bl, {})
        self.assertEqual(merged["services"], [{"name": "api-server"}])

    def test_bom_override_services_to_pr(self):
        """merge_overrides で services を PR 優先に"""
        pr = make_cdx_sbom(services=[{"name": "new-svc"}])
        bl = make_cdx_sbom(services=[{"name": "old-svc"}])
        rules = {"services": "pr"}
        merged, changes = merge_bom_attributes(pr, bl, rules)
        self.assertEqual(merged["services"], [{"name": "new-svc"}])


# === 統合テスト ===

class TestMergeSboms(unittest.TestCase):
    def test_full_merge(self):
        """フルマージシナリオ"""
        pr = make_cdx_sbom(
            components=[
                make_component("cJSON", version="NOASSERTION",
                               licenses=[{"license": {"id": "MIT"}}]),
                make_component("zlib"),
                make_component("new-lib", version="1.0"),
            ],
            metadata={"tools": [{"name": "scancode"}]},
            dependencies=[{"ref": "root", "dependsOn": ["cjson", "zlib", "new-lib"]}],
        )
        bl = make_cdx_sbom(
            components=[
                make_component("cJSON", version="1.7.15",
                               purl="pkg:generic/cjson@1.7.15",
                               licenses=[{"expression": "MIT"}]),
                make_component("Zlib", version="1.2.11"),
                make_component("removed-lib", version="2.0"),
            ],
            metadata={
                "tools": [{"name": "old-tool"}],
                "authors": [{"name": "Author"}],
            },
        )

        merged, report = merge_sboms(pr, bl, {})

        # サマリー
        self.assertEqual(report["summary"]["matched"], 2)
        self.assertEqual(report["summary"]["new_in_pr"], 1)
        self.assertEqual(report["summary"]["removed_from_baseline"], 1)

        # cJSON: version を fallback で引き継ぎ、licenses は PR 優先で上書き
        cjson = next(c for c in merged["components"] if c["name"] == "cJSON")
        self.assertEqual(cjson["version"], "1.7.15")  # inherited
        self.assertEqual(cjson["licenses"], [{"license": {"id": "MIT"}}])  # PR kept

        # purl も fallback で引き継ぎ
        self.assertEqual(cjson["purl"], "pkg:generic/cjson@1.7.15")

        # zlib: version を fallback で引き継ぎ
        zlib = next(c for c in merged["components"] if normalize_name(c["name"]) == "zlib")
        self.assertEqual(zlib["version"], "1.2.11")

        # new-lib: そのまま
        new_lib = next(c for c in merged["components"] if c["name"] == "new-lib")
        self.assertEqual(new_lib["version"], "1.0")

        # BOM: authors が fallback で引き継がれ、tools は PR 優先
        self.assertEqual(merged["metadata"]["authors"], [{"name": "Author"}])
        self.assertEqual(merged["metadata"]["tools"], [{"name": "scancode"}])

        # removed-lib はレポートに記録
        self.assertIn("removed-lib", report["removed_components"])
        self.assertIn("new-lib", report["new_components"])

    def test_empty_baseline(self):
        """ベースラインが空の場合、PR SBOM がそのまま出力"""
        pr = make_cdx_sbom(components=[make_component("cJSON")])
        bl = make_cdx_sbom(components=[])

        merged, report = merge_sboms(pr, bl, {})
        self.assertEqual(len(merged["components"]), 1)
        self.assertEqual(report["summary"]["matched"], 0)
        self.assertEqual(report["summary"]["new_in_pr"], 1)

    def test_with_merge_overrides(self):
        """merge_overrides で version を PR 優先に変更"""
        pr = make_cdx_sbom(
            components=[make_component("cJSON", version="2.0")]
        )
        bl = make_cdx_sbom(
            components=[make_component("cJSON", version="1.7.15")]
        )
        config = {
            "merge_overrides": {
                "component_attributes": {"version": "pr"}
            }
        }

        merged, report = merge_sboms(pr, bl, config)
        cjson = merged["components"][0]
        self.assertEqual(cjson["version"], "2.0")

        # 上書き通知あり
        match = report["matches"][0]
        self.assertTrue(any(
            o["attribute"] == "version" for o in match["overwritten_attributes"]
        ))

    def test_vulnerabilities_not_inherited(self):
        """ベースラインの vulnerabilities は引き継がない"""
        pr = make_cdx_sbom(components=[make_component("lib")])
        bl = make_cdx_sbom(
            components=[make_component("lib")],
            vulnerabilities=[{"id": "CVE-2024-0001", "source": {"name": "NVD"}}]
        )
        merged, report = merge_sboms(pr, bl, {})
        self.assertNotIn("vulnerabilities", merged)


# === 追加テスト ===

class TestSpecVersionCompatibility(unittest.TestCase):
    """CycloneDX 1.4 ベースラインとのマージ互換性"""

    def test_cdx14_baseline_merge(self):
        """specVersion 1.4 のベースラインとマージできる"""
        pr = make_cdx_sbom(
            components=[make_component("cJSON", version="NOASSERTION")],
        )
        bl = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "components": [
                make_component("cJSON", version="1.7.15",
                               purl="pkg:generic/cjson@1.7.15"),
            ],
        }
        merged, report = merge_sboms(pr, bl, {})
        # マージは成功し、PR の specVersion を保持
        self.assertEqual(merged["specVersion"], "1.5")
        self.assertEqual(merged["components"][0]["version"], "1.7.15")
        self.assertEqual(report["summary"]["matched"], 1)

    def test_cdx14_baseline_empty_components(self):
        """specVersion 1.4 の空ベースラインでもエラーにならない"""
        pr = make_cdx_sbom(components=[make_component("lib")])
        bl = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "version": 1,
            "components": [],
        }
        merged, report = merge_sboms(pr, bl, {})
        self.assertEqual(len(merged["components"]), 1)
        self.assertEqual(report["summary"]["new_in_pr"], 1)


class TestBomLevelMergeOverridesIntegration(unittest.TestCase):
    """BOM レベルの merge_overrides が merge_sboms で反映されるか"""

    def test_services_override_to_pr(self):
        """bom_attributes で services を PR 優先に変更した場合"""
        pr = make_cdx_sbom(
            components=[make_component("lib")],
            services=[{"name": "new-api"}],
        )
        bl = make_cdx_sbom(
            components=[make_component("lib")],
            services=[{"name": "old-api"}],
        )
        config = {
            "merge_overrides": {
                "bom_attributes": {"services": "pr"}
            }
        }
        merged, report = merge_sboms(pr, bl, config)
        self.assertEqual(merged["services"], [{"name": "new-api"}])

    def test_metadata_authors_override_to_pr(self):
        """bom_attributes で metadata.authors を PR 優先に変更"""
        pr = make_cdx_sbom(
            components=[make_component("lib")],
            metadata={"authors": [{"name": "New Author"}]},
        )
        bl = make_cdx_sbom(
            components=[make_component("lib")],
            metadata={"authors": [{"name": "Old Author"}]},
        )
        config = {
            "merge_overrides": {
                "bom_attributes": {"metadata.authors": "pr"}
            }
        }
        merged, report = merge_sboms(pr, bl, config)
        self.assertEqual(merged["metadata"]["authors"], [{"name": "New Author"}])


class TestFullAttributeFallback(unittest.TestCase):
    """全 fallback 属性が一度に正しく引き継がれるか"""

    def test_all_fallback_attrs_inherited(self):
        """PR が空で、ベースラインの全 (A) 属性が引き継がれる"""
        pr = make_component("cJSON")  # name のみ
        bl = make_component(
            "cJSON",
            version="1.7.15",
            purl="pkg:generic/cjson@1.7.15",
            supplier={"name": "Dave Gamble"},
            author="Dave Gamble",
            description="JSON parser for C",
            externalReferences=[{"type": "website", "url": "https://example.com"}],
            properties=[{"name": "custom", "value": "data"}],
        )
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})

        self.assertEqual(merged["version"], "1.7.15")
        self.assertEqual(merged["purl"], "pkg:generic/cjson@1.7.15")
        self.assertEqual(merged["supplier"], {"name": "Dave Gamble"})
        self.assertEqual(merged["author"], "Dave Gamble")
        self.assertEqual(merged["description"], "JSON parser for C")
        self.assertEqual(merged["externalReferences"],
                         [{"type": "website", "url": "https://example.com"}])
        self.assertEqual(merged["properties"],
                         [{"name": "custom", "value": "data"}])
        self.assertEqual(len(overwritten), 0)
        self.assertGreaterEqual(len(inherited), 6)

    def test_pr_values_not_overwritten_by_fallback(self):
        """PR に値がある属性はベースラインで上書きされない"""
        pr = make_component(
            "cJSON",
            version="2.0.0",
            purl="pkg:generic/cjson@2.0.0",
            supplier={"name": "New Maintainer"},
        )
        bl = make_component(
            "cJSON",
            version="1.7.15",
            purl="pkg:generic/cjson@1.7.15",
            supplier={"name": "Dave Gamble"},
        )
        merged, overwritten, inherited = merge_component_attributes(pr, bl, {})

        self.assertEqual(merged["version"], "2.0.0")
        self.assertEqual(merged["purl"], "pkg:generic/cjson@2.0.0")
        self.assertEqual(merged["supplier"], {"name": "New Maintainer"})
        self.assertEqual(len(inherited), 0)


class TestMixedMatchMethods(unittest.TestCase):
    """purl, name, config_bridge が同時に使われるケース"""

    def test_three_methods_in_one_merge(self):
        """3種類のマッチ方法が同一マージで正しく動作"""
        pr = make_cdx_sbom(components=[
            make_component("cJSON", purl="pkg:generic/cjson@1.7.15"),
            make_component("zlib"),          # name 正規化マッチ
            make_component("mbedtls"),        # config bridge マッチ
            make_component("brand-new-lib"),  # マッチなし
        ])
        bl = make_cdx_sbom(components=[
            make_component("cJSON", version="1.7.15",
                           purl="pkg:generic/cjson@1.7.14"),
            make_component("Zlib", version="1.2.11"),
            make_component("Mbed-TLS-Official", version="3.5.0"),
            make_component("deprecated-lib", version="0.1"),
        ])
        config = {
            "component_overrides": {
                "third-party/mbedtls": {"name": "Mbed-TLS-Official"}
            }
        }

        merged, report = merge_sboms(pr, bl, config)

        self.assertEqual(report["summary"]["matched"], 3)
        self.assertEqual(report["summary"]["new_in_pr"], 1)
        self.assertEqual(report["summary"]["removed_from_baseline"], 1)

        # マッチ方法の確認
        methods = {m["match_method"] for m in report["matches"]}
        self.assertIn("purl", methods)
        self.assertIn("name_normalized", methods)
        self.assertIn("config_bridge", methods)

        # version fallback 確認
        zlib = next(c for c in merged["components"]
                    if normalize_name(c["name"]) == "zlib")
        self.assertEqual(zlib["version"], "1.2.11")

        mbedtls = next(c for c in merged["components"]
                       if normalize_name(c["name"]) == "mbedtls")
        self.assertEqual(mbedtls["version"], "3.5.0")


class TestReportStructure(unittest.TestCase):
    """マージレポートの必須フィールドが揃っているか"""

    def test_report_has_required_fields(self):
        """レポートに summary, matches, new_components, removed_components がある"""
        pr = make_cdx_sbom(components=[
            make_component("cJSON", licenses=[{"license": {"id": "MIT"}}]),
            make_component("new-lib"),
        ])
        bl = make_cdx_sbom(components=[
            make_component("cJSON", version="1.7.15",
                           licenses=[{"expression": "Apache-2.0"}]),
            make_component("old-lib"),
        ])
        _, report = merge_sboms(pr, bl, {})

        # トップレベルキー
        self.assertIn("summary", report)
        self.assertIn("matches", report)
        self.assertIn("new_components", report)
        self.assertIn("removed_components", report)

        # summary 必須キー
        for key in ("matched", "new_in_pr", "removed_from_baseline"):
            self.assertIn(key, report["summary"])

        # matches の各エントリ構造
        for match in report["matches"]:
            self.assertIn("pr_name", match)
            self.assertIn("baseline_name", match)
            self.assertIn("match_method", match)
            self.assertIn("overwritten_attributes", match)
            self.assertIn("inherited_attributes", match)

    def test_overwritten_attribute_structure(self):
        """overwritten_attributes の各エントリに attribute, baseline_value, pr_value がある"""
        pr = make_cdx_sbom(components=[
            make_component("lib", licenses=[{"license": {"id": "MIT"}}]),
        ])
        bl = make_cdx_sbom(components=[
            make_component("lib", licenses=[{"expression": "Apache-2.0"}]),
        ])
        _, report = merge_sboms(pr, bl, {})

        overwritten = report["matches"][0]["overwritten_attributes"]
        self.assertGreaterEqual(len(overwritten), 1)
        for entry in overwritten:
            self.assertIn("attribute", entry)
            self.assertIn("baseline_value", entry)
            self.assertIn("pr_value", entry)

    def test_inherited_attribute_structure(self):
        """inherited_attributes の各エントリに attribute, baseline_value, rule がある"""
        pr = make_cdx_sbom(components=[make_component("lib")])
        bl = make_cdx_sbom(components=[
            make_component("lib", version="1.0", purl="pkg:generic/lib@1.0"),
        ])
        _, report = merge_sboms(pr, bl, {})

        inherited = report["matches"][0]["inherited_attributes"]
        self.assertGreaterEqual(len(inherited), 1)
        for entry in inherited:
            self.assertIn("attribute", entry)
            self.assertIn("baseline_value", entry)
            self.assertIn("rule", entry)


# === CLI 統合テスト ===

class TestCLI(unittest.TestCase):
    def test_cli_execution(self):
        """CLI として実行し、ファイル出力を確認"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pr_path = os.path.join(tmpdir, "pr-sbom.json")
            bl_path = os.path.join(tmpdir, "baseline.json")
            out_sbom = os.path.join(tmpdir, "merged.json")
            out_report = os.path.join(tmpdir, "report.json")

            pr = make_cdx_sbom(
                components=[make_component("cJSON", version="NOASSERTION")],
                metadata={"tools": [{"name": "test"}]},
            )
            bl = make_cdx_sbom(
                components=[make_component("cJSON", version="1.7.15")],
            )

            with open(pr_path, "w") as f:
                json.dump(pr, f)
            with open(bl_path, "w") as f:
                json.dump(bl, f)

            script = os.path.join(SCRIPT_DIR, "merge_baseline_sbom.py")
            exit_code = os.system(
                f"python3 {script} {pr_path} {bl_path} "
                f"--output-sbom {out_sbom} --output-report {out_report}"
            )
            self.assertEqual(exit_code, 0)

            with open(out_sbom) as f:
                merged = json.load(f)
            with open(out_report) as f:
                report = json.load(f)

            self.assertEqual(merged["components"][0]["version"], "1.7.15")
            self.assertEqual(report["summary"]["matched"], 1)

    def test_cli_empty_baseline(self):
        """ベースラインが空の場合の CLI 実行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pr_path = os.path.join(tmpdir, "pr-sbom.json")
            bl_path = os.path.join(tmpdir, "baseline.json")
            out_sbom = os.path.join(tmpdir, "merged.json")
            out_report = os.path.join(tmpdir, "report.json")

            pr = make_cdx_sbom(components=[make_component("lib", version="1.0")])
            bl = make_cdx_sbom(components=[])

            with open(pr_path, "w") as f:
                json.dump(pr, f)
            with open(bl_path, "w") as f:
                json.dump(bl, f)

            script = os.path.join(SCRIPT_DIR, "merge_baseline_sbom.py")
            exit_code = os.system(
                f"python3 {script} {pr_path} {bl_path} "
                f"--output-sbom {out_sbom} --output-report {out_report}"
            )
            self.assertEqual(exit_code, 0)

            with open(out_sbom) as f:
                merged = json.load(f)
            self.assertEqual(merged["components"][0]["version"], "1.0")


if __name__ == "__main__":
    unittest.main()

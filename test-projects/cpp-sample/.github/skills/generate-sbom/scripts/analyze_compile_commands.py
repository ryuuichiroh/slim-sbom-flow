#!/usr/bin/env python3
"""
compile_commands.json を解析してビルド関連情報を抽出する。

Clang JSON Compilation Database 仕様に基づき、各エントリの
`arguments` (推奨) または `command` (シェル文字列) を扱う。

出力例:
{
  "entry_count": 2,
  "compilers": ["gcc"],
  "source_files": ["src/main.c", "third-party/cjson/cJSON.c"],
  "include_paths": ["third-party/cjson", "third-party/mbedtls", "third-party/zlib"],
  "third_party_include_paths": ["third-party/cjson", "third-party/mbedtls", "third-party/zlib"],
  "libraries": ["crypto", "ssl", "z"],
  "warnings": []
}
"""

import argparse
import json
import os
import shlex
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize_path(path_value: str, base_dir: str) -> str:
    if not path_value:
        return ""
    if os.path.isabs(path_value):
        normalized = os.path.normpath(path_value)
    else:
        normalized = os.path.normpath(os.path.join(base_dir, path_value))
    return normalized


def _to_repo_relative(path_value: str, repo_root: str) -> str:
    try:
        rel = os.path.relpath(path_value, repo_root)
        if not rel.startswith(".."):
            return rel.replace("\\", "/")
    except Exception:
        pass
    return path_value.replace("\\", "/")


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """
    .sbom-config.json を読み込む（存在しなければ空dict）
    """
    if config_path and os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _normalize_deps_dirs(deps_dirs: List[str]) -> List[str]:
    """
    deps_directories を正規化（末尾の / を統一）
    """
    normalized = []
    for d in deps_dirs:
        d_stripped = d.rstrip("/")
        if d_stripped:
            normalized.append(d_stripped)
    return normalized


def _parse_argv(entry: Dict[str, Any]) -> Tuple[List[str], str]:
    args = entry.get("arguments")
    cmd = entry.get("command")

    if isinstance(args, list) and args:
        return [str(a) for a in args], "arguments"

    if isinstance(cmd, str) and cmd.strip():
        return shlex.split(cmd), "command"

    return [], "missing"


def extract_compile_db_info(
    db: List[Dict[str, Any]],
    repo_root: str,
    deps_dirs: Optional[List[str]] = None
) -> Dict[str, Any]:
    compilers: Set[str] = set()
    source_files: Set[str] = set()
    include_paths: Set[str] = set()
    third_party_includes: Set[str] = set()
    libraries: Set[str] = set()
    warnings: List[str] = []

    # deps_directories のデフォルト値
    if deps_dirs is None:
        deps_dirs = ["third-party", "third_party", "deps", "vendor", "external"]
    else:
        deps_dirs = _normalize_deps_dirs(deps_dirs)

    # include_markers 判定用（小文字に統一）
    include_markers = tuple(d.lower() for d in deps_dirs)

    for idx, entry in enumerate(db):
        if not isinstance(entry, dict):
            warnings.append(f"entry[{idx}] is not an object")
            continue

        directory = entry.get("directory")
        main_file = entry.get("file")
        if not isinstance(directory, str) or not directory:
            warnings.append(f"entry[{idx}] has invalid or missing 'directory'")
            continue
        if not isinstance(main_file, str) or not main_file:
            warnings.append(f"entry[{idx}] has invalid or missing 'file'")
            continue

        argv, source = _parse_argv(entry)
        if not argv:
            warnings.append(f"entry[{idx}] has neither usable 'arguments' nor 'command'")
            continue

        if source == "command":
            warnings.append(
                f"entry[{idx}] used 'command'; prefer 'arguments' to avoid shell parsing ambiguity"
            )

        compiler = argv[0]
        compilers.add(os.path.basename(compiler))

        abs_main_file = _normalize_path(main_file, directory)
        source_files.add(_to_repo_relative(abs_main_file, repo_root))

        i = 1
        while i < len(argv):
            arg = argv[i]

            if arg == "-I":
                if i + 1 < len(argv):
                    inc_abs = _normalize_path(argv[i + 1], directory)
                    inc_rel = _to_repo_relative(inc_abs, repo_root)
                    include_paths.add(inc_rel)
                    lowered = inc_rel.lower()
                    if any(marker in lowered for marker in include_markers):
                        third_party_includes.add(inc_rel)
                    i += 2
                    continue
            elif arg.startswith("-I") and arg != "-I":
                inc_abs = _normalize_path(arg[2:], directory)
                inc_rel = _to_repo_relative(inc_abs, repo_root)
                include_paths.add(inc_rel)
                lowered = inc_rel.lower()
                if any(marker in lowered for marker in include_markers):
                    third_party_includes.add(inc_rel)
            elif arg in ("-isystem", "-iquote"):
                if i + 1 < len(argv):
                    inc_abs = _normalize_path(argv[i + 1], directory)
                    inc_rel = _to_repo_relative(inc_abs, repo_root)
                    include_paths.add(inc_rel)
                    lowered = inc_rel.lower()
                    if any(marker in lowered for marker in include_markers):
                        third_party_includes.add(inc_rel)
                    i += 2
                    continue
            elif arg == "-l":
                if i + 1 < len(argv):
                    libraries.add(argv[i + 1])
                    i += 2
                    continue
            elif arg.startswith("-l") and arg != "-l":
                libraries.add(arg[2:])

            i += 1

    return {
        "entry_count": len(db),
        "compilers": sorted(compilers),
        "source_files": sorted(source_files),
        "include_paths": sorted(include_paths),
        "third_party_include_paths": sorted(third_party_includes),
        "libraries": sorted(libraries),
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="compile_commands.json から source/include/compiler 情報を抽出する"
    )
    parser.add_argument("compile_commands", help="compile_commands.json のパス")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="相対パス算出に使うリポジトリルート（デフォルト: カレント）",
    )
    parser.add_argument(
        "--config",
        default=None,
        help=".sbom-config.json のパス（オプション）。deps_directories があれば使用",
    )
    parser.add_argument(
        "--output",
        default="compile-analysis.json",
        help="出力 JSON パス（デフォルト: compile-analysis.json）",
    )
    args = parser.parse_args()

    with open(args.compile_commands, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("compile_commands.json must be a JSON array")

    repo_root = os.path.abspath(args.repo_root)
    
    # config から deps_directories を読み込み（あれば）
    config = _load_config(args.config)
    deps_dirs = config.get("deps_directories")
    
    result = extract_compile_db_info(data, repo_root, deps_dirs)

    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    print(
        "Parsed compile_commands.json: "
        f"entries={result['entry_count']}, "
        f"sources={len(result['source_files'])}, "
        f"includes={len(result['include_paths'])}, "
        f"libs={len(result['libraries'])}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

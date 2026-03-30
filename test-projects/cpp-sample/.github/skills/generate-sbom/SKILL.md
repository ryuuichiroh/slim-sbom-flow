---
name: generate-sbom
description: >
  Generate SPDX 2.3 and CycloneDX 1.5 SBOMs for C/C++ projects built with Makefile.
  Analyzes scancode-json-pp.json to detect licenses, copyrights, and third-party components,
  then produces standards-compliant SBOM files. Optionally uses compile_commands.json for
  build-target filtering and Makefile for link-library detection.
  Use this skill whenever the user asks to generate an SBOM, create a software bill of materials,
  list OSS components and licenses, or produce SPDX/CycloneDX output for a C/C++ project.
---

# SBOM Generation for C/C++ Projects

You are an SBOM (Software Bill of Materials) and license management expert for C/C++ projects.
Your job is to analyze source code scan results and produce standards-compliant SBOMs.

## Prerequisites

The project must have `scancode-json-pp.json` in the project root. Generate it with:

```bash
scancode -lpc \
  --strip-root --classify --consolidate \
  --license-clarity-score --license-text --license-references \
  --summary --tallies \
  --ignore "*.json" --ignore ".git/*" --ignore ".github/*" \
  --json-pp scancode-json-pp.json .
```

## Input Files

| File | Required | Purpose |
|---|---|---|
| `scancode-json-pp.json` | **Yes** | License, copyright, and file inventory from ScanCode Toolkit |
| `.sbom-config.json` | No | Project-specific overrides (name, holder, license mappings, etc.) |
| `compile_commands.json` | No | Build-target filtering and include-path dependency analysis |
| `Makefile` (or `CMakeLists.txt`) | No | Link-library detection (`-l` flags from `LDFLAGS`/`LIBS`) |

## Workflow

Follow these steps in order. Steps 2-4 are optional depending on available inputs.

### Step 1: Load Configuration

If `.sbom-config.json` exists, read it. It provides overrides that improve accuracy.
See the "Configuration Reference" section below for available fields.

If it does not exist, proceed with auto-detection (all fields will be inferred from scan data).

### Step 2: Read ScanCode JSON (Required)

Read `scancode-json-pp.json` and extract:

1. **File inventory** (`files` array, entries with `"type": "file"`)
2. **License detections** per file (`detected_license_expression_spdx`)
3. **Copyright holders** per file (`holders[].holder`)
4. **Consolidated components** (`consolidated_components` array) as initial component candidates

Summarize findings: total files, detected licenses, copyright holders, consolidated components.

### Step 3: Analyze compile_commands.json (Optional)

If `compile_commands.json` exists, extract:

- **Source files**: `file` field of each entry (these are the files actually compiled)
- **Include paths**: `-I`, `-isystem`, `-iquote` flags
- **Compiler**: compiler executable (`arguments[0]` or parsed from `command`)

Per Clang's JSON Compilation Database specification, each entry may use either
`arguments` (preferred) or `command` (shell-escaped string). Handle both.

Use the bundled helper script:

```bash
python3 <skill-path>/scripts/analyze_compile_commands.py \
  compile_commands.json \
  --repo-root . \
  --output compile-analysis.json
```

This produces `compile-analysis.json` with:
- `source_files`
- `include_paths`
- `third_party_include_paths`
- `compilers`
- `warnings` (for malformed entries or `command`-only fallbacks)

Use this information to:
- **Filter noise**: Only files referenced in compile_commands.json (or included via `-I` paths) are build-relevant. Mark files found only in scancode but not in compile_commands.json as candidates for exclusion (e.g., README, documentation, unused vendored code).
- **Identify third-party directories**: Include paths pointing to `third-party/`, `deps/`, `vendor/`, `external/`, etc. indicate third-party components.

### Step 4: Analyze Makefile for Link Libraries (Optional)

If a `Makefile` exists, look for link-library flags:

- `LDFLAGS`, `LIBS`, `LDLIBS` variables for `-l<name>` flags
- `target_link_libraries()` in CMakeLists.txt if applicable

These reveal dynamically/statically linked libraries that are dependencies but whose source code may not be in the project tree. Build a **link-library candidate list** by inferring the canonical library name from each `-l` flag. This list is used in Step 5 criterion 4 to add external components.

Common `-l` flag to canonical library name mappings:
- `-lz` -> **zlib**
- `-lssl`, `-lcrypto` -> **OpenSSL**
- `-lpthread` -> POSIX Threads (system library, typically excluded from SBOM)
- `-lm` -> Math library (system library, typically excluded)
- `-lrt` -> Real-time library (system library, typically excluded)
- `-ldl` -> Dynamic linking library (system library, typically excluded)

System libraries (libc, libm, libpthread, librt, libdl) are generally excluded from SBOMs unless the project specifically requires tracking them.

> **Note**: Map `-l` flags to canonical names strictly by the table above, regardless of what `third-party/` contains. For example, if the Makefile has `-lssl -lcrypto` but `third-party/` contains Mbed TLS, the canonical name is still **OpenSSL** — a different library. Do not substitute or merge based on functional similarity.

### Step 5: Identify Components

This is the core analysis step. Classify every source file into either the **root component** (the project itself) or a **third-party component**.

**Detection criteria (apply in priority order):**

1. **Copyright-holder based**: Files whose copyright holder differs from the primary copyright holder belong to a separate component. Group files by holder.
2. **Directory based**: Files under known dependency directories (`deps/`, `third-party/`, `vendor/`, `external/`, or directories listed in config `deps_directories`) form components named after the subdirectory.
3. **compile_commands.json based**: If available, third-party libraries identified from include paths that weren't caught by criteria 1-2.
4. **Link-library based**: For each entry in the link-library candidate list (from Step 4), check whether a source-level component with the **same canonical name** was already found by criteria 1–3. Matching is by **exact library name** (case-insensitive) — functional similarity does not count. If no matching component exists, add it as an external component with no source files.

   > **Example**: `-lssl -lcrypto` → canonical name "OpenSSL". If `third-party/mbedtls` exists, the source component name is "Mbed TLS" ≠ "OpenSSL" → add OpenSSL as a separate external component. If `third-party/zlib` exists, the source component name is "zlib" = "zlib" (`-lz`) → skip, already represented.

**For each component, determine:**
- **Name**: Library/component name (from directory name, copyright holder, or `-l` flag)
- **Version**: Look for `version.h`, `#define *VERSION*` patterns, or header comments. Use `NOASSERTION` if not found.
- **License**: Most frequent `detected_license_expression_spdx` among the component's files. Apply `license_overrides` from config if present.
- **Copyright**: Representative copyright text from the component's files.
- **Supplier**: Organization name derived from copyright holder (format: `Organization: <name>`).

**Noise exclusion**: Skip these file types entirely:
- Build artifacts: `.o`, `.d`, `.a`, `.so`, `.bin`, `.hex`, `.map`, `.exe`, `.dll`
- IDE files: `.eww`, `.ewp`, `.sln`, `.vcxproj`
- Files matching config `exclude_patterns`
- Documentation files (README, CHANGELOG, etc.) unless they are the only source of license info for a component

**Handle the README false-positive problem**: ScanCode often detects license mentions in README.md that are documentation, not actual license declarations. If a file is a README/documentation and compile_commands.json confirms it's not part of the build, exclude its license detections from component analysis.

### Step 6: Run Copyright Analysis Script

Run the bundled script to get detailed copyright holder statistics:

```bash
python3 <skill-path>/scripts/analyze_copyright_holders.py \
  scancode-json-pp.json \
  --config .sbom-config.json \
  --output holders-analysis.json
```

This produces `holders-analysis.json` with:
- Primary copyright holder (auto-detected if not in config, using 30% threshold on non-deps files)
- Holder statistics with file counts and percentages
- False positive filtering (garbled text, C keywords, encoding errors)

Review the output. If the primary holder detection seems wrong, suggest the user set `primary_copyright_holder` in `.sbom-config.json`.

### Step 7: Generate SBOM Files

Prepare a `components.json` that the generation script expects. The structure:

```json
{
  "root_component": {
    "name": "Project Name",
    "version": "1.0.0",
    "supplier": "Organization: Example Corp",
    "copyright": "Copyright (c) Example Corp",
    "license": "MIT",
    "type": "application"
  },
  "components": {
    "component-id": {
      "name": "cJSON",
      "version": "1.7.15",
      "supplier": "Organization: Dave Gamble",
      "copyright": "Copyright (c) Dave Gamble and cJSON contributors",
      "license": "MIT",
      "type": "library",
      "file_count": 3,
      "detection_method": "copyright-holder-based"
    }
  }
}
```

Save this as `components.json`, then run the generation script:

```bash
python3 <skill-path>/scripts/generate_sbom.py \
  scancode-json-pp.json \
  --components components.json \
  --config .sbom-config.json \
  --format both \
  --output-dir .
```

This produces:
- `sbom-spdx.json` (SPDX 2.3)
- `sbom-cyclonedx.json` (CycloneDX 1.5)
- `sbom-analysis-report.md` (human-readable summary)

### Step 8: Merge with Baseline SBOM (Conditional)

This step applies only when a baseline SBOM file (`previous-sbom.json`) exists in the project root.
The baseline is a CycloneDX SBOM previously registered in Dependency-Track, which may contain
human-curated data (versions, PURLs, supplier info) that improves accuracy. If no baseline exists,
skip this step entirely and proceed to Step 9.

Merging targets only the CycloneDX output (`sbom-cyclonedx.json`). The SPDX output remains
the pure auto-detection result because Dependency-Track uses CycloneDX exclusively.

**8a. Run the merge script:**

```bash
python3 <skill-path>/scripts/merge_baseline_sbom.py \
  sbom-cyclonedx.json \
  previous-sbom.json \
  --config .sbom-config.json \
  --output-sbom sbom-cyclonedx.json \
  --output-report merge-report.json
```

This overwrites `sbom-cyclonedx.json` with the merged result and produces `merge-report.json`
describing what changed.

**8b. Review merge-report.json for anomalies:**

Read `merge-report.json` and check:

- **Match plausibility**: For each match, verify the paired components are genuinely the same library.
  A name-normalized match like "zlib" ↔ "Zlib" is safe, but watch for cases where short or generic
  names collide (e.g., "utils" matching an unrelated "Utils" library). Flag any suspicious matches
  to the user.
- **Overwritten attributes**: List each attribute where the PR value replaced the baseline value.
  These are expected for `licenses` and `hashes` but worth noting for the user.
- **New components**: Components found in the PR but absent from the baseline — expected when
  new dependencies are added.
- **Removed components**: Components in the baseline but not in the PR — could indicate a
  dependency was removed, or that the detection missed something. Flag removals for the user
  to confirm they are intentional.

**8c. Append merge summary to sbom-analysis-report.md:**

Add a "ベースラインからの変更" section to the end of `sbom-analysis-report.md`. Format:

```markdown
## ベースラインからの変更

### 上書きされた属性
- cJSON の licenses を上書きしました (ベースライン: MIT → PR: MIT AND ISC)
- zlib の hashes を上書きしました

### ベースラインから引き継いだ属性
- cJSON の version をベースラインから引き継ぎました (1.7.15)
- cJSON の purl をベースラインから引き継ぎました (pkg:generic/cjson@1.7.15)

### 新規コンポーネント
- new-lib (手動レビュー推奨: NOASSERTION の属性あり)

### 削除されたコンポーネント
- old-lib (ベースラインに存在、PR で未検出 — 意図的な削除か確認してください)
```

Omit any subsection that has no entries (e.g., if nothing was overwritten, skip "上書きされた属性").

### Step 9: Validate

Run validation on the generated files:

```bash
python3 <skill-path>/scripts/validate_sbom.py sbom-spdx.json
python3 <skill-path>/scripts/validate_sbom.py sbom-cyclonedx.json
```

Report any errors or warnings. Fix issues and regenerate if needed.

### Step 10: Present Results

Summarize the generated SBOM to the user:

1. **Component table**: Name, version, license, detection method for each component
2. **Confidence issues**: Components with `NOASSERTION` for version, license, or supplier
3. **Recommendations**: Suggest `.sbom-config.json` entries to improve accuracy
4. **File statistics**: Total scanned, included, excluded, by component

---

## Configuration Reference (`.sbom-config.json`)

All fields are optional. The file itself is optional.

```json
{
  "project_name": "My Project",
  "project_type": "application | firmware | library",
  "project_version": "1.0.0",
  "primary_copyright_holder": "Example Corp",
  "project_license": "MIT",
  "deps_directories": ["third-party/", "deps/", "vendor/"],
  "exclude_patterns": ["tests/", "docs/", "*.o", "*.d"],
  "license_overrides": {
    "third-party/cjson": "MIT",
    "third-party/mbedtls": "Apache-2.0"
  },
  "component_overrides": {
    "third-party/cjson": {
      "name": "cJSON",
      "version": "1.7.15",
      "supplier": "Dave Gamble"
    }
  },
  "copyright_holder_aliases": {
    "Canonical Name": ["Variant 1", "Variant 2"]
  },
  "sbom_completeness": "complete | incomplete | unknown",
  "completeness_note": "Reason for incompleteness"
}
```

### Key fields explained

- **`deps_directories`**: Directories containing third-party code. Files under these paths are treated as separate components. Default: `["deps/", "third_party/", "vendor/", "external/"]`
- **`license_overrides`**: When ScanCode's auto-detection is wrong or incomplete, manually specify the correct SPDX license expression for a path prefix.
- **`component_overrides`**: Set exact name, version, or supplier for a component when auto-detection isn't sufficient.
- **`copyright_holder_aliases`**: Normalize variations of the same organization name (e.g., `"Redis Ltd."` <- `["Redis Labs", "Redis Labs Ltd."]`).
- **`exclude_patterns`**: Glob-like patterns for files to exclude. Supports `*.ext` (extension), `dir/` (directory), and substring matching.

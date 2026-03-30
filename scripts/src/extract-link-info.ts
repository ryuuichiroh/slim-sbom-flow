import { readFile, writeFile } from 'fs/promises';

interface CompileCommand {
  directory: string;
  command: string;
  file: string;
}

interface LinkInfo {
  libraries: string[];
  include_paths: string[];
  source_files: string[];
}

export function extractLinkInfo(compileCommands: CompileCommand[]): LinkInfo {
  const libraries = new Set<string>();
  const includePaths = new Set<string>();
  const sourceFiles = new Set<string>();

  for (const cmd of compileCommands) {
    const commandParts = cmd.command.split(/\s+/);

    for (let i = 0; i < commandParts.length; i++) {
      const part = commandParts[i];

      if (part.startsWith('-l')) {
        const lib = part.slice(2) || commandParts[i + 1];
        if (lib) {
          libraries.add(lib);
        }
      }

      if (part.startsWith('-I')) {
        const path = part.slice(2) || commandParts[i + 1];
        if (path) {
          includePaths.add(path);
        }
      }
    }

    if (cmd.file) {
      sourceFiles.add(cmd.file);
    }
  }

  return {
    libraries: Array.from(libraries).sort(),
    include_paths: Array.from(includePaths).sort(),
    source_files: Array.from(sourceFiles).sort(),
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];

  if (!inputPath || !outputPath) {
    console.error('Usage: extract-link-info.js <compile_commands.json> <output_path>');
    process.exit(1);
  }

  const compileCommands = JSON.parse(await readFile(inputPath, 'utf-8')) as CompileCommand[];
  const linkInfo = extractLinkInfo(compileCommands);

  await writeFile(outputPath, JSON.stringify(linkInfo, null, 2));
  console.log(`Link info extracted: ${linkInfo.libraries.length} libraries, ${linkInfo.include_paths.length} include paths`);
}

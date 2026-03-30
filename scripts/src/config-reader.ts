import { readFile } from 'fs/promises';
import yaml from 'js-yaml';
import { SSFConfig, CycloneDXBOM } from './types.js';

export async function readSSFConfig(configPath: string): Promise<SSFConfig> {
  try {
    const content = await readFile(configPath, 'utf-8');
    return yaml.load(content) as SSFConfig;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return {};
    }
    throw error;
  }
}

export async function getProjectName(config: SSFConfig, sbom: CycloneDXBOM): Promise<string> {
  if (config.project_name) {
    return config.project_name;
  }

  const componentName = sbom.metadata?.component?.name;
  if (!componentName) {
    throw new Error('project_name not specified in config and SBOM metadata.component.name not found');
  }

  return componentName;
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const configPath = process.argv[2];
  const fieldName = process.argv[3];

  if (!configPath || !fieldName) {
    console.error('Usage: config-reader.js <config-file> <field-name>');
    process.exit(1);
  }

  try {
    const config = await readSSFConfig(configPath);
    const value = config[fieldName as keyof SSFConfig];
    console.log(value !== undefined && value !== null ? String(value) : '');
    process.exit(0);
  } catch (error) {
    console.error(`Error reading config file: ${error}`);
    process.exit(1);
  }
}

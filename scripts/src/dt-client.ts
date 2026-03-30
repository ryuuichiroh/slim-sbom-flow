import { CycloneDXBOM } from './types.js';

export class DTClient {
  private baseUrl: string;
  private apiKey: string;
  private secretToken?: string;

  constructor(baseUrl: string, apiKey: string, secretToken?: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.secretToken = secretToken;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'X-Api-Key': this.apiKey,
      'Content-Type': 'application/json',
    };

    if (this.secretToken) {
      headers['x-ssf-secret-token'] = this.secretToken;
    }

    return headers;
  }

  async getSBOM(projectName: string, version: string): Promise<CycloneDXBOM> {
    // Step 1: Get project UUID by name and version
    const projectUrl = `${this.baseUrl}/api/v1/project?name=${encodeURIComponent(projectName)}`;

    const projectResponse = await fetch(projectUrl, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!projectResponse.ok) {
      throw new Error(`Failed to get project from Dependency-Track: ${projectResponse.status} ${projectResponse.statusText}`);
    }

    const projects = await projectResponse.json() as Array<{ uuid: string; version: string; name: string }>;

    if (projects.length === 0) {
      throw new Error(`Project not found: ${projectName}`);
    }

    const project = projects.find(p => p.version === version);
    if (!project) {
      const availableVersions = projects.map(p => p.version).join(', ');
      throw new Error(`Version ${version} not found for project ${projectName}. Available versions: ${availableVersions}`);
    }

    // Step 2: Get SBOM using project UUID
    const sbomUrl = `${this.baseUrl}/api/v1/bom/cyclonedx/project/${project.uuid}`;

    const sbomResponse = await fetch(sbomUrl, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!sbomResponse.ok) {
      throw new Error(`Failed to get SBOM from Dependency-Track: ${sbomResponse.status} ${sbomResponse.statusText}`);
    }

    return await sbomResponse.json() as CycloneDXBOM;
  }
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const baseUrl = process.env.DT_BASE_URL;
  const apiKey = process.env.DT_API_KEY;
  const secretToken = process.env.SSF_SECRET_TOKEN;

  if (!baseUrl || !apiKey) {
    console.error('DT_BASE_URL and DT_API_KEY environment variables are required');
    process.exit(1);
  }

  const projectName = process.argv[2];
  const version = process.argv[3];
  const outputPath = process.argv[4];

  if (!projectName || !version || !outputPath) {
    console.error('Usage: dt-client.js <project_name> <version> <output_path>');
    process.exit(1);
  }

  const client = new DTClient(baseUrl, apiKey, secretToken);

  try {
    const sbom = await client.getSBOM(projectName, version);
    const { writeFile } = await import('fs/promises');
    await writeFile(outputPath, JSON.stringify(sbom, null, 2));
    console.log(`SBOM saved to ${outputPath}`);
  } catch (error) {
    console.error('Error:', (error as Error).message);
    process.exit(1);
  }
}

import { readFile, writeFile } from 'fs/promises';
import { CycloneDXBOM, Component, DiffResult, ComponentDiff } from './types.js';

function getComponentKey(component: Component): string {
  if (component.purl) {
    return component.purl;
  }
  const parts = [component.name];
  if (component.group) {
    parts.unshift(component.group);
  }
  return parts.join(':');
}

function getComponentVersion(component: Component): string | undefined {
  return component.version;
}

function componentsMatch(a: Component, b: Component): boolean {
  if (a.purl && b.purl) {
    const aPurl = a.purl.split('@')[0];
    const bPurl = b.purl.split('@')[0];
    return aPurl === bPurl;
  }

  if (a.name !== b.name) {
    return false;
  }

  if (a.group || b.group) {
    return a.group === b.group;
  }

  return true;
}

export function diffSBOMs(current: CycloneDXBOM, previous: CycloneDXBOM, baselineVersion?: string): DiffResult {
  const currentComponents = current.components || [];
  const previousComponents = previous.components || [];

  const changes: ComponentDiff[] = [];
  let unchanged = 0;

  const previousMap = new Map<string, Component>();
  for (const comp of previousComponents) {
    previousMap.set(getComponentKey(comp), comp);
  }

  const processedPrevious = new Set<string>();

  for (const currentComp of currentComponents) {
    const key = getComponentKey(currentComp);
    const previousComp = previousMap.get(key);

    if (previousComp) {
      processedPrevious.add(key);
      const currentVersion = getComponentVersion(currentComp);
      const previousVersion = getComponentVersion(previousComp);

      if (currentVersion !== previousVersion) {
        changes.push({
          type: 'updated',
          component: currentComp,
          previous_version: previousVersion,
        });
      } else {
        unchanged++;
      }
    } else {
      let found = false;
      for (const prevComp of previousComponents) {
        if (componentsMatch(currentComp, prevComp)) {
          processedPrevious.add(getComponentKey(prevComp));
          const currentVersion = getComponentVersion(currentComp);
          const previousVersion = getComponentVersion(prevComp);

          if (currentVersion !== previousVersion) {
            changes.push({
              type: 'updated',
              component: currentComp,
              previous_version: previousVersion,
            });
          } else {
            unchanged++;
          }
          found = true;
          break;
        }
      }

      if (!found) {
        changes.push({
          type: 'added',
          component: currentComp,
        });
      }
    }
  }

  for (const prevComp of previousComponents) {
    const key = getComponentKey(prevComp);
    if (!processedPrevious.has(key)) {
      changes.push({
        type: 'removed',
        component: prevComp,
      });
    }
  }

  const summary = {
    added: changes.filter(c => c.type === 'added').length,
    removed: changes.filter(c => c.type === 'removed').length,
    updated: changes.filter(c => c.type === 'updated').length,
    unchanged,
  };

  return {
    baseline_version: baselineVersion,
    has_baseline: !!baselineVersion,
    summary,
    changes,
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const currentPath = process.argv[2];
  const previousPath = process.argv[3];
  const outputPath = process.argv[4];
  const baselineVersion = process.argv[5];

  if (!currentPath || !previousPath || !outputPath) {
    console.error('Usage: diff-checker.js <current_sbom> <previous_sbom> <output_path> [baseline_version]');
    process.exit(1);
  }

  const currentSBOM = JSON.parse(await readFile(currentPath, 'utf-8')) as CycloneDXBOM;
  const previousSBOM = JSON.parse(await readFile(previousPath, 'utf-8')) as CycloneDXBOM;

  const diff = diffSBOMs(currentSBOM, previousSBOM, baselineVersion);
  await writeFile(outputPath, JSON.stringify(diff, null, 2));
  console.log(`Diff result saved to ${outputPath}`);
  console.log(`Summary: +${diff.summary.added} -${diff.summary.removed} ~${diff.summary.updated} =${diff.summary.unchanged}`);
}

import { defaultConfiguration, type TestWorkspace } from './model';

export function createCleanWorkspace(): TestWorkspace {
  return {
    id: 'clean',
    schemaVersion: 2,
    status: 'draft',
    currentStage: 'configuration',
    configuration: { ...defaultConfiguration },
    questions: [],
    evaluation: [],
  };
}

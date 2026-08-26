import { workflowStages, type TestWorkspace, type WorkflowStage } from '../../entities/workspace/model';

export function getStageState(
  workspace: TestWorkspace,
  stage: WorkflowStage,
): 'locked' | 'active' | 'working' | 'complete' {
  const currentIndex = workflowStages.indexOf(workspace.currentStage);
  const stageIndex = workflowStages.indexOf(stage);

  if (stage === 'upload' && workspace.manualUpload) return 'working';
  if (stageIndex < currentIndex) return 'complete';
  if (stageIndex > currentIndex) return 'locked';
  if (workspace.status === 'generating' && (stage === 'configuration' || stage === 'questions')) {
    return 'working';
  }
  if (stage === 'evaluation' && workspace.status === 'evaluating') {
    return 'working';
  }
  return 'active';
}

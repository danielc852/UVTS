import { workflowStages, type TestWorkspace, type WorkflowStage } from '../../shared/model/workspace';

export function getStageState(
  workspace: TestWorkspace,
  stage: WorkflowStage,
): 'locked' | 'active' | 'working' | 'complete' {
  const currentIndex = workflowStages.indexOf(workspace.currentStage);
  const stageIndex = workflowStages.indexOf(stage);

  if (stageIndex < currentIndex) return 'complete';
  if (stageIndex > currentIndex) return 'locked';
  if (stage === 'evaluation' && workspace.evaluation.some((item) => item.status === 'checking' || item.status === 'waiting')) {
    return 'working';
  }
  return 'active';
}

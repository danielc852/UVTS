import { Banner } from '@astryxdesign/core/Banner';
import { useQuery } from '@tanstack/react-query';
import { useLocation, useParams } from 'react-router-dom';

import { createCleanWorkspace } from '../../entities/workspace/clean';
import {
  workflowStages,
  type TestWorkspace,
  type WorkflowStage,
} from '../../entities/workspace/model';
import { queryKeys } from '../../entities/workspace/query';
import { useTestEvents } from '../../features/evaluation/useEvaluationEvents';
import { isMockWorkspaceId } from '../../mocks/workspace-ids';
import { loadWorkspace } from './load-workspace';
import { WorkspaceView } from './WorkspaceView';

function initialWorkspaceStage(
  workspace: TestWorkspace,
  showUpload: boolean,
): WorkflowStage {
  const canShowUpload =
    workflowStages.indexOf('upload') <= workflowStages.indexOf(workspace.currentStage);
  if ((showUpload && canShowUpload) || workspace.manualUpload) return 'upload';

  const errorStage = workspace.error?.stage;
  const canShowErrorStage =
    errorStage !== undefined &&
    workflowStages.indexOf(errorStage) <= workflowStages.indexOf(workspace.currentStage);
  if (canShowErrorStage) return errorStage;

  return workspace.currentStage;
}

export function WorkspacePage() {
  const { testId } = useParams();
  const location = useLocation();
  const queryId = testId ?? 'clean';
  const query = useQuery({
    queryKey: queryKeys.test(queryId),
    queryFn: () => (testId ? loadWorkspace(testId) : createCleanWorkspace()),
    retry: false,
  });

  const usesLiveApi = Boolean(testId) && !isMockWorkspaceId(testId ?? '');
  useTestEvents(
    testId ?? '',
    Boolean(testId) &&
      usesLiveApi &&
      (Boolean(query.data?.manualUpload) ||
        query.data?.status === 'generating' ||
        query.data?.status === 'evaluating'),
  );

  if (query.isPending) {
    return <div className="workspace"><p role="status">Loading your test…</p></div>;
  }

  if (query.isError || !query.data) {
    return (
      <div className="workspace">
        <h1>Check a manual</h1>
        <Banner
          status="error"
          title="This test could not be opened"
          description="Check the link or return to a clean workspace."
        />
        <a href="/">Open a clean workspace</a>
      </div>
    );
  }

  const workspace = query.data;
  const routeState = location.state as { showUpload?: boolean } | null;
  const initialStage = initialWorkspaceStage(workspace, Boolean(routeState?.showUpload));
  return <WorkspaceView workspace={workspace} initialStage={initialStage} />;
}

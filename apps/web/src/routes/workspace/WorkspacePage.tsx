import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useEffect, useState } from 'react';
import { useLocation, useParams } from 'react-router-dom';

import { getTestWorkspace } from '../../api/workspaces';
import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { queryKeys } from '../../api/query-keys';
import { EvaluationSection } from '../../features/evaluation/EvaluationSection';
import { useTestEvents } from '../../features/evaluation/useEvaluationEvents';
import { ManualSection } from '../../features/manual/ManualSection';
import { QuestionsSection } from '../../features/questions/QuestionsSection';
import { WorkflowOverview } from '../../shared/ui/WorkflowOverview';
import { workflowStages, type TestWorkspace, type WorkflowStage } from '../../shared/model/workspace';
import { getStageState } from './stage-state';

const ConfigurationSection = lazy(() =>
  import('../../features/configuration/ConfigurationSection').then((module) => ({
    default: module.ConfigurationSection,
  })),
);
const ReportSection = lazy(() =>
  import('../../features/report/ReportSection').then((module) => ({ default: module.ReportSection })),
);

const stepLabels: Record<WorkflowStage, string> = {
  configuration: 'Product setup',
  questions: 'Review and confirm questions',
  upload: 'Upload manual',
  evaluation: 'Evaluation',
  report: 'Report',
};

function WorkspaceStep({ workspace, stage }: { workspace: TestWorkspace; stage: WorkflowStage }) {
  const state = getStageState(workspace, stage);
  switch (stage) {
    case 'configuration':
      return (
        <Suspense fallback={<p role="status">Loading question settings…</p>}>
          <ConfigurationSection
            testId={workspace.id === 'clean' ? undefined : workspace.id}
            state={state}
            configuration={workspace.configuration}
            error={workspace.error}
            isLocked={workspace.questionSet?.status === 'confirmed'}
            isBusy={workspace.status === 'generating'}
          />
        </Suspense>
      );
    case 'questions':
      return <QuestionsSection state={state} workspace={workspace} />;
    case 'upload':
      return <ManualSection workspace={workspace} state={state} />;
    case 'evaluation':
      return (
        <EvaluationSection
          state={state}
          questions={workspace.questions}
          evaluation={workspace.evaluation}
          testId={workspace.id}
        />
      );
    case 'report':
      return (
        <Suspense fallback={<p role="status">Loading report…</p>}>
          <ReportSection
            state={state === 'locked' ? 'locked' : 'active'}
            report={workspace.report}
            testId={workspace.id}
          />
        </Suspense>
      );
  }
}

export function WorkspacePage() {
  const { testId } = useParams();
  const location = useLocation();
  const queryId = testId ?? 'clean';
  const query = useQuery({
    queryKey: queryKeys.test(queryId),
    queryFn: () => {
      if (!testId) {
        const cleanWorkspace = getWorkspaceFixture('clean');
        if (!cleanWorkspace) throw new Error('CLEAN_WORKSPACE_MISSING');
        return Promise.resolve(cleanWorkspace);
      }
      return getTestWorkspace(testId);
    },
    retry: false,
  });

  const usesLiveApi = !testId || !getWorkspaceFixture(testId);
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
  const errorStage = workspace.error?.stage;
  const canShowUpload =
    workflowStages.indexOf('upload') <= workflowStages.indexOf(workspace.currentStage);
  const canShowErrorStage =
    errorStage !== undefined &&
    workflowStages.indexOf(errorStage) <= workflowStages.indexOf(workspace.currentStage);
  const initialStage =
    (routeState?.showUpload && canShowUpload) || workspace.manualUpload
      ? 'upload'
      : canShowErrorStage
        ? errorStage
        : workspace.currentStage;
  return (
    <WorkspaceView workspace={workspace} initialStage={initialStage} />
  );
}

function WorkspaceView({
  workspace,
  initialStage,
}: {
  workspace: TestWorkspace;
  initialStage: WorkflowStage;
}) {
  const [viewedStage, setViewedStage] = useState<WorkflowStage>(initialStage);
  const currentIndex = workflowStages.indexOf(workspace.currentStage);
  const viewedIndex = workflowStages.indexOf(viewedStage);

  useEffect(() => {
    setViewedStage(initialStage);
  }, [initialStage, workspace.id]);

  const showStage = (stage: WorkflowStage) => {
    if (workflowStages.indexOf(stage) > currentIndex) return;
    setViewedStage(stage);
    requestAnimationFrame(() =>
      document
        .getElementById(`stage-${workflowStages.indexOf(stage) + 1}-heading`)
        ?.focus(),
    );
  };

  return (
    <div className="workspace">
      <header className="workspace-intro">
        <p className="workspace-eyebrow">Manual coverage test</p>
        <h1>Check a manual</h1>
        <p>Find information that may be missing from a product manual.</p>
        <WorkflowOverview
          currentStage={workspace.currentStage}
          viewedStage={viewedStage}
          onStageChange={showStage}
        />
      </header>
      <section className="workflow-step" aria-label={`Step ${viewedIndex + 1} of ${workflowStages.length}`}>
        <WorkspaceStep workspace={workspace} stage={viewedStage} />
        <nav className="step-navigation" aria-label="Workflow steps">
          <div>
            {viewedIndex > 0 ? (
              <Button
                label={`Back to ${stepLabels[workflowStages[viewedIndex - 1]]}`}
                variant="secondary"
                onClick={() => showStage(workflowStages[viewedIndex - 1])}
              />
            ) : null}
          </div>
          <div>
            {viewedIndex < currentIndex ? (
              <Button
                label={`Continue to ${stepLabels[workflowStages[viewedIndex + 1]]}`}
                variant="primary"
                onClick={() => showStage(workflowStages[viewedIndex + 1])}
              />
            ) : null}
          </div>
        </nav>
      </section>
    </div>
  );
}

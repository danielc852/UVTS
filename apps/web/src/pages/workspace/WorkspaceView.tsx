import { Button } from '@astryxdesign/core/Button';
import { Suspense, useEffect, useRef, useState } from 'react';

import {
  workflowStages,
  type TestWorkspace,
  type WorkflowStage,
} from '../../entities/workspace/model';
import { WorkflowOverview } from '../../shared/ui/WorkflowOverview';
import { getStageState } from './stage-state';
import {
  ConfigurationSection,
  EvaluationSection,
  ManualSection,
  preloadWorkspaceStage,
  QuestionsSection,
  ReportSection,
} from './stage-modules';

const stepLabels: Record<WorkflowStage, string> = {
  configuration: 'Product setup',
  questions: 'Review and confirm questions',
  upload: 'Upload manual',
  evaluation: 'Evaluation',
  report: 'Report',
};

const stageFallbacks: Record<WorkflowStage, string> = {
  configuration: 'Loading question settings…',
  questions: 'Loading questions…',
  upload: 'Loading manual workspace…',
  evaluation: 'Loading evaluation…',
  report: 'Loading report…',
};

function FocusStageHeading({ stage, requestId }: { stage: WorkflowStage; requestId: number }) {
  useEffect(() => {
    if (requestId > 0) focusStageHeading(stage);
  }, [requestId, stage]);

  return null;
}

function WorkspaceStep({
  workspace,
  stage,
  focusRequestId,
}: {
  workspace: TestWorkspace;
  stage: WorkflowStage;
  focusRequestId: number;
}) {
  const state = getStageState(workspace, stage);
  let content;

  switch (stage) {
    case 'configuration':
      content = (
        <ConfigurationSection
          testId={workspace.id === 'clean' ? undefined : workspace.id}
          state={state}
          configuration={workspace.configuration}
          error={workspace.error}
          isLocked={workspace.questionSet?.status === 'confirmed'}
          isBusy={workspace.status === 'generating'}
        />
      );
      break;
    case 'questions':
      content = <QuestionsSection state={state} workspace={workspace} />;
      break;
    case 'upload':
      content = <ManualSection workspace={workspace} state={state} />;
      break;
    case 'evaluation':
      content = (
        <EvaluationSection
          state={state}
          questions={workspace.questions}
          evaluation={workspace.evaluation}
          testId={workspace.id}
        />
      );
      break;
    case 'report':
      content = (
        <ReportSection
          state={state === 'locked' ? 'locked' : 'active'}
          report={workspace.report}
          testId={workspace.id}
        />
      );
      break;
  }

  return (
    <Suspense fallback={<p role="status">{stageFallbacks[stage]}</p>}>
      <FocusStageHeading stage={stage} requestId={focusRequestId} />
      {content}
    </Suspense>
  );
}

function focusStageHeading(stage: WorkflowStage) {
  requestAnimationFrame(() =>
    document
      .getElementById(`stage-${workflowStages.indexOf(stage) + 1}-heading`)
      ?.focus(),
  );
}

export function WorkspaceView({
  workspace,
  initialStage,
}: {
  workspace: TestWorkspace;
  initialStage: WorkflowStage;
}) {
  const [viewedStage, setViewedStage] = useState<WorkflowStage>(initialStage);
  const [focusRequestId, setFocusRequestId] = useState(0);
  const previousWorkspace = useRef({ id: workspace.id, currentStage: workspace.currentStage });
  const currentIndex = workflowStages.indexOf(workspace.currentStage);
  const viewedIndex = workflowStages.indexOf(viewedStage);

  useEffect(() => {
    setViewedStage(initialStage);
    const previous = previousWorkspace.current;
    const stageAdvanced =
      previous.id === workspace.id &&
      workflowStages.indexOf(workspace.currentStage) >
        workflowStages.indexOf(previous.currentStage);
    previousWorkspace.current = { id: workspace.id, currentStage: workspace.currentStage };
    if (stageAdvanced) setFocusRequestId((current) => current + 1);
  }, [initialStage, workspace.id, workspace.currentStage]);

  useEffect(() => {
    const nextStage = workflowStages[currentIndex + 1];
    if (nextStage) preloadWorkspaceStage(nextStage);
  }, [currentIndex]);

  const showStage = (stage: WorkflowStage) => {
    if (workflowStages.indexOf(stage) > currentIndex) return;
    setViewedStage(stage);
    setFocusRequestId((current) => current + 1);
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
          onStagePreload={preloadWorkspaceStage}
        />
      </header>
      <section
        className="workflow-step"
        aria-label="Current workflow stage"
      >
        <WorkspaceStep
          workspace={workspace}
          stage={viewedStage}
          focusRequestId={focusRequestId}
        />
        <nav className="step-navigation" aria-label="Workflow navigation">
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

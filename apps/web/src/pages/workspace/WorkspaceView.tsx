import { Button } from '@astryxdesign/core/Button';
import { Suspense, useEffect, useState } from 'react';

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

function WorkspaceStep({ workspace, stage }: { workspace: TestWorkspace; stage: WorkflowStage }) {
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

  return <Suspense fallback={<p role="status">{stageFallbacks[stage]}</p>}>{content}</Suspense>;
}

export function WorkspaceView({
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

  useEffect(() => {
    const nextStage = workflowStages[currentIndex + 1];
    if (nextStage) preloadWorkspaceStage(nextStage);
  }, [currentIndex]);

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
          onStagePreload={preloadWorkspaceStage}
        />
      </header>
      <section
        className="workflow-step"
        aria-label={`Step ${viewedIndex + 1} of ${workflowStages.length}`}
      >
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

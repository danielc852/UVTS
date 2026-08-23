import { Banner } from '@astryxdesign/core/Banner';
import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { useParams } from 'react-router-dom';

import { getTestWorkspace } from '../../api/workspaces';
import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { queryKeys } from '../../api/query-keys';
import { EvaluationSection } from '../../features/evaluation/EvaluationSection';
import { useEvaluationEvents } from '../../features/evaluation/useEvaluationEvents';
import { ManualSection } from '../../features/manual/ManualSection';
import { QuestionsSection } from '../../features/questions/QuestionsSection';
import { StageSection } from '../../shared/ui/StageSection';
import { WorkflowOverview } from '../../shared/ui/WorkflowOverview';
import { getStageState } from './stage-state';

const ConfigurationSection = lazy(() =>
  import('../../features/configuration/ConfigurationSection').then((module) => ({
    default: module.ConfigurationSection,
  })),
);
const ReportSection = lazy(() =>
  import('../../features/report/ReportSection').then((module) => ({ default: module.ReportSection })),
);

export function WorkspacePage() {
  const { testId } = useParams();
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

  useEvaluationEvents(
    testId ?? '',
    Boolean(testId) && query.data?.currentStage === 'evaluation' && import.meta.env.VITE_ENABLE_MOCKS === 'false',
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
  const configurationState = getStageState(workspace, 'configuration');
  const questionsState = getStageState(workspace, 'questions');
  const evaluationState = getStageState(workspace, 'evaluation');
  const reportState = getStageState(workspace, 'report');

  return (
    <div className="workspace">
      <header className="workspace-intro">
        <h1>Check a manual</h1>
        <p>Find information that may be missing from a product manual.</p>
        <WorkflowOverview currentStage={workspace.currentStage} />
      </header>
      <ManualSection manual={workspace.manual} error={workspace.error} />
      {configurationState === 'locked' ? (
        <StageSection number={2} title="Generate questions" state="locked" lockedText="Upload a manual to continue." />
      ) : (
        <Suspense fallback={<p role="status">Loading question settings…</p>}>
          <ConfigurationSection
            state={configurationState === 'working' ? 'active' : configurationState}
            configuration={workspace.configuration}
            error={workspace.error}
          />
        </Suspense>
      )}
      <QuestionsSection
        state={questionsState === 'working' ? 'active' : questionsState}
        questions={workspace.questions}
      />
      <EvaluationSection state={evaluationState} questions={workspace.questions} evaluation={workspace.evaluation} />
      {reportState === 'active' ? (
        <Suspense fallback={<p role="status">Loading report…</p>}>
          <ReportSection state="active" report={workspace.report} />
        </Suspense>
      ) : (
        <StageSection number={5} title="Report" state="locked" lockedText="Complete the evaluation to see the report." />
      )}
    </div>
  );
}

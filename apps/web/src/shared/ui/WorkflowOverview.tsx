import { workflowStages, type WorkflowStage } from '../model/workspace';

const labels: Record<WorkflowStage, string> = {
  upload: 'Upload',
  configuration: 'Questions',
  questions: 'Review',
  evaluation: 'Evaluate',
  report: 'Report',
};

export function WorkflowOverview({ currentStage }: { currentStage: WorkflowStage }) {
  const currentIndex = workflowStages.indexOf(currentStage);

  return (
    <nav aria-label="Test progress">
      <ol className="workflow-overview">
        {workflowStages.map((stage, index) => (
          <li key={stage} aria-current={stage === currentStage ? 'step' : undefined}>
            <span>{labels[stage]}</span>
            <small>{index < currentIndex ? 'Complete' : index === currentIndex ? 'Current' : 'Locked'}</small>
          </li>
        ))}
      </ol>
    </nav>
  );
}

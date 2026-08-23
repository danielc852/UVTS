import { workflowStages, type WorkflowStage } from '../model/workspace';

const labels: Record<WorkflowStage, string> = {
  upload: 'Upload',
  configuration: 'Questions',
  questions: 'Review',
  evaluation: 'Evaluate',
  report: 'Report',
};

interface WorkflowOverviewProps {
  currentStage: WorkflowStage;
  viewedStage: WorkflowStage;
  onStageChange: (stage: WorkflowStage) => void;
}

export function WorkflowOverview({ currentStage, viewedStage, onStageChange }: WorkflowOverviewProps) {
  const currentIndex = workflowStages.indexOf(currentStage);

  return (
    <nav aria-label="Test progress">
      <ol className="workflow-overview">
        {workflowStages.map((stage, index) => (
          <li
            key={stage}
            data-selected={stage === viewedStage ? 'true' : undefined}
            data-state={index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'locked'}
          >
            <button
              type="button"
              aria-current={stage === viewedStage ? 'step' : undefined}
              disabled={index > currentIndex}
              onClick={() => onStageChange(stage)}
            >
              <span className="workflow-step-label">
                <span className="workflow-step-marker" aria-hidden="true">
                  {index < currentIndex ? '✓' : index + 1}
                </span>
                <span>{labels[stage]}</span>
              </span>
              <small>{index < currentIndex ? 'Complete' : index === currentIndex ? 'Current' : 'Locked'}</small>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}

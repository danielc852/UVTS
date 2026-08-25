import { lazy } from 'react';

import type { WorkflowStage } from '../../entities/workspace/model';

const stageLoaders = {
  configuration: () => import('../../features/configuration/ConfigurationSection'),
  questions: () => import('../../features/questions/QuestionsSection'),
  upload: () => import('../../features/manual/ManualSection'),
  evaluation: () => import('../../features/evaluation/EvaluationSection'),
  report: () => import('../../features/report/ReportSection'),
};

export const ConfigurationSection = lazy(() =>
  stageLoaders.configuration().then((module) => ({ default: module.ConfigurationSection })),
);

export const QuestionsSection = lazy(() =>
  stageLoaders.questions().then((module) => ({ default: module.QuestionsSection })),
);

export const ManualSection = lazy(() =>
  stageLoaders.upload().then((module) => ({ default: module.ManualSection })),
);

export const EvaluationSection = lazy(() =>
  stageLoaders.evaluation().then((module) => ({ default: module.EvaluationSection })),
);

export const ReportSection = lazy(() =>
  stageLoaders.report().then((module) => ({ default: module.ReportSection })),
);

export function preloadWorkspaceStage(stage: WorkflowStage): void {
  void stageLoaders[stage]();
}

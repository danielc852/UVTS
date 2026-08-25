import { Banner } from '@astryxdesign/core/Banner';
import { Section } from '@astryxdesign/core/Section';
import type { ReactNode } from 'react';

import { workflowStages, type WorkspaceError } from '../../entities/workspace/model';

type StagePresentation = 'locked' | 'active' | 'working' | 'complete';

interface StageSectionProps {
  number: number;
  title: string;
  state: StagePresentation;
  summary?: string;
  lockedText?: string;
  error?: WorkspaceError;
  children?: ReactNode;
}

export function StageSection({
  number,
  title,
  state,
  summary,
  lockedText,
  error,
  children,
}: StageSectionProps) {
  const headingId = `stage-${number}-heading`;

  return (
    <Section variant={state === 'locked' ? 'muted' : 'section'} padding={8}>
      <section
        aria-labelledby={headingId}
        aria-current={state === 'active' || state === 'working' ? 'step' : undefined}
      >
        <div className="stage-heading-row">
          <h2 id={headingId} tabIndex={-1}>
            {number}. {title}
          </h2>
          {state === 'complete' ? <span className="stage-status">Complete</span> : null}
          {state === 'working' ? <span className="stage-status" role="status">Working</span> : null}
        </div>
        {error?.stage === workflowStages[number - 1] ? (
          <Banner status="error" title={error.title} description={error.message} />
        ) : null}
        {state === 'locked' ? <p className="locked-text">{lockedText}</p> : null}
        {state === 'complete' && summary ? <p className="stage-summary">{summary}</p> : null}
        {state === 'active' || state === 'working' || state === 'complete' ? children : null}
      </section>
    </Section>
  );
}

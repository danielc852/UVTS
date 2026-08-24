import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Collapsible, CollapsibleGroup } from '@astryxdesign/core/Collapsible';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { EvaluationRequestError, retryReport } from '../../api/evaluation';
import { queryKeys } from '../../api/query-keys';
import type { CoverageStatus, Report } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

interface ReportSectionProps {
  state: 'locked' | 'active';
  report?: Report;
  testId: string;
}

const statusLabel: Record<CoverageStatus, string> = {
  found: 'Information found',
  partly_found: 'Information partly found',
  not_found: 'Information not found',
  failed: 'Failed',
};

const statusVariant: Record<CoverageStatus, 'success' | 'warning' | 'error'> = {
  found: 'success',
  partly_found: 'warning',
  not_found: 'error',
  failed: 'error',
};

export function ReportSection({ state, report, testId }: ReportSectionProps) {
  const queryClient = useQueryClient();
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string>();
  if (state === 'locked' || !report) {
    return (
      <StageSection
        number={5}
        title="Report"
        state="locked"
        lockedText="Complete the evaluation to see the report."
      />
    );
  }

  const total = Object.values(report.counts).reduce((sum, count) => sum + count, 0);

  const retry = async () => {
    setIsRetrying(true);
    setRetryError(undefined);
    try {
      const updated = await retryReport(testId);
      queryClient.setQueryData(queryKeys.test(updated.id), updated);
    } catch (error) {
      setRetryError(
        error instanceof EvaluationRequestError
          ? error.message
          : 'The report retry could not be started. Try again.',
      );
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <StageSection number={5} title="Report" state="active">
      {retryError ? <Banner status="error" title="Report retry failed" description={retryError} /> : null}
      {!report.isComplete ? (
        <Banner
          status="warning"
          title="Report incomplete"
          description={`${report.counts.failed} ${report.counts.failed === 1 ? 'question still needs' : 'questions still need'} to be checked.`}
          endContent={
            <Button
              label="Retry report"
              variant="secondary"
              size="sm"
              isLoading={isRetrying}
              onClick={() => void retry()}
            />
          }
        />
      ) : null}

      <section aria-labelledby="test-summary-heading">
        <h3 id="test-summary-heading">Test summary</h3>
        <p className="coverage-sentence">
          {report.counts.found} questions are covered out of {total} total questions.
        </p>
        <dl className="summary-grid">
          <div><dt>Information found</dt><dd>{report.counts.found}</dd></div>
          <div><dt>Information partly found</dt><dd>{report.counts.partly_found}</dd></div>
          <div><dt>Information not found</dt><dd>{report.counts.not_found}</dd></div>
          <div><dt>Failed</dt><dd>{report.counts.failed}</dd></div>
        </dl>
      </section>

      <section aria-labelledby="coverage-overview-heading">
        <h3 id="coverage-overview-heading">Coverage overview</h3>
        <p>The detailed results below show the manual evidence and gaps for each confirmed question.</p>
      </section>

      <section aria-labelledby="question-results-heading">
        <h3 id="question-results-heading">Question results</h3>
        <CollapsibleGroup type="multiple" hasDividers>
          {report.results.map((result, index) => (
            <Collapsible
              key={result.question.id}
              value={result.question.id}
              defaultIsOpen={index === 0}
              trigger={
                <span className="result-trigger">
                  <span>{index + 1}. {result.question.text}</span>
                  <Badge label={statusLabel[result.status]} variant={statusVariant[result.status]} />
                </span>
              }
            >
              <div className="result-details">
                <h4>Information needed</h4>
                <p>{result.informationNeeded}</p>
                <h4>Information found</h4>
                <p>{result.informationFound ?? 'No supporting information found.'}</p>
                {result.informationMissing ? (
                  <><h4>Information missing or unclear</h4><p>{result.informationMissing}</p></>
                ) : null}
                <h4>Page evidence</h4>
                {(result.evidence ?? []).length > 0 ? (
                  <ul>{(result.evidence ?? []).map((evidence) => <li key={`${result.question.id}-${evidence.page}`}>Page {evidence.page}: {evidence.extract}</li>)}</ul>
                ) : (
                  <p>No supporting information found.</p>
                )}
              </div>
            </Collapsible>
          ))}
        </CollapsibleGroup>
      </section>

      <section aria-labelledby="gaps-heading">
        <h3 id="gaps-heading">Main gaps</h3>
        {report.gaps.length > 0 ? (
          <ul>{report.gaps.map((gap) => <li key={gap.id}><strong>{gap.title}</strong> — {gap.whyItMatters} Affects {gap.affectedQuestionIds.join(', ')}.</li>)}</ul>
        ) : <p>The tested questions did not reveal missing information.</p>}
      </section>

      <section aria-labelledby="recommendations-heading">
        <h3 id="recommendations-heading">Recommendations</h3>
        <ul>{report.recommendations.map((recommendation) => <li key={recommendation.id}><strong>{recommendation.priority}:</strong> {recommendation.change} {recommendation.reason}</li>)}</ul>
      </section>

      <section aria-labelledby="follow-up-heading">
        <h3 id="follow-up-heading">Follow-up</h3>
        <ul>{report.followUpQuestions.map((question) => <li key={question}>{question}</li>)}</ul>
      </section>

      <Banner
        status="info"
        title="What this report means"
        description="UVTS checks whether information exists in this manual. It does not confirm that the information is correct, safe, clearly written, or complete for every possible user. Its suggestions do not replace legal, safety, or expert review."
      />
    </StageSection>
  );
}

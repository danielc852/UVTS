import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Card } from '@astryxdesign/core/Card';
import { Collapsible, CollapsibleGroup } from '@astryxdesign/core/Collapsible';
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@astryxdesign/core/SegmentedControl';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type CSSProperties } from 'react';

import { storeWorkspace } from '../../entities/workspace/query';
import type { CoverageStatus, Report } from '../../entities/workspace/model';
import { StageSection } from '../../shared/ui/StageSection';
import { ReportRequestError, retryReport } from './api';
import './ReportSection.css';

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

type ReportFilter = 'all' | 'attention' | 'covered' | 'failed';

const filterLabel: Record<ReportFilter, string> = {
  all: 'All',
  attention: 'Review',
  covered: 'Found',
  failed: 'Failed',
};

const statusFilter: Record<CoverageStatus, ReportFilter> = {
  found: 'covered',
  partly_found: 'attention',
  not_found: 'attention',
  failed: 'failed',
};

function matchesFilter(status: CoverageStatus, filter: ReportFilter): boolean {
  return filter === 'all' || statusFilter[status] === filter;
}

function resultStatus(status: CoverageStatus) {
  if (status === 'found') {
    return <span className="result-status-found">{statusLabel[status]}</span>;
  }
  return <Badge label={statusLabel[status]} variant={statusVariant[status]} />;
}

function reportRetryError(error: Error | null): string | undefined {
  if (!error) return undefined;
  if (error instanceof ReportRequestError) return error.message;
  return 'The report retry could not be started. Try again.';
}

export function ReportSection({ state, report, testId }: ReportSectionProps) {
  const [filter, setFilter] = useState<ReportFilter>('all');
  const queryClient = useQueryClient();
  const retryMutation = useMutation({
    mutationFn: () => retryReport(testId),
    onSuccess: (updated) => {
      setFilter('all');
      storeWorkspace(queryClient, updated);
    },
  });
  const retryError = reportRetryError(retryMutation.error);
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
  const attentionCount = report.counts.partly_found + report.counts.not_found + report.counts.failed;
  const coverageSegments = [
    { status: 'found', label: statusLabel.found, count: report.counts.found },
    { status: 'partly_found', label: statusLabel.partly_found, count: report.counts.partly_found },
    { status: 'not_found', label: statusLabel.not_found, count: report.counts.not_found },
    { status: 'failed', label: statusLabel.failed, count: report.counts.failed },
  ] satisfies Array<{ status: CoverageStatus; label: string; count: number }>;
  const filters = [
    { value: 'all', label: filterLabel.all, count: total },
    { value: 'attention', label: filterLabel.attention, count: attentionCount },
    { value: 'covered', label: filterLabel.covered, count: report.counts.found },
    { value: 'failed', label: filterLabel.failed, count: report.counts.failed },
  ] satisfies Array<{ value: ReportFilter; label: string; count: number }>;
  const visibleResults = report.results
    .map((result, index) => ({ result, number: index + 1 }))
    .filter(({ result }) => matchesFilter(result.status, filter));
  const questionNumberById = new Map(
    report.results.map((result, index) => [result.question.id, index + 1]),
  );
  const gapById = new Map(report.gaps.map((gap) => [gap.id, gap]));

  const revealQuestion = (questionId: string) => {
    setFilter('all');
    requestAnimationFrame(() => {
      const trigger = document
        .getElementById(`question-result-${questionId}`)
        ?.closest<HTMLButtonElement>('button');
      if (trigger?.getAttribute('aria-expanded') === 'false') trigger.click();
      trigger?.focus();
    });
  };

  return (
    <StageSection number={5} title="Report" state="active">
      <div className="report-dashboard">
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
                isLoading={retryMutation.isPending}
                onClick={() => retryMutation.mutate()}
              />
            }
          />
        ) : null}

        <section className="report-section report-summary" aria-labelledby="test-summary-heading">
          <h3 id="test-summary-heading">Test summary</h3>
          <p className="report-eyebrow">Coverage result</p>
          <p className="coverage-sentence">
            {report.counts.found} questions are covered out of {total} total questions.
          </p>
          <p className="report-summary-copy">
            Coverage means the manual contains the information needed to address the question.
          </p>
          <dl className="coverage-metrics">
            {coverageSegments.map((segment) => (
              <Card padding={3} key={segment.status}>
                <dt>{segment.label}</dt>
                <dd>{segment.count}</dd>
              </Card>
            ))}
          </dl>
        </section>

        <section className="report-section" aria-labelledby="coverage-overview-heading">
          <div className="report-section-heading">
            <div>
              <h3 id="coverage-overview-heading">Coverage overview</h3>
              <p>Select a section of the chart or use the filters to inspect matching questions.</p>
            </div>
          </div>
          <figure className="coverage-figure">
            <figcaption className="report-visually-hidden">
              Coverage breakdown for {total} questions
            </figcaption>
            <div className="coverage-bar" role="group" aria-label="Coverage breakdown">
              {coverageSegments.map((segment) =>
                segment.count > 0 ? (
                  <button
                    key={segment.status}
                    type="button"
                    className="coverage-bar-segment"
                    data-status={segment.status}
                    style={{ '--coverage-weight': segment.count } as CSSProperties}
                    aria-label={`${segment.label}: ${segment.count} of ${total}. Show matching results.`}
                    aria-pressed={filter === statusFilter[segment.status]}
                    onClick={() => setFilter(statusFilter[segment.status])}
                  />
                ) : null,
              )}
            </div>
            <ul className="coverage-legend" aria-label="Coverage values">
              {coverageSegments.map((segment) => (
                <li key={segment.status}>
                  <span className="coverage-legend-swatch" data-status={segment.status} aria-hidden="true" />
                  <span>{segment.label}</span>
                  <strong>{segment.count}</strong>
                </li>
              ))}
            </ul>
          </figure>
        </section>

        <section className="report-section" aria-labelledby="question-results-heading">
          <div className="report-results-heading">
            <div>
              <h3 id="question-results-heading">Question results</h3>
              <p>Open questions to compare what was found, what is missing, and the page evidence.</p>
            </div>
            <div className="report-filter-control">
              <SegmentedControl
                value={filter}
                onChange={(value) => setFilter(value as ReportFilter)}
                label="Filter question results"
                size="sm"
                layout="fill"
              >
                {filters.map((item) => (
                  <SegmentedControlItem
                    key={item.value}
                    value={item.value}
                    label={`${item.label} ${item.count}`}
                  />
                ))}
              </SegmentedControl>
            </div>
          </div>
          <p className="report-filter-summary" role="status">
            Showing {visibleResults.length} of {total} question results.
          </p>
          {visibleResults.length > 0 ? (
            <CollapsibleGroup
              key={report.source?.questionSetId ?? 'report-results'}
              type="multiple"
              defaultValue={report.results[0] ? [report.results[0].question.id] : []}
              hasDividers
            >
              {visibleResults.map(({ result, number }) => (
                <Collapsible
                  key={result.question.id}
                  value={result.question.id}
                  trigger={
                    <span className="result-trigger" id={`question-result-${result.question.id}`}>
                      <span>{number}. {result.question.text}</span>
                      {resultStatus(result.status)}
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
          ) : (
            <p className="report-empty-state">No questions match this filter.</p>
          )}
        </section>

        <section className="report-section" aria-labelledby="gaps-heading">
          <h3 id="gaps-heading">Main gaps</h3>
          {report.gaps.length > 0 ? (
            <ul className="report-action-list">
              {report.gaps.map((gap) => (
                <li key={gap.id}>
                  <div className="report-action-heading">
                    <strong>{gap.title}</strong>
                    <Badge
                      label={gap.kind === 'missing' ? 'Missing' : 'Incomplete'}
                      variant={gap.kind === 'missing' ? 'error' : 'warning'}
                    />
                  </div>
                  <p>{gap.whyItMatters}</p>
                  <div className="report-question-links" aria-label={`Questions affected by ${gap.title}`}>
                    <span>Affects</span>
                    {gap.affectedQuestionIds.map((questionId) => (
                      <button key={questionId} type="button" onClick={() => revealQuestion(questionId)}>
                        Question {questionNumberById.get(questionId) ?? questionId}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          ) : <p>The tested questions did not reveal missing information.</p>}
        </section>

        <section className="report-section" aria-labelledby="recommendations-heading">
          <h3 id="recommendations-heading">Recommendations</h3>
          {report.recommendations.length > 0 ? (
            <ol className="report-action-list report-recommendations">
              {report.recommendations.map((recommendation) => {
                const linkedGap = gapById.get(recommendation.gapId);
                const firstQuestionId = linkedGap?.affectedQuestionIds[0];
                return (
                  <li key={recommendation.id}>
                    <div className="report-action-heading">
                      <strong>{recommendation.change}</strong>
                      <Badge
                        label={recommendation.priority}
                        variant={recommendation.priority === 'High' ? 'red' : recommendation.priority === 'Medium' ? 'orange' : 'blue'}
                      />
                    </div>
                    <p>{recommendation.reason}</p>
                    {linkedGap && firstQuestionId ? (
                      <button
                        className="report-text-button"
                        type="button"
                        onClick={() => revealQuestion(firstQuestionId)}
                      >
                        Review linked questions for {linkedGap.title}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          ) : <p>No recommendations were generated for this report.</p>}
        </section>

        <section className="report-section" aria-labelledby="follow-up-heading">
          <h3 id="follow-up-heading">Follow-up</h3>
          {report.followUpQuestions.length > 0 ? (
            <ul>{report.followUpQuestions.map((question) => <li key={question}>{question}</li>)}</ul>
          ) : <p>No follow-up questions were suggested.</p>}
        </section>

        <Banner
          status="info"
          title="What this report means"
          description="UVTS checks whether information exists in this manual. It does not confirm that the information is correct, safe, clearly written, or complete for every possible user. Its suggestions do not replace legal, safety, or expert review."
        />
      </div>
    </StageSection>
  );
}

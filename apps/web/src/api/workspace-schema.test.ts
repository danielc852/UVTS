import { describe, expect, it } from 'vitest';

import { getWorkspaceFixture } from './fixtures/workspaces';
import { parseTestWorkspace } from './workspaces';

describe('workspace response contract', () => {
  it('derives the browser question list from the persisted question set', () => {
    const fixture = getWorkspaceFixture('upload-ready');
    expect(fixture).toBeDefined();
    if (!fixture) return;

    const parsed = parseTestWorkspace(JSON.parse(JSON.stringify(fixture)));

    expect(parsed.schemaVersion).toBe(2);
    expect(parsed.questionSet?.status).toBe('confirmed');
    expect(parsed.questions).toEqual(parsed.questionSet?.items);
  });

  it('normalizes nullable compatibility fields without inventing lineage', () => {
    const fixture = getWorkspaceFixture('report-ready');
    expect(fixture).toBeDefined();
    if (!fixture?.report) return;
    const response = JSON.parse(JSON.stringify(fixture)) as Record<string, unknown>;
    response.evaluationSource = null;
    response.report = { ...fixture.report, source: null };

    const parsed = parseTestWorkspace(response);

    expect(parsed.evaluationSource).toBeUndefined();
    expect(parsed.report?.source).toBeUndefined();
  });

  it('rejects a question set whose provenance is missing', () => {
    const fixture = getWorkspaceFixture('questions-ready');
    expect(fixture?.questionSet).toBeDefined();
    if (!fixture?.questionSet) return;
    const response = JSON.parse(JSON.stringify(fixture)) as Record<string, unknown>;
    response.questionSet = { ...fixture.questionSet, source: undefined };

    expect(() => parseTestWorkspace(response)).toThrow('INVALID_TEST_STATE');
  });
});

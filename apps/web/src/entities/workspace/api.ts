import type { TestWorkspace } from './model';
import { apiClient } from '../../shared/api/client';
import { workspaceStateSchema } from './schema';

let sessionBootstrap: Promise<void> | undefined;

export function bootstrapSession(): Promise<void> {
  sessionBootstrap ??= apiClient
    .POST('/api/v1/session')
    .then(({ error }) => {
      if (error) throw new Error('SESSION_BOOTSTRAP_FAILED');
    })
    .catch((error: unknown) => {
      sessionBootstrap = undefined;
      throw error;
    });
  return sessionBootstrap;
}

export async function getTestWorkspace(testId: string): Promise<TestWorkspace> {
  await bootstrapSession();
  const { data, error, response } = await apiClient.GET('/api/v1/tests/{test_id}', {
    params: { path: { test_id: testId } },
  });

  if (error || !data) {
    throw new Error(response.status === 404 ? 'TEST_NOT_FOUND' : 'TEST_LOAD_FAILED');
  }

  return parseTestWorkspace(data);
}

export function parseTestWorkspace(value: unknown): TestWorkspace {
  const parsed = workspaceStateSchema.safeParse(value);
  if (!parsed.success) throw new Error('INVALID_TEST_STATE');
  return parsed.data;
}

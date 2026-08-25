import type { QueryClient } from '@tanstack/react-query';

import type { TestWorkspace } from './model';

export const queryKeys = {
  test: (testId: string) => ['tests', testId] as const,
};

export function storeWorkspace(queryClient: QueryClient, workspace: TestWorkspace): void {
  queryClient.setQueryData(queryKeys.test(workspace.id), workspace);
}

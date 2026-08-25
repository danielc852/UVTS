import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { queryKeys } from '../../entities/workspace/query';
import { useTestEvents } from './useEvaluationEvents';

class TestEventSource extends EventTarget {
  static latest: TestEventSource | undefined;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(readonly url: string, readonly options?: EventSourceInit) {
    super();
    TestEventSource.latest = this;
  }

  close() {}
}

describe('useTestEvents', () => {
  it('invalidates the workspace query when upload processing publishes an update', () => {
    vi.stubGlobal('EventSource', TestEventSource);
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useTestEvents('uploading-test', true), { wrapper });
    act(() => {
      TestEventSource.latest?.dispatchEvent(new MessageEvent('test.updated'));
    });

    expect(TestEventSource.latest?.url).toMatch(/\/api\/v1\/tests\/uploading-test\/events$/);
    expect(TestEventSource.latest?.options).toEqual({ withCredentials: true });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.test('uploading-test') });
    vi.unstubAllGlobals();
  });
});

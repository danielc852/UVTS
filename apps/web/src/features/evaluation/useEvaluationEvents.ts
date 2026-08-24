import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { apiUrl } from '../../api/client';
import { queryKeys } from '../../api/query-keys';

export function useTestEvents(testId: string, enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || typeof EventSource === 'undefined') {
      return undefined;
    }

    const eventSource = new EventSource(apiUrl(`/api/v1/tests/${testId}/events`), { withCredentials: true });
    const refetch = () => void queryClient.invalidateQueries({ queryKey: queryKeys.test(testId) });

    eventSource.addEventListener('test.updated', refetch);
    eventSource.onmessage = refetch;

    return () => eventSource.close();
  }, [enabled, queryClient, testId]);
}

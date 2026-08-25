import { Theme } from '@astryxdesign/core/theme';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type ReactNode } from 'react';

import { bootstrapSession } from '../entities/workspace/api';
import { uvtsLightTheme } from './theme/generated/uvts-light';

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 15_000, refetchOnWindowFocus: false },
        },
      }),
  );

  useEffect(() => {
    void bootstrapSession().catch(() => undefined);
  }, []);

  return (
    <Theme theme={uvtsLightTheme} mode="light">
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </Theme>
  );
}

import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { App } from '../app/App';
import { AppProviders } from '../app/providers';

export function renderApp(route: string | { pathname: string; state?: unknown } = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppProviders>
        <App />
      </AppProviders>
    </MemoryRouter>,
  );
}

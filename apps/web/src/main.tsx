import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import './app/theme/generated/uvts-theme.css';
import './app/styles.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { App } from './app/App';
import { ErrorBoundary } from './app/ErrorBoundary';
import { AppProviders } from './app/providers';

const root = document.getElementById('root');

if (!root) throw new Error('Root element was not found.');

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AppProviders>
          <App />
        </AppProviders>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);

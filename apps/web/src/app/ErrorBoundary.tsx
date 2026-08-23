import { Banner } from '@astryxdesign/core/Banner';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryState { hasError: boolean }

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) console.error('Unhandled UI error', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="workspace">
          <h1>Check a manual</h1>
          <Banner
            status="error"
            title="UVTS could not show this workspace"
            description="Reload the page. Your saved test remains on the server."
          />
        </div>
      );
    }
    return this.props.children;
  }
}

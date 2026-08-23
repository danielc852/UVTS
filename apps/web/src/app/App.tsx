import { AppShell } from '@astryxdesign/core/AppShell';
import { TopNav } from '@astryxdesign/core/TopNav';
import { Link } from 'react-router-dom';

import { AppRouter } from './router';

export function App() {
  return (
    <AppShell
      height="auto"
      variant="section"
      contentPadding={0}
      topNav={
        <TopNav
          label="Product navigation"
          heading={<Link className="product-link" to="/">UVTS</Link>}
          endContent={<span className="privacy-note">Private workspace</span>}
        />
      }
    >
      <AppRouter />
    </AppShell>
  );
}

import { AppShell } from '@astryxdesign/core/AppShell';
import { TopNav } from '@astryxdesign/core/TopNav';
import { Link } from 'react-router-dom';

import { AppRouter } from './router';

export function App() {
  return (
    <AppShell
      height="auto"
      variant="surface"
      contentPadding={0}
      topNav={
        <TopNav
          label="Product navigation"
          heading={<Link className="product-link" to="/">UVTS</Link>}
        />
      }
    >
      <AppRouter />
    </AppShell>
  );
}

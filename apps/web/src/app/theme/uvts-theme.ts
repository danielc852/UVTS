import { defineTheme } from '@astryxdesign/core/theme';

/**
 * Source definition for the committed static production theme. Regenerate it
 * with `pnpm build:theme` whenever these tokens change.
 */
export const uvtsTheme = defineTheme({
  name: 'uvts-light',
  tokens: {
    '--color-background-body': '#ffffff',
    '--color-background-surface': '#ffffff',
    '--color-text-primary': '#111111',
    '--color-text-secondary': '#525252',
    '--color-accent': '#111111',
    '--radius-container': '8px',
  },
});

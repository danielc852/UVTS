import { describe, expect, it } from 'vitest';

import { releasePdfPageSurface } from './pdf-page-surface';

describe('PDF page rendering', () => {
  it('releases canvas and text-layer memory when a page leaves the render window', () => {
    const canvas = document.createElement('canvas');
    const textLayer = document.createElement('div');
    canvas.width = 1280;
    canvas.height = 1920;
    textLayer.append(document.createElement('span'));

    releasePdfPageSurface(canvas, textLayer);

    expect(canvas.width).toBe(0);
    expect(canvas.height).toBe(0);
    expect(textLayer).toBeEmptyDOMElement();
  });
});

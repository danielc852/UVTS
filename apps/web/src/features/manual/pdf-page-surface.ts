export function releasePdfPageSurface(
  canvas: HTMLCanvasElement,
  textContainer: HTMLDivElement,
): void {
  canvas.width = 0;
  canvas.height = 0;
  textContainer.replaceChildren();
}

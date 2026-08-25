import 'pdfjs-dist/web/pdf_viewer.css';

import {
  getDocument,
  GlobalWorkerOptions,
  TextLayer,
  type PDFDocumentProxy,
  type PDFPageProxy,
  type RenderTask,
} from 'pdfjs-dist';
import { useEffect, useRef, useState } from 'react';

import { releasePdfPageSurface } from './pdf-page-surface';

GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PdfViewerProps {
  filename: string;
  url: string;
}

interface PdfPageProps {
  document: PDFDocumentProxy;
  pageNumber: number;
  width: number;
}

function PdfPage({ document, pageNumber, width }: PdfPageProps) {
  const rootRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const [isNearViewport, setIsNearViewport] = useState(pageNumber === 1);
  const [page, setPage] = useState<PDFPageProxy>();
  const [pageError, setPageError] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || typeof IntersectionObserver === 'undefined') {
      setIsNearViewport(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsNearViewport(entry.isIntersecting);
      },
      { root: root.closest<HTMLElement>('.pdf-viewer'), rootMargin: '800px 0px' },
    );
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!isNearViewport || page) return undefined;
    let active = true;
    void document
      .getPage(pageNumber)
      .then((loadedPage) => {
        if (active) setPage(loadedPage);
      })
      .catch(() => {
        if (active) setPageError(true);
      });
    return () => {
      active = false;
    };
  }, [document, isNearViewport, page, pageNumber]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const textContainer = textRef.current;
    if (!isNearViewport || !page || !canvas || !textContainer || width <= 0) return undefined;

    const unscaled = page.getViewport({ scale: 1 });
    const viewport = page.getViewport({ scale: width / unscaled.width });
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(viewport.width * pixelRatio);
    canvas.height = Math.floor(viewport.height * pixelRatio);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;
    textContainer.replaceChildren();
    textContainer.style.width = `${Math.floor(viewport.width)}px`;
    textContainer.style.height = `${Math.floor(viewport.height)}px`;
    const pageSurface = canvas.parentElement;
    if (pageSurface) {
      pageSurface.style.width = `${Math.floor(viewport.width)}px`;
      pageSurface.style.height = `${Math.floor(viewport.height)}px`;
    }
    rootRef.current?.style.setProperty('--scale-factor', String(viewport.scale));
    setPageError(false);

    const renderTask: RenderTask = page.render({
      canvas,
      viewport,
      transform: pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0],
    });
    const textLayer = new TextLayer({
      textContentSource: page.streamTextContent(),
      container: textContainer,
      viewport,
    });
    let active = true;
    void Promise.all([renderTask.promise, textLayer.render()]).catch((error: unknown) => {
      if (
        active &&
        (!(error instanceof Error) || error.name !== 'RenderingCancelledException')
      ) {
        setPageError(true);
      }
    });

    return () => {
      active = false;
      renderTask.cancel();
      textLayer.cancel();
      releasePdfPageSurface(canvas, textContainer);
    };
  }, [isNearViewport, page, width]);

  return (
    <article
      ref={rootRef}
      className="pdf-page"
      aria-label={`Page ${pageNumber} of ${document.numPages}`}
    >
      <p className="pdf-page-label">Page {pageNumber} of {document.numPages}</p>
      <div className="pdf-page-surface">
        <canvas ref={canvasRef} aria-hidden="true" />
        <div ref={textRef} className="textLayer" />
        {pageError ? (
          <p className="pdf-page-loading" role="alert">Page {pageNumber} could not be rendered.</p>
        ) : !page ? (
          <p className="pdf-page-loading" role="status">Loading page {pageNumber}…</p>
        ) : null}
      </div>
    </article>
  );
}

export function PdfViewer({ filename, url }: PdfViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy>();
  const [width, setWidth] = useState(640);
  const [error, setError] = useState(false);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(240, Math.floor(entry.contentRect.width - 32)));
    });
    observer.observe(viewer);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setDocument(undefined);
    setError(false);
    let active = true;
    const loadingTask = getDocument({ url, withCredentials: true });
    void loadingTask.promise
      .then((loadedDocument) => {
        if (active) setDocument(loadedDocument);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
      void loadingTask.destroy();
    };
  }, [url]);

  if (error) {
    return (
      <div className="pdf-viewer-error" role="alert">
        The preview could not be loaded. Open the original PDF instead.
      </div>
    );
  }

  return (
    <div
      ref={viewerRef}
      className="pdf-viewer"
      role="region"
      aria-label={`${filename} document preview`}
      tabIndex={0}
    >
      {document ? (
        Array.from({ length: document.numPages }, (_, index) => (
          <PdfPage key={index + 1} document={document} pageNumber={index + 1} width={width} />
        ))
      ) : (
        <p className="pdf-viewer-loading" role="status">Loading document preview…</p>
      )}
    </div>
  );
}

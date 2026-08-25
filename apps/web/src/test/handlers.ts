import { http, HttpResponse } from 'msw';

import { getWorkspaceFixture } from '../mocks/workspaces';

export const handlers = [
  http.post('*/api/v1/session', () =>
    HttpResponse.json({ authenticated: true, expires_in_seconds: 86_400 }),
  ),
  http.get('*/api/v1/tests/:testId', ({ params }) => {
    const fixture = getWorkspaceFixture(String(params.testId));
    return fixture ? HttpResponse.json(fixture) : HttpResponse.json({ detail: 'Not found' }, { status: 404 });
  }),
];

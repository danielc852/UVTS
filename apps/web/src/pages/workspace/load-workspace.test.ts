import { describe, expect, it, vi } from 'vitest';

const getTestWorkspace = vi.hoisted(() => vi.fn());
const mockCatalogLoaded = vi.hoisted(() => vi.fn());

vi.mock('../../entities/workspace/api', () => ({ getTestWorkspace }));
vi.mock('../../mocks/workspaces', () => {
  mockCatalogLoaded();
  return { getWorkspaceFixture: () => undefined };
});

describe('workspace loading', () => {
  it('does not load the demo fixture catalog for a live API workspace', async () => {
    const workspace = { id: 'test-1' };
    getTestWorkspace.mockResolvedValue(workspace);
    const { loadWorkspace } = await import('./load-workspace');

    await expect(loadWorkspace('test-1')).resolves.toEqual(workspace);
    expect(mockCatalogLoaded).not.toHaveBeenCalled();
    expect(getTestWorkspace).toHaveBeenCalledWith('test-1');
  });
});

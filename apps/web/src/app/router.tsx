import { Navigate, Route, Routes } from 'react-router-dom';

import { WorkspacePage } from '../routes/workspace/WorkspacePage';

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<WorkspacePage />} />
      <Route path="/tests/:testId" element={<WorkspacePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

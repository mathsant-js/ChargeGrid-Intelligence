import { Navigate, Route, Routes } from 'react-router-dom'

import { FoundationPage } from './pages/FoundationPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<FoundationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

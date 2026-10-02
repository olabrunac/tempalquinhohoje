import { Navigate, Route, Routes } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import MainScreen from './MainScreen'
import AdminScreen from './AdminScreen'
import EventsScreen from './EventsScreen'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<MainScreen />} />
        <Route path="/admin" element={<AdminScreen />} />
        <Route path="/eventos" element={<EventsScreen />} />
        {/* URL errada/velha (ex: /docs, /openapi.json) volta pra tela principal
            em vez de ficar numa página em branco. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Analytics />
    </>
  )
}

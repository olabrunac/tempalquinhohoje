import { Route, Routes } from 'react-router-dom'
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
      </Routes>
      <Analytics />
    </>
  )
}

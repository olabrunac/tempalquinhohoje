import { Route, Routes } from 'react-router-dom'
import MainScreen from './MainScreen'
import AdminScreen from './AdminScreen'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainScreen />} />
      <Route path="/admin" element={<AdminScreen />} />
    </Routes>
  )
}
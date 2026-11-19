import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import ParticipantDashboard from './pages/Participant'
import AdminDashboard from './pages/Admin'
import {
  AdminLogin, ChangePassword, ParticipantLogin, Register, ResetPassword,
} from './pages/Auth'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<ParticipantLogin />} />
        <Route path="/organiser/login" element={<AdminLogin />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/change-password" element={<ChangePassword />} />
        <Route path="/dashboard" element={<ParticipantDashboard />} />
        <Route path="/organiser" element={<AdminDashboard />} />
        <Route path="/organiser/dashboard" element={<Navigate to="/organiser" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

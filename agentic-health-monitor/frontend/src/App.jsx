import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home.jsx'
import SymptomForm from './pages/SymptomForm.jsx'
import FollowUp from './pages/FollowUp.jsx'
import Report from './pages/Report.jsx'
import History from './pages/History.jsx'
import Signup from './pages/Signup.jsx'
import Login from './pages/Login.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Dashboard from './pages/Dashboard.jsx'
import SharedReport from './pages/SharedReport.jsx'
import AgentFlow from './pages/AgentFlow.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/shared/:token" element={<SharedReport />} />
      <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/symptom-form" element={<ProtectedRoute><SymptomForm /></ProtectedRoute>} />
      <Route path="/follow-up" element={<ProtectedRoute><FollowUp /></ProtectedRoute>} />
      <Route path="/report" element={<ProtectedRoute><Report /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="/agent-flow" element={<ProtectedRoute><AgentFlow /></ProtectedRoute>} />
    </Routes>
  )
}

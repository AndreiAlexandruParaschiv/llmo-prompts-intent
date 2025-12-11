import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Projects from '@/pages/Projects'
import ProjectDetail from '@/pages/ProjectDetail'
import Prompts from '@/pages/Prompts'
import PromptDetail from '@/pages/PromptDetail'
import Pages from '@/pages/Pages'
import Opportunities from '@/pages/Opportunities'
import OrphanPages from '@/pages/OrphanPages'
import Import from '@/pages/Import'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:projectId" element={<ProjectDetail />} />
          <Route path="projects/:projectId/import" element={<Import />} />
          <Route path="prompts" element={<Prompts />} />
          <Route path="prompts/:promptId" element={<PromptDetail />} />
          <Route path="pages" element={<Pages />} />
          <Route path="orphan-pages" element={<OrphanPages />} />
          <Route path="opportunities" element={<Opportunities />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  )
}

export default App


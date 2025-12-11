import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ProjectStore {
  selectedProjectId: string | null
  setSelectedProjectId: (id: string | null) => void
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      selectedProjectId: null,
      setSelectedProjectId: (id) => set({ selectedProjectId: id }),
    }),
    {
      name: 'project-store',
    }
  )
)


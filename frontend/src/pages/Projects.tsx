import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { 
  Plus, 
  FolderKanban, 
  MessageSquareText, 
  Globe, 
  Lightbulb,
  MoreHorizontal,
  Pencil,
  Trash2,
  ExternalLink,
  Calendar,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { projectsApi, Project } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

function CreateProjectDialog({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [domains, setDomains] = useState('')
  const { toast } = useToast()

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; target_domains?: string[] }) =>
      projectsApi.create(data),
    onSuccess: () => {
      toast({ title: 'Project created successfully' })
      setOpen(false)
      setName('')
      setDescription('')
      setDomains('')
      onSuccess()
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to create project', description: error.message, variant: 'destructive' })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name,
      description: description || undefined,
      target_domains: domains ? domains.split(',').map(d => d.trim()).filter(Boolean) : [],
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600">
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Set up a new content gap analysis project.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Project Name</label>
              <Input
                placeholder="My Content Analysis"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input
                placeholder="Analyzing blog content opportunities..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Target Domains</label>
              <Input
                placeholder="example.com, blog.example.com"
                value={domains}
                onChange={(e) => setDomains(e.target.value)}
              />
              <p className="text-xs text-slate-500">
                Comma-separated list of domains to analyze
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name || createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { selectedProjectId, setSelectedProjectId } = useProjectStore()
  const { toast } = useToast()
  const isSelected = selectedProjectId === project.id

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.delete(project.id),
    onSuccess: () => {
      toast({ title: 'Project deleted' })
      if (selectedProjectId === project.id) {
        setSelectedProjectId(null)
      }
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to delete', description: error.message, variant: 'destructive' })
    },
  })

  const handleSelect = () => {
    setSelectedProjectId(project.id)
    navigate(`/projects/${project.id}`)
  }

  return (
    <Card 
      className={cn(
        "group relative overflow-hidden border-slate-200 dark:border-slate-800 hover:shadow-lg transition-all duration-300 cursor-pointer",
        isSelected && "ring-2 ring-cyan-500 ring-offset-2"
      )}
      onClick={handleSelect}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800" />
      <CardHeader className="relative pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
              <FolderKanban className="w-5 h-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg">{project.name}</CardTitle>
              {project.description && (
                <CardDescription className="line-clamp-1">
                  {project.description}
                </CardDescription>
              )}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/projects/${project.id}`) }}>
                <ExternalLink className="w-4 h-4 mr-2" />
                Open
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { 
                e.stopPropagation()
                if (isSelected) {
                  setSelectedProjectId(null)
                  toast({ title: 'Project deactivated' })
                } else {
                  setSelectedProjectId(project.id)
                  toast({ title: 'Project set as active' })
                }
                queryClient.invalidateQueries({ queryKey: ['project-stats'] })
              }}>
                <Pencil className="w-4 h-4 mr-2" />
                {isSelected ? 'Deactivate' : 'Set as Active'}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-red-600"
                onClick={(e) => { e.stopPropagation(); deleteMutation.mutate() }}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="relative pt-4">
        {/* Target Domains */}
        {project.target_domains && project.target_domains.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {project.target_domains.slice(0, 3).map((domain, i) => (
              <Badge key={i} variant="secondary" className="text-xs">
                {domain}
              </Badge>
            ))}
            {project.target_domains.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{project.target_domains.length - 3} more
              </Badge>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
            <MessageSquareText className="w-4 h-4 mx-auto mb-1 text-cyan-500" />
            <p className="text-lg font-bold text-slate-900 dark:text-white">
              {project.prompt_count || 0}
            </p>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Prompts</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
            <Globe className="w-4 h-4 mx-auto mb-1 text-emerald-500" />
            <p className="text-lg font-bold text-slate-900 dark:text-white">
              {project.page_count || 0}
            </p>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Pages</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
            <Lightbulb className="w-4 h-4 mx-auto mb-1 text-amber-500" />
            <p className="text-lg font-bold text-slate-900 dark:text-white">
              {project.opportunity_count || 0}
            </p>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Opps</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Calendar className="w-3.5 h-3.5" />
            <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
          </div>
          {isSelected && (
            <Badge className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20">
              Active
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function Projects() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const projects = data?.data?.projects || []

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Projects</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Manage your content gap analysis projects
          </p>
        </div>
        <CreateProjectDialog onSuccess={() => queryClient.invalidateQueries({ queryKey: ['projects'] })} />
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-40 bg-slate-200 dark:bg-slate-800 rounded-lg" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 flex items-center justify-center mb-4">
              <FolderKanban className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              No projects yet
            </h3>
            <p className="text-slate-500 dark:text-slate-400 mb-4 text-center max-w-sm">
              Create your first project to start analyzing content gaps and opportunities.
            </p>
            <CreateProjectDialog onSuccess={() => queryClient.invalidateQueries({ queryKey: ['projects'] })} />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  )
}


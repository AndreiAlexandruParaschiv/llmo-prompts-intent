import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Lightbulb,
  Search,
  Download,
  Filter,
  ChevronRight,
  ExternalLink,
  FileText,
  Pencil,
  Target,
  TrendingUp,
  Check,
  X,
  Clock,
  ArrowUpRight,
  Star,
  Sparkles,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { opportunitiesApi, pagesApi, Opportunity } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

const statusConfig = {
  new: { 
    label: 'New', 
    color: 'bg-amber-500', 
    textColor: 'text-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    icon: Lightbulb
  },
  in_progress: { 
    label: 'In Progress', 
    color: 'bg-blue-500', 
    textColor: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    icon: Clock
  },
  resolved: { 
    label: 'Resolved', 
    color: 'bg-emerald-500', 
    textColor: 'text-emerald-500',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
    icon: Check
  },
  dismissed: { 
    label: 'Dismissed', 
    color: 'bg-slate-400', 
    textColor: 'text-slate-400',
    bgColor: 'bg-slate-50 dark:bg-slate-800',
    icon: X
  },
}

const actionConfig = {
  create_faq: { label: 'Create FAQ', icon: FileText, color: 'text-cyan-500' },
  create_article: { label: 'Create Article', icon: FileText, color: 'text-blue-500' },
  create_product_page: { label: 'Create Product Page', icon: FileText, color: 'text-indigo-500' },
  create_landing_page: { label: 'Create Landing Page', icon: FileText, color: 'text-purple-500' },
  expand_existing: { label: 'Expand Content', icon: Pencil, color: 'text-amber-500' },
  add_cta: { label: 'Add CTA', icon: Target, color: 'text-rose-500' },
  add_structured_data: { label: 'Add Schema', icon: Sparkles, color: 'text-emerald-500' },
  translate: { label: 'Translate', icon: FileText, color: 'text-teal-500' },
  canonicalize: { label: 'Canonicalize', icon: FileText, color: 'text-slate-500' },
}

function OpportunityCard({ 
  opportunity, 
  onStatusChange,
}: { 
  opportunity: Opportunity
  onStatusChange: (id: string, status: string) => void
}) {
  const [showRelatedPages, setShowRelatedPages] = useState(false)
  const [relatedPages, setRelatedPages] = useState<Array<{ id: string; url: string; title?: string }>>([])
  const [loadingPages, setLoadingPages] = useState(false)
  
  const handleToggleRelatedPages = async () => {
    if (!showRelatedPages && relatedPages.length === 0 && opportunity.related_page_ids?.length) {
      setLoadingPages(true)
      try {
        const pages = await Promise.all(
          opportunity.related_page_ids.slice(0, 5).map(async (pageId) => {
            try {
              const response = await pagesApi.get(pageId)
              return { id: pageId, url: response.data.url, title: response.data.title }
            } catch {
              return { id: pageId, url: `Page ${pageId.slice(0, 8)}...`, title: undefined }
            }
          })
        )
        setRelatedPages(pages)
      } finally {
        setLoadingPages(false)
      }
    }
    setShowRelatedPages(!showRelatedPages)
  }
  
  const status = statusConfig[opportunity.status as keyof typeof statusConfig] || statusConfig.new
  const action = actionConfig[opportunity.recommended_action as keyof typeof actionConfig] || actionConfig.create_article
  const StatusIcon = status.icon
  const ActionIcon = action.icon

  // priority_score is 0-1 from backend, convert to 0-100 for display
  const rawScore = opportunity.priority_score ?? 0
  const priorityPercent = Math.min(100, Math.round(rawScore <= 1 ? rawScore * 100 : rawScore))
  const priorityLevel = priorityPercent >= 70 ? 'High' : priorityPercent >= 40 ? 'Medium' : 'Low'
  const priorityColor = priorityPercent >= 70 ? 'text-red-500' : priorityPercent >= 40 ? 'text-amber-500' : 'text-emerald-500'

  return (
    <Card className={cn(
      "border-slate-200 dark:border-slate-800 transition-all duration-200 hover:shadow-md",
      status.bgColor
    )}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Priority indicator */}
          <div className="flex flex-col items-center gap-1">
            <div className={cn(
              "w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold",
              priorityPercent >= 70 ? "bg-red-100 dark:bg-red-900/30 text-red-500" :
              priorityPercent >= 40 ? "bg-amber-100 dark:bg-amber-900/30 text-amber-500" :
              "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500"
            )}>
              {priorityPercent}
            </div>
            <span className={cn("text-[10px] font-medium", priorityColor)}>
              {priorityLevel}
            </span>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Prompt text */}
            <p className="font-medium text-slate-900 dark:text-white line-clamp-2">
              {opportunity.prompt_text || 'Untitled Opportunity'}
            </p>

            {/* Action badge */}
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <Badge variant="outline" className="text-xs">
                <ActionIcon className={cn("w-3 h-3 mr-1", action.color)} />
                {action.label}
              </Badge>

              {opportunity.prompt_topic && (
                <Badge variant="secondary" className="text-xs">
                  {opportunity.prompt_topic}
                </Badge>
              )}

              {opportunity.prompt_intent && (
                <Badge variant="secondary" className="text-xs capitalize">
                  {opportunity.prompt_intent}
                </Badge>
              )}

              {opportunity.prompt_transaction_score > 0.6 && (
                <Badge className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  High Intent
                </Badge>
              )}
            </div>

            {/* Reason */}
            {opportunity.reason && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 line-clamp-2">
                {opportunity.reason}
              </p>
            )}

            {/* Related pages */}
            {opportunity.related_page_ids && opportunity.related_page_ids.length > 0 && (
              <div className="mt-2">
                <button
                  onClick={handleToggleRelatedPages}
                  className="flex items-center gap-2 text-xs text-cyan-600 hover:text-cyan-700 dark:text-cyan-400"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  {opportunity.related_page_ids.length} related page(s)
                  <span className="text-slate-400">{showRelatedPages ? '▼' : '▶'}</span>
                </button>
                
                {showRelatedPages && (
                  <div className="mt-2 space-y-1 pl-5 border-l-2 border-slate-200 dark:border-slate-700">
                    {loadingPages ? (
                      <p className="text-xs text-slate-400">Loading pages...</p>
                    ) : relatedPages.length > 0 ? (
                      relatedPages.map((page) => (
                        <a
                          key={page.id}
                          href={page.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-xs text-slate-600 hover:text-cyan-600 dark:text-slate-400 dark:hover:text-cyan-400"
                        >
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{page.title || page.url}</span>
                        </a>
                      ))
                    ) : (
                      <p className="text-xs text-slate-400">No pages found</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            {/* Status dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8">
                  <StatusIcon className={cn("w-3.5 h-3.5 mr-1.5", status.textColor)} />
                  {status.label}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {Object.entries(statusConfig).map(([key, config]) => (
                  <DropdownMenuItem 
                    key={key}
                    onClick={() => onStatusChange(opportunity.id, key)}
                  >
                    <config.icon className={cn("w-4 h-4 mr-2", config.textColor)} />
                    {config.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Opportunities() {
  const { selectedProjectId, setSelectedProjectId } = useProjectStore()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [searchParams] = useSearchParams()

  // Get project_id from URL or store
  const urlProjectId = searchParams.get('project_id')
  const projectId = urlProjectId || selectedProjectId
  
  // Set project if from URL - use useEffect to avoid state update during render
  useEffect(() => {
    if (urlProjectId && urlProjectId !== selectedProjectId) {
      setSelectedProjectId(urlProjectId)
    }
  }, [urlProjectId, selectedProjectId, setSelectedProjectId])

  const [status, setStatus] = useState(searchParams.get('status') || 'all')
  const [action, setAction] = useState('all')
  const [minPriority, setMinPriority] = useState<string>('')
  const [page, setPage] = useState(1)

  // Fetch opportunities
  const { data, isLoading, error } = useQuery({
    queryKey: ['opportunities', { 
      projectId, 
      status, 
      action, 
      minPriority, 
      page 
    }],
    queryFn: () => opportunitiesApi.list({
      project_id: projectId || undefined,
      status: status !== 'all' ? status : undefined,
      recommended_action: action !== 'all' ? action : undefined,
      min_priority: minPriority ? parseInt(minPriority) / 100 : undefined, // Convert to 0-1 scale
      page,
      page_size: 20,
    }),
    enabled: !!projectId, // Only fetch when project is selected
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Update status mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      opportunitiesApi.update(id, { status }),
    onSuccess: () => {
      toast({ title: 'Status updated' })
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to update', description: error.message, variant: 'destructive' })
    },
  })

  // Export handlers
  const handleExportCsv = async () => {
    if (!projectId) return
    try {
      const response = await opportunitiesApi.exportCsv(projectId)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `opportunities-${projectId}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      toast({ title: 'Export failed', variant: 'destructive' })
    }
  }

  const handleExportJson = async () => {
    if (!projectId) return
    try {
      const response = await opportunitiesApi.exportJson(projectId)
      const blob = new Blob([response.data], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `opportunities-${projectId}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      toast({ title: 'Export failed', variant: 'destructive' })
    }
  }

  const opportunities = data?.data?.opportunities || []
  const total = Object.values(data?.data?.by_status || {}).reduce((a, b) => a + b, 0) as number
  const byStatus = data?.data?.by_status || {}
  const byAction = data?.data?.by_action || {}
  
  // Handle no project selected
  if (!projectId) {
    return (
      <div className="space-y-6 animate-in">
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Lightbulb className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              Select a Project
            </h3>
            <p className="text-slate-500 text-center max-w-sm">
              Choose a project from the sidebar to view its opportunities.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  // Handle error state
  if (error) {
    return (
      <div className="space-y-6 animate-in">
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20">
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-300">Error loading opportunities</h3>
            <p className="text-red-600 dark:text-red-400 mt-2">{(error as Error).message}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Opportunities</h2>
          <p className="text-slate-500 dark:text-slate-400">
            {total} opportunities {projectId ? 'in this project' : 'across all projects'}
          </p>
        </div>
        {projectId && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleExportCsv}>
                Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleExportJson}>
                Export as JSON
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      {/* Status Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        {Object.entries(statusConfig).map(([key, config]) => {
          const count = (byStatus[key] || 0) as number
          return (
            <Card 
              key={key} 
              className={cn(
                "border-slate-200 dark:border-slate-800 cursor-pointer transition-all hover:shadow-md",
                status === key && "ring-2 ring-cyan-500"
              )}
              onClick={() => setStatus(status === key ? 'all' : key)}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center",
                    config.color,
                    "bg-opacity-20"
                  )}>
                    <config.icon className={cn("w-5 h-5", config.textColor)} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{count}</p>
                    <p className="text-xs text-slate-500">{config.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Filters */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            {/* Action filter */}
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Action Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                {Object.entries(actionConfig).map(([key, config]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <config.icon className={cn("w-4 h-4", config.color)} />
                      {config.label}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Priority filter */}
            <Select value={minPriority || 'any'} onValueChange={(v) => setMinPriority(v === 'any' ? '' : v)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Min Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any Priority</SelectItem>
                <SelectItem value="70">High (70+)</SelectItem>
                <SelectItem value="40">Medium+ (40+)</SelectItem>
              </SelectContent>
            </Select>

            {/* Clear filters */}
            {(status !== 'all' || action !== 'all' || minPriority) && (
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => {
                  setStatus('all')
                  setAction('all')
                  setMinPriority('')
                }}
              >
                Clear filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Opportunities List */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="h-24 bg-slate-200 dark:bg-slate-800 rounded-lg" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : opportunities.length === 0 ? (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Lightbulb className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              No opportunities found
            </h3>
            <p className="text-slate-500 text-center max-w-sm">
              {projectId 
                ? 'Run matching to identify content opportunities.'
                : 'Select a project to view opportunities.'}
            </p>
            {projectId && (
              <Button asChild className="mt-4">
                <Link to={`/projects/${projectId}`}>Go to Project</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {opportunities.map((opportunity) => (
            <OpportunityCard 
              key={opportunity.id} 
              opportunity={opportunity}
              onStatusChange={(id, status) => updateMutation.mutate({ id, status })}
            />
          ))}
        </div>
      )}
    </div>
  )
}


import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Sparkles,
  Download,
  RefreshCw,
  Search,
  Filter,
  ExternalLink,
  Target,
  Users,
  TrendingUp,
  Loader2,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  Zap,
  ChevronDown,
  ChevronUp,
  FileText,
  Globe,
  StopCircle,
  Upload,
} from 'lucide-react'
import { useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
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
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { pagesApi } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

const intentColors: Record<string, string> = {
  transactional: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  informational: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  commercial: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  navigational: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  comparison: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
}

const funnelColors: Record<string, string> = {
  awareness: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  consideration: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  decision: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
}

const categoryColors: Record<string, string> = {
  generic: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  comparison: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  branded_verify: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  branded_sentiment: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
}

const categoryLabels: Record<string, string> = {
  generic: 'Generic',
  comparison: 'Comparison',
  branded_verify: 'Branded (Verify)',
  branded_sentiment: 'Branded (Sentiment)',
}

interface CandidatePromptItem {
  page_id: string
  page_url: string
  page_title: string | null
  page_topic: string
  page_summary: string
  brand_name?: string
  product_category?: string
  text: string
  prompt_category: string
  intent: string
  funnel_stage: string
  topic: string
  sub_topic: string
  audience_persona: string
  transaction_score: number
  citation_trigger: string
  reasoning: string
  generated_at: string
}

function PromptCard({ prompt, expanded, onToggle }: { 
  prompt: CandidatePromptItem
  expanded: boolean
  onToggle: () => void 
}) {
  return (
    <Card className="border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-200">
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Prompt Text */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-violet-500/20">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-slate-900 dark:text-white font-medium">
                "{prompt.text}"
              </p>
              <div className="flex items-center gap-2 mt-1">
                <a
                  href={prompt.page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 truncate max-w-md"
                >
                  {prompt.page_title || prompt.page_url}
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
                </a>
              </div>
            </div>
          </div>

          {/* Badges Row */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Prompt Category - Most important for filtering */}
            {prompt.prompt_category && (
              <Badge className={cn("text-xs font-medium", categoryColors[prompt.prompt_category] || 'bg-slate-100')}>
                {categoryLabels[prompt.prompt_category] || prompt.prompt_category}
              </Badge>
            )}
            
            {/* Transaction Score */}
            <Badge variant="outline" className="gap-1">
              <TrendingUp className="w-3 h-3" />
              {Math.round(prompt.transaction_score * 100)}%
            </Badge>
            
            {/* Intent */}
            <Badge className={cn("capitalize text-xs", intentColors[prompt.intent] || 'bg-slate-100')}>
              {prompt.intent}
            </Badge>
            
            {/* Funnel Stage */}
            {prompt.funnel_stage && (
              <Badge className={cn("capitalize text-xs", funnelColors[prompt.funnel_stage] || 'bg-slate-100')}>
                {prompt.funnel_stage}
              </Badge>
            )}
            
            {/* Topic */}
            {prompt.topic && (
              <Badge variant="outline" className="text-xs">
                {prompt.topic}
              </Badge>
            )}
          </div>

          {/* Expandable Details */}
          <div>
            <button
              onClick={onToggle}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? 'Hide details' : 'Show details'}
            </button>
            
            {expanded && (
              <div className="mt-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 space-y-3 text-sm">
                {/* Audience */}
                {prompt.audience_persona && (
                  <div className="flex items-start gap-2">
                    <Users className="w-4 h-4 text-violet-500 mt-0.5" />
                    <div>
                      <span className="text-slate-500 text-xs">Audience: </span>
                      <span className="text-slate-700 dark:text-slate-300">{prompt.audience_persona}</span>
                    </div>
                  </div>
                )}
                
                {/* Citation Trigger */}
                {prompt.citation_trigger && (
                  <div className="flex items-start gap-2">
                    <Target className="w-4 h-4 text-emerald-500 mt-0.5" />
                    <div>
                      <span className="text-slate-500 text-xs">Would cite: </span>
                      <span className="text-slate-700 dark:text-slate-300">{prompt.citation_trigger}</span>
                    </div>
                  </div>
                )}
                
                {/* Reasoning */}
                {prompt.reasoning && (
                  <div className="flex items-start gap-2">
                    <Zap className="w-4 h-4 text-amber-500 mt-0.5" />
                    <div>
                      <span className="text-slate-500 text-xs">Why: </span>
                      <span className="text-slate-700 dark:text-slate-300">{prompt.reasoning}</span>
                    </div>
                  </div>
                )}

                {/* Page Summary */}
                {prompt.page_summary && (
                  <div className="flex items-start gap-2">
                    <FileText className="w-4 h-4 text-blue-500 mt-0.5" />
                    <div>
                      <span className="text-slate-500 text-xs">Page: </span>
                      <span className="text-slate-700 dark:text-slate-300">{prompt.page_summary}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function CandidatePrompts() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { selectedProjectId } = useProjectStore()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [intentFilter, setIntentFilter] = useState<string>('all')
  const [funnelFilter, setFunnelFilter] = useState<string>('all')
  const [expandedPrompts, setExpandedPrompts] = useState<Set<string>>(new Set())
  const pageSize = 20

  const projectId = searchParams.get('project_id') || selectedProjectId

  // Fetch stats
  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['candidate-prompts-stats', projectId],
    queryFn: () => pagesApi.getCandidatePromptsStats(projectId!),
    enabled: !!projectId,
    refetchInterval: 10000, // Poll every 10 seconds for progress updates
  })

  // Fetch prompts list
  const { data: promptsData, isLoading: promptsLoading, refetch: refetchPrompts } = useQuery({
    queryKey: ['candidate-prompts-list', projectId, categoryFilter, intentFilter, funnelFilter, search, page],
    queryFn: () => pagesApi.listCandidatePrompts({
      project_id: projectId!,
      prompt_category: categoryFilter === 'all' ? undefined : categoryFilter,
      intent: intentFilter === 'all' ? undefined : intentFilter,
      funnel_stage: funnelFilter === 'all' ? undefined : funnelFilter,
      search: search || undefined,
      page,
      page_size: pageSize,
    }),
    enabled: !!projectId,
  })

  const stats = statsData?.data
  const prompts = promptsData?.data?.prompts || []
  const total = promptsData?.data?.total || 0
  const totalPages = Math.ceil(total / pageSize)

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: (regenerate: boolean = false) =>
      pagesApi.generateCandidatePromptsBatch(projectId!, regenerate, 8),
    onSuccess: (response) => {
      const data = response.data
      if (data.status === 'processing') {
        toast({
          title: 'Generation Started',
          description: `Processing ${data.pages_queued} pages. Progress will update automatically.`,
        })
      } else if (data.status === 'no_pages') {
        toast({ title: 'No Pages to Process', description: data.message })
      }
      // Refetch stats to show progress
      setTimeout(() => refetchStats(), 2000)
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start generation', description: error.message, variant: 'destructive' })
    },
  })

  // Cancel generation mutation
  const cancelMutation = useMutation({
    mutationFn: () => pagesApi.cancelCandidatePromptsGeneration(projectId!),
    onSuccess: (response) => {
      const data = response.data
      if (data.status === 'cancelled') {
        toast({
          title: 'Generation Stopped',
          description: 'Prompt generation has been cancelled.',
        })
      } else {
        toast({ title: 'No Active Task', description: data.message })
      }
      refetchStats()
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to cancel', description: error.message, variant: 'destructive' })
    },
  })

  // Export handler
  const handleExport = async () => {
    if (!projectId) return
    try {
      const response = await pagesApi.exportCandidatePromptsCsv(projectId)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `candidate-prompts-${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
      toast({ title: 'Export Complete', description: 'CSV downloaded successfully.' })
    } catch {
      toast({ title: 'Export failed', description: 'No prompts to export. Generate prompts first.', variant: 'destructive' })
    }
  }

  const toggleExpand = (promptText: string) => {
    setExpandedPrompts(prev => {
      const next = new Set(prev)
      if (next.has(promptText)) {
        next.delete(promptText)
      } else {
        next.add(promptText)
      }
      return next
    })
  }

  const handleFilterChange = () => {
    setPage(1)
  }

  useEffect(() => {
    handleFilterChange()
  }, [categoryFilter, intentFilter, funnelFilter, search])

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <Sparkles className="w-16 h-16 text-slate-300 mb-4" />
        <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          No Project Selected
        </h2>
        <p className="text-slate-500 dark:text-slate-400">
          Choose a project from the sidebar to manage candidate prompts.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-7 h-7 text-violet-500" />
            Candidate Prompts
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            AI-generated prompts that would make LLMs cite your pages
          </p>
        </div>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                className="bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600"
                disabled={generateMutation.isPending}
              >
                {generateMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                Generate
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => generateMutation.mutate(false)}>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate Missing
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => generateMutation.mutate(true)}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Regenerate All
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="outline" onClick={handleExport} disabled={!stats?.total_prompts}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>

          <Button variant="outline" size="icon" onClick={() => { refetchStats(); refetchPrompts(); }}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {statsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : stats && (
        <>
          {/* Progress Bar (if generation in progress) */}
          {stats.pages_without_prompts > 0 && stats.generation_progress > 0 && stats.generation_progress < 100 && (
            <Card className="border-violet-200 dark:border-violet-800 bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                    <span className="text-sm font-medium text-violet-700 dark:text-violet-300">
                      Generation in Progress
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-violet-600 dark:text-violet-400">
                      {stats.pages_with_prompts} / {stats.total_pages} pages
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => cancelMutation.mutate()}
                      disabled={cancelMutation.isPending}
                      className="text-red-600 border-red-300 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-900/20"
                    >
                      {cancelMutation.isPending ? (
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      ) : (
                        <StopCircle className="w-3 h-3 mr-1" />
                      )}
                      Stop
                    </Button>
                  </div>
                </div>
                <Progress value={stats.generation_progress} className="h-2" />
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Total Pages */}
            <Card className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
                  <Globe className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total_pages}</p>
                  <p className="text-xs text-slate-500">Total Pages</p>
                </div>
              </CardContent>
            </Card>

            {/* Pages with Prompts */}
            <Card className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                  <CheckCircle2 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.pages_with_prompts}</p>
                  <p className="text-xs text-slate-500">Pages with Prompts</p>
                </div>
              </CardContent>
            </Card>

            {/* Pages without Prompts */}
            <Card className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center shadow-lg",
                  stats.pages_without_prompts > 0 
                    ? "bg-gradient-to-br from-amber-500 to-orange-500 shadow-amber-500/30"
                    : "bg-gradient-to-br from-slate-400 to-slate-500 shadow-slate-500/30"
                )}>
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.pages_without_prompts}</p>
                  <p className="text-xs text-slate-500">Need Generation</p>
                </div>
              </CardContent>
            </Card>

            {/* Total Prompts */}
            <Card className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total_prompts}</p>
                  <p className="text-xs text-slate-500">Total Prompts</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Distribution Charts */}
          {stats.total_prompts > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* By Prompt Category - Most Important */}
              <Card className="border-slate-200 dark:border-slate-800 md:col-span-1">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Filter className="w-4 h-4 text-cyan-500" />
                    By Category
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {stats.by_prompt_category && Object.entries(stats.by_prompt_category).sort((a, b) => b[1] - a[1]).map(([category, count]) => (
                      <div key={category} className="flex items-center justify-between">
                        <Badge className={cn("text-xs", categoryColors[category] || 'bg-slate-100')}>
                          {categoryLabels[category] || category}
                        </Badge>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          {count} ({Math.round((count / stats.total_prompts) * 100)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* By Intent */}
              <Card className="border-slate-200 dark:border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-violet-500" />
                    By Intent
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(stats.by_intent).sort((a, b) => b[1] - a[1]).map(([intent, count]) => (
                      <div key={intent} className="flex items-center justify-between">
                        <Badge className={cn("capitalize text-xs", intentColors[intent] || 'bg-slate-100')}>
                          {intent}
                        </Badge>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          {count} ({Math.round((count / stats.total_prompts) * 100)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* By Funnel Stage */}
              <Card className="border-slate-200 dark:border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                    By Funnel Stage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(stats.by_funnel_stage).sort((a, b) => b[1] - a[1]).map(([stage, count]) => (
                      <div key={stage} className="flex items-center justify-between">
                        <Badge className={cn("capitalize text-xs", funnelColors[stage] || 'bg-slate-100')}>
                          {stage}
                        </Badge>
                        <span className="text-sm text-slate-600 dark:text-slate-400">
                          {count} ({Math.round((count / stats.total_prompts) * 100)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}

      {/* Filters */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Search prompts..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Category Filter - Most Important */}
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="generic">Generic (Citation)</SelectItem>
                <SelectItem value="comparison">Comparison</SelectItem>
                <SelectItem value="branded_verify">Branded (Verify)</SelectItem>
                <SelectItem value="branded_sentiment">Branded (Sentiment)</SelectItem>
              </SelectContent>
            </Select>

            {/* Intent Filter */}
            <Select value={intentFilter} onValueChange={setIntentFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Intents" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Intents</SelectItem>
                <SelectItem value="transactional">Transactional</SelectItem>
                <SelectItem value="commercial">Commercial</SelectItem>
                <SelectItem value="comparison">Comparison</SelectItem>
                <SelectItem value="informational">Informational</SelectItem>
              </SelectContent>
            </Select>

            {/* Funnel Filter */}
            <Select value={funnelFilter} onValueChange={setFunnelFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All Stages" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                <SelectItem value="awareness">Awareness</SelectItem>
                <SelectItem value="consideration">Consideration</SelectItem>
                <SelectItem value="decision">Decision</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Prompts List */}
      {promptsLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : prompts.length === 0 ? (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Sparkles className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              {stats?.total_prompts === 0 ? 'No Prompts Generated Yet' : 'No Matching Prompts'}
            </h3>
            <p className="text-slate-500 text-center max-w-sm">
              {stats?.total_prompts === 0
                ? 'Click "Generate" above to create candidate prompts for your pages.'
                : 'Try adjusting your filters to see more prompts.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} prompts
            </p>
          </div>

          <div className="space-y-3">
            {prompts.map((prompt, idx) => (
              <PromptCard
                key={`${prompt.page_id}-${idx}`}
                prompt={prompt}
                expanded={expandedPrompts.has(prompt.text)}
                onToggle={() => toggleExpand(prompt.text)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-800">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-500">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

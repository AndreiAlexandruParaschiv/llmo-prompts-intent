import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  MessageSquareText,
  Search,
  Filter,
  ChevronRight,
  Globe,
  Target,
  AlertCircle,
  CheckCircle2,
  Clock,
  TrendingUp,
  Sparkles,
  Zap,
  Tag,
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
import { promptsApi, projectsApi, Prompt } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

const intentColors: Record<string, string> = {
  transactional: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  commercial: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  comparison: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  informational: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  navigational: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  exploratory: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  procedural: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  troubleshooting: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  opinion_seeking: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  emotional: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
  regulatory: 'bg-slate-100 text-slate-700 dark:bg-slate-700/30 dark:text-slate-300',
  brand_monitoring: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  meta: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
}

const matchStatusColors = {
  answered: 'bg-emerald-500',
  partial: 'bg-amber-500',
  gap: 'bg-red-500',
  pending: 'bg-slate-400',
}

const matchStatusIcons = {
  answered: CheckCircle2,
  partial: AlertCircle,
  gap: Target,
  pending: Clock,
}

function PromptCard({ prompt }: { prompt: Prompt }) {
  const StatusIcon = matchStatusIcons[prompt.match_status as keyof typeof matchStatusIcons] || Clock

  return (
    <Link to={`/prompts/${prompt.id}`}>
      <Card className="group border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start gap-4">
            {/* Status indicator */}
            <div className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
              matchStatusColors[prompt.match_status as keyof typeof matchStatusColors] || matchStatusColors.pending,
              "bg-opacity-20"
            )}>
              <StatusIcon className={cn(
                "w-5 h-5",
                prompt.match_status === 'answered' && "text-emerald-500",
                prompt.match_status === 'partial' && "text-amber-500",
                prompt.match_status === 'gap' && "text-red-500",
                prompt.match_status === 'pending' && "text-slate-500",
              )} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-900 dark:text-white line-clamp-2 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors">
                {prompt.raw_text}
              </p>
              
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {/* Intent badge */}
                <Badge className={cn(
                  "text-xs capitalize",
                  intentColors[prompt.intent_label as keyof typeof intentColors] || intentColors.unknown
                )}>
                  {prompt.intent_label}
                </Badge>

                {/* Transaction score - buying intent indicator */}
                {prompt.transaction_score > 0 && (
                  <Badge 
                    variant="outline" 
                    className={cn(
                      "text-xs",
                      prompt.transaction_score >= 0.6 
                        ? "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-700" 
                        : ""
                    )}
                  >
                    <TrendingUp className="w-3 h-3 mr-1" />
                    {prompt.transaction_score >= 0.6 ? '🛒 ' : ''}
                    {Math.round(prompt.transaction_score * 100)}% buying intent
                  </Badge>
                )}

                {/* Language */}
                {prompt.language && (
                  <Badge variant="secondary" className="text-xs">
                    <Globe className="w-3 h-3 mr-1" />
                    {prompt.language.toUpperCase()}
                  </Badge>
                )}

                {/* Category */}
                {prompt.category && (
                  <Badge variant="outline" className="text-xs bg-slate-100 dark:bg-slate-800">
                    {prompt.category}
                  </Badge>
                )}

                {/* Topic */}
                {prompt.topic && (
                  <Badge variant="outline" className="text-xs bg-violet-100 text-violet-700 border-violet-300 dark:bg-violet-900/30 dark:text-violet-400 dark:border-violet-700">
                    <Tag className="w-3 h-3 mr-1" />
                    {prompt.topic}
                  </Badge>
                )}
              </div>

              {/* Match info */}
              {prompt.best_match_score && (
                <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                  <Sparkles className="w-3.5 h-3.5" />
                  Best match: {Math.round(prompt.best_match_score * 100)}% similarity
                </div>
              )}
            </div>

            {/* Arrow */}
            <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-cyan-500 transition-colors flex-shrink-0" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

export default function Prompts() {
  const { selectedProjectId } = useProjectStore()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [intent, setIntent] = useState(searchParams.get('intent_label') || 'all')
  const [matchStatus, setMatchStatus] = useState(searchParams.get('match_status') || 'all')
  const [language, setLanguage] = useState(searchParams.get('language') || 'all')
  const [topic, setTopic] = useState(searchParams.get('topic') || 'all')
  const [page, setPage] = useState(1)

  // AI Reclassification state
  const [reclassifyTaskId, setReclassifyTaskId] = useState<string | null>(null)
  const [reclassifyProgress, setReclassifyProgress] = useState<{
    processed: number
    total: number
    changed: number
    current_item?: string
  } | null>(null)

  // Poll for task progress
  const { data: taskStatus } = useQuery({
    queryKey: ['task-status', reclassifyTaskId],
    queryFn: async () => {
      const response = await fetch(`/api/jobs/${reclassifyTaskId}`)
      return response.json()
    },
    enabled: !!reclassifyTaskId,
    refetchInterval: 1000,
  })

  // Update progress when task status changes - use useEffect to avoid state updates during render
  useEffect(() => {
    if (!taskStatus || !reclassifyTaskId) return

    if (taskStatus.state === 'PROGRESS' && taskStatus.meta) {
      setReclassifyProgress(taskStatus.meta)
    } else if (taskStatus.state === 'SUCCESS' || taskStatus.ready) {
      setReclassifyTaskId(null)
      setReclassifyProgress(null)
      queryClient.invalidateQueries({ queryKey: ['prompts'] })
      queryClient.invalidateQueries({ queryKey: ['project-stats'] })
      toast({
        title: 'AI Reclassification Complete',
        description: `${taskStatus.result?.processed || 0} prompts processed, ${taskStatus.result?.changed || 0} updated.`,
      })
    } else if (taskStatus.state === 'FAILURE') {
      setReclassifyTaskId(null)
      setReclassifyProgress(null)
      toast({
        title: 'AI Reclassification Failed',
        description: 'An error occurred while reclassifying prompts.',
        variant: 'destructive',
      })
    }
  }, [taskStatus, reclassifyTaskId, queryClient, toast])

  // AI Reclassification mutation
  const reclassifyMutation = useMutation({
    mutationFn: () => promptsApi.reclassifyWithAI(selectedProjectId!),
    onSuccess: (response) => {
      setReclassifyTaskId(response.data.task_id)
      setReclassifyProgress({ processed: 0, total: response.data.prompt_count, changed: 0 })
      toast({
        title: 'AI Reclassification Started',
        description: `Analyzing ${response.data.prompt_count} prompts with AI...`,
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Reclassification failed',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  // Fetch prompts
  const { data, isLoading } = useQuery({
    queryKey: ['prompts', { 
      projectId: selectedProjectId, 
      search, 
      intent, 
      matchStatus, 
      language,
      topic,
      page 
    }],
    queryFn: () => promptsApi.list({
      project_id: selectedProjectId || undefined,
      search: search || undefined,
      intent_label: intent !== 'all' ? intent : undefined,
      match_status: matchStatus !== 'all' && matchStatus !== 'buying_intent' ? matchStatus : undefined,
      min_transaction_score: matchStatus === 'buying_intent' ? 0.6 : undefined,
      language: language !== 'all' ? language : undefined,
      topic: topic !== 'all' ? topic : undefined,
      page,
      page_size: 20,
    }),
    refetchOnMount: true,
    staleTime: 10000, // Consider stale after 10 seconds
  })

  // Fetch filters
  const { data: topicsData } = useQuery({
    queryKey: ['prompt-topics', selectedProjectId],
    queryFn: () => promptsApi.getTopics(selectedProjectId || undefined),
  })

  const { data: languagesData } = useQuery({
    queryKey: ['prompt-languages', selectedProjectId],
    queryFn: () => promptsApi.getLanguages(selectedProjectId || undefined),
  })

  // Fetch project stats for accurate counts
  const { data: statsData } = useQuery({
    queryKey: ['project-stats', selectedProjectId],
    queryFn: () => projectsApi.getStats(selectedProjectId!),
    enabled: !!selectedProjectId,
    refetchOnMount: true,
    staleTime: 0, // Always refetch fresh data when navigating
  })

  const prompts = data?.data?.prompts || []
  const total = data?.data?.total || 0
  const totalPages = data?.data?.pages || 1
  const languages = languagesData?.data?.languages || {}
  const topics = topicsData?.data?.topics || {}
  const stats = statsData?.data

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Prompts</h2>
          <p className="text-slate-500 dark:text-slate-400">
            {total} prompts {selectedProjectId ? 'in this project' : 'across all projects'}
          </p>
        </div>
        {selectedProjectId && (
          <Button
            variant="outline"
            onClick={() => reclassifyMutation.mutate()}
            disabled={reclassifyMutation.isPending || !!reclassifyTaskId}
            className="bg-gradient-to-r from-violet-50 to-purple-50 hover:from-violet-100 hover:to-purple-100 border-violet-200 dark:from-violet-900/20 dark:to-purple-900/20 dark:border-violet-800"
          >
            <Zap className="w-4 h-4 mr-2 text-violet-500" />
            {reclassifyTaskId ? 'Reclassifying...' : 'Reclassify with AI'}
          </Button>
        )}
      </div>

      {/* AI Reclassification Progress */}
      {(reclassifyProgress || reclassifyTaskId) && (
        <Card className="border-violet-200 dark:border-violet-800 bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/50 flex items-center justify-center">
                <Zap className="w-5 h-5 text-violet-500 animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-violet-700 dark:text-violet-300">
                    AI Reclassification in Progress
                  </span>
                </div>
                {/* Animated indeterminate progress bar */}
                <div className="w-full bg-violet-200 dark:bg-violet-800 rounded-full h-2 mb-2 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-violet-400 via-violet-500 to-violet-400 rounded-full"
                    style={{ 
                      width: '40%',
                      animation: 'shimmer 1.5s ease-in-out infinite',
                    }}
                  />
                </div>
                <p className="text-xs text-violet-600 dark:text-violet-400">
                  Analyzing prompts with AI...
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search prompts..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Intent filter */}
            <Select value={intent} onValueChange={(v) => { setIntent(v); setPage(1); }}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Intent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Intents</SelectItem>
                <SelectItem value="transactional">Transactional</SelectItem>
                <SelectItem value="commercial">Commercial</SelectItem>
                <SelectItem value="comparison">Comparison</SelectItem>
                <SelectItem value="informational">Informational</SelectItem>
                <SelectItem value="navigational">Navigational</SelectItem>
                <SelectItem value="exploratory">Exploratory</SelectItem>
                <SelectItem value="procedural">Procedural</SelectItem>
                <SelectItem value="troubleshooting">Troubleshooting</SelectItem>
                <SelectItem value="opinion_seeking">Opinion Seeking</SelectItem>
                <SelectItem value="emotional">Emotional</SelectItem>
                <SelectItem value="regulatory">Regulatory</SelectItem>
                <SelectItem value="brand_monitoring">Brand Monitoring</SelectItem>
                <SelectItem value="meta">Meta</SelectItem>
              </SelectContent>
            </Select>

            {/* Match status filter */}
            <Select value={matchStatus} onValueChange={(v) => { setMatchStatus(v); setPage(1); }}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Match Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="answered">Answered</SelectItem>
                <SelectItem value="partial">Partial Match</SelectItem>
                <SelectItem value="gap">Content Gap</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>

            {/* Language filter */}
            <Select value={language} onValueChange={(v) => { setLanguage(v); setPage(1); }}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Languages</SelectItem>
                {Object.entries(languages).map(([lang, count]) => (
                  <SelectItem key={lang} value={lang}>
                    {lang.toUpperCase()} ({count as number})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Topic filter */}
            {Object.keys(topics).length > 0 && (
              <Select value={topic} onValueChange={(v) => { setTopic(v); setPage(1); }}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Topic" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Topics</SelectItem>
                  {Object.entries(topics)
                    .sort((a, b) => (b[1] as number) - (a[1] as number))
                    .map(([topicName, count]) => (
                      <SelectItem key={topicName} value={topicName}>
                        {topicName} ({count as number})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid gap-4 md:grid-cols-5">
        {[
          { label: 'Total', count: total, color: 'bg-slate-500', filter: 'all' },
          { label: 'Answered', count: stats?.by_match_status?.answered || 0, color: 'bg-emerald-500', filter: 'answered' },
          { label: 'Partial', count: stats?.by_match_status?.partial || 0, color: 'bg-amber-500', filter: 'partial' },
          { label: 'Gaps', count: stats?.by_match_status?.gap || 0, color: 'bg-red-500', filter: 'gap' },
          { label: 'Buying Intent', count: stats?.high_transaction_count || 0, color: 'bg-emerald-600', filter: 'buying_intent', icon: TrendingUp },
        ].map(stat => (
          <Card 
            key={stat.label} 
            className={cn(
              "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
              matchStatus === stat.filter && "ring-2 ring-cyan-500"
            )}
            onClick={() => { setMatchStatus(stat.filter); setPage(1); }}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                {stat.icon ? (
                  <stat.icon className={cn("w-5 h-5", stat.color.replace('bg-', 'text-'))} />
                ) : (
                  <div className={cn("w-3 h-3 rounded-full", stat.color)} />
                )}
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{stat.count}</p>
                  <p className="text-xs text-slate-500">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Prompts List */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="h-16 bg-slate-200 dark:bg-slate-800 rounded-lg" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : prompts.length === 0 ? (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <MessageSquareText className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              No prompts found
            </h3>
            <p className="text-slate-500 text-center max-w-sm">
              {selectedProjectId 
                ? 'Import a CSV file to add prompts to this project.'
                : 'Select a project and import CSV data to get started.'}
            </p>
            {selectedProjectId && (
              <Button asChild className="mt-4">
                <Link to={`/projects/${selectedProjectId}/import`}>Import CSV</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {prompts.map((prompt) => (
              <PromptCard key={prompt.id} prompt={prompt} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
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
                onClick={() => setPage(page + 1)}
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


import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  MessageSquareText,
  Globe,
  Target,
  AlertCircle,
  CheckCircle2,
  Clock,
  TrendingUp,
  Sparkles,
  ExternalLink,
  Link2,
  Languages,
  MapPin,
  BarChart3,
  Lightbulb,
  Zap,
  Info,
  Hash,
  Gauge,
  RefreshCw,
  Loader2,
  Activity,
  Wand2,
  DollarSign,
  Users,
  Quote,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { promptsApi, cwvApi, pagesApi, Prompt, PromptMatch, IntentExplanation, CWVPageResult, CWVMetrics, CandidatePrompt, CandidatePromptsResponse } from '@/services/api'
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

const matchStatusConfig = {
  answered: { 
    label: 'Answered', 
    color: 'bg-emerald-500', 
    textColor: 'text-emerald-500',
    icon: CheckCircle2,
    description: 'This prompt is well covered by existing content.'
  },
  partial: { 
    label: 'Partial Match', 
    color: 'bg-amber-500', 
    textColor: 'text-amber-500',
    icon: AlertCircle,
    description: 'Existing content partially addresses this prompt.'
  },
  gap: { 
    label: 'Content Gap', 
    color: 'bg-red-500', 
    textColor: 'text-red-500',
    icon: Target,
    description: 'No existing content matches this prompt.'
  },
  pending: { 
    label: 'Pending', 
    color: 'bg-slate-400', 
    textColor: 'text-slate-400',
    icon: Clock,
    description: 'Matching has not been run yet.'
  },
}

function MatchCard({ match }: { match: PromptMatch }) {
  const similarityPercent = Math.round(match.similarity_score * 100)

  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Link2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <a 
                href={match.page_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sm font-medium text-cyan-600 dark:text-cyan-400 hover:underline truncate"
              >
                {match.page_url}
              </a>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            </div>
            {match.page_title && (
              <p className="text-sm text-slate-700 dark:text-slate-300 mt-1">
                {match.page_title}
              </p>
            )}
            {match.matched_snippet && (
              <p className="text-xs text-slate-500 mt-2 line-clamp-2">
                "{match.matched_snippet}"
              </p>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <div className="flex items-center gap-2">
              <Progress value={similarityPercent} className="w-20 h-2" />
              <span className={cn(
                "text-sm font-bold",
                similarityPercent >= 75 ? "text-emerald-500" :
                similarityPercent >= 50 ? "text-amber-500" : "text-red-500"
              )}>
                {similarityPercent}%
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {match.match_type}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// CWV Score Badge Component
function CWVScoreBadge({ score, label }: { score: string | null; label: string }) {
  if (!score) return <span className="text-xs text-slate-400">N/A</span>
  
  const colorClass = 
    score === 'good' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' :
    score === 'needs-improvement' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  
  return (
    <Badge className={cn("text-[10px] capitalize", colorClass)}>
      {label}: {score.replace('-', ' ')}
    </Badge>
  )
}

// CWV Metric Row Component
function CWVMetricRow({ 
  name, 
  value, 
  score, 
  unit = 'ms',
  description 
}: { 
  name: string
  value: number | null
  score: string | null
  unit?: string
  description: string
}) {
  const scoreColor = 
    score === 'good' ? 'text-emerald-500' :
    score === 'needs-improvement' ? 'text-amber-500' :
    score === 'poor' ? 'text-red-500' : 'text-slate-400'

  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <div className="flex-1">
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{name}</p>
        <p className="text-[10px] text-slate-400">{description}</p>
      </div>
      <div className="text-right">
        {value !== null ? (
          <span className={cn("text-sm font-bold", scoreColor)}>
            {unit === 'ms' ? `${Math.round(value)}ms` : value.toFixed(3)}
          </span>
        ) : (
          <span className="text-xs text-slate-400">N/A</span>
        )}
      </div>
    </div>
  )
}

// CWV Card Component
function CWVCard({ cwvData, url, title, isLoading }: { 
  cwvData: CWVMetrics | null
  url: string
  title: string | null
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-violet-500" />
            <div>
              <p className="text-sm text-slate-700 dark:text-slate-300">Fetching Core Web Vitals...</p>
              <p className="text-xs text-slate-400 truncate max-w-md">{url}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!cwvData) return null

  if (cwvData.error) {
    return (
      <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-red-400">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {title || url}
              </p>
              <p className="text-xs text-red-500 mt-1">{cwvData.error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardContent className="p-4">
        {/* Header with URL and Performance Score */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1 min-w-0">
            <a 
              href={url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-sm font-medium text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1"
            >
              {title || url}
              <ExternalLink className="w-3 h-3" />
            </a>
            <div className="flex flex-wrap gap-1 mt-2">
              <CWVScoreBadge score={cwvData.lcp_score} label="LCP" />
              <CWVScoreBadge score={cwvData.cls_score} label="CLS" />
              <CWVScoreBadge score={cwvData.inp_score || cwvData.fid_score} label="INP" />
            </div>
          </div>
          {cwvData.performance_score !== null && (
            <div className="text-center flex-shrink-0">
              <div className={cn(
                "w-14 h-14 rounded-full flex items-center justify-center font-bold text-lg",
                cwvData.performance_score >= 90 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
                cwvData.performance_score >= 50 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              )}>
                {cwvData.performance_score}
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Score</p>
            </div>
          )}
        </div>

        {/* Metrics */}
        <div className="space-y-0">
          <CWVMetricRow 
            name="LCP" 
            value={cwvData.lcp} 
            score={cwvData.lcp_score}
            description="Largest Contentful Paint"
          />
          <CWVMetricRow 
            name="CLS" 
            value={cwvData.cls} 
            score={cwvData.cls_score}
            unit=""
            description="Cumulative Layout Shift"
          />
          <CWVMetricRow 
            name="INP" 
            value={cwvData.inp || cwvData.fid} 
            score={cwvData.inp_score || cwvData.fid_score}
            description="Interaction to Next Paint"
          />
          <CWVMetricRow 
            name="FCP" 
            value={cwvData.fcp} 
            score={cwvData.fcp_score}
            description="First Contentful Paint"
          />
          <CWVMetricRow 
            name="TTFB" 
            value={cwvData.ttfb} 
            score={cwvData.ttfb_score}
            description="Time to First Byte"
          />
        </div>

        {/* Data source indicator */}
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <span className="text-[10px] text-slate-400">
            {cwvData.has_field_data ? '📊 Real user data (CrUX)' : '🧪 Lab data (Lighthouse)'}
          </span>
          {cwvData.fetched_at && (
            <span className="text-[10px] text-slate-400">
              {new Date(cwvData.fetched_at).toLocaleString()}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// Candidate Prompt Card Component
function CandidatePromptCard({ prompt, index }: { prompt: CandidatePrompt; index: number }) {
  const intentColor = intentColors[prompt.intent] || intentColors.unknown
  
  return (
    <Card className="border-slate-200 dark:border-slate-800 hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 font-bold text-sm">
            {index + 1}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 dark:text-white mb-2">
              "{prompt.text}"
            </p>
            
            <div className="flex flex-wrap gap-2 mb-3">
              <Badge className={cn("text-xs capitalize", intentColor)}>
                {prompt.intent}
              </Badge>
              <Badge 
                variant="outline" 
                className={cn(
                  "text-xs",
                  prompt.transaction_score >= 0.7 ? "border-emerald-300 text-emerald-600 dark:text-emerald-400" :
                  prompt.transaction_score >= 0.4 ? "border-amber-300 text-amber-600 dark:text-amber-400" : 
                  "border-slate-300 text-slate-500"
                )}
              >
                <DollarSign className="w-3 h-3 mr-1" />
                {Math.round(prompt.transaction_score * 100)}% transaction
              </Badge>
            </div>
            
            <div className="space-y-2 text-xs text-slate-500">
              <div className="flex items-start gap-2">
                <Lightbulb className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                <span>{prompt.reasoning}</span>
              </div>
              <div className="flex items-start gap-2">
                <Users className="w-3.5 h-3.5 text-violet-500 flex-shrink-0 mt-0.5" />
                <span>{prompt.target_audience}</span>
              </div>
              {prompt.citation_trigger && (
                <div className="flex items-start gap-2">
                  <Quote className="w-3.5 h-3.5 text-cyan-500 flex-shrink-0 mt-0.5" />
                  <span className="italic">{prompt.citation_trigger}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function PromptDetail() {
  const { promptId } = useParams<{ promptId: string }>()
  const [showCWV, setShowCWV] = useState(false)
  const [showCandidatePrompts, setShowCandidatePrompts] = useState(false)
  const [forceRegenerate, setForceRegenerate] = useState(false)
  const [forceRefreshCWV, setForceRefreshCWV] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['prompt', promptId],
    queryFn: () => promptsApi.get(promptId!),
    enabled: !!promptId,
  })

  // Fetch intent explanation
  const { data: intentData } = useQuery({
    queryKey: ['prompt-intent', promptId],
    queryFn: () => promptsApi.explainIntent(promptId!),
    enabled: !!promptId,
  })

  // Fetch CWV data for matched pages
  const { data: cwvData, isLoading: cwvLoading, isFetching: cwvFetching } = useQuery({
    queryKey: ['prompt-cwv', promptId, forceRefreshCWV],
    queryFn: () => cwvApi.getForPrompt(promptId!, forceRefreshCWV),
    enabled: !!promptId && showCWV,
  })

  // Reset the refresh flag after fetch completes
  useEffect(() => {
    if (forceRefreshCWV && !cwvFetching) {
      setForceRefreshCWV(false)
    }
  }, [forceRefreshCWV, cwvFetching])

  // Function to trigger CWV refresh
  const handleRefreshCWV = () => {
    setForceRefreshCWV(true)
  }

  const prompt = data?.data as Prompt | undefined
  const bestMatchPageId = prompt?.matches?.[0]?.page_id

  // Fetch candidate prompts for best matched page
  const { 
    data: candidatePromptsData, 
    isLoading: candidatePromptsLoading,
    isFetching: candidatePromptsFetching,
  } = useQuery({
    queryKey: ['candidate-prompts', bestMatchPageId, forceRegenerate],
    queryFn: () => pagesApi.getCandidatePrompts(bestMatchPageId!, forceRegenerate),
    enabled: !!bestMatchPageId && showCandidatePrompts,
  })

  // Reset the regenerate flag after fetch completes
  useEffect(() => {
    if (forceRegenerate && !candidatePromptsFetching) {
      setForceRegenerate(false)
    }
  }, [forceRegenerate, candidatePromptsFetching])

  // Function to trigger regeneration
  const handleRegenerateCandidatePrompts = () => {
    setForceRegenerate(true)
  }
  const intentExplanation = intentData?.data as IntentExplanation | undefined
  const cwvResults = cwvData?.data?.matches as CWVPageResult[] | undefined
  const candidatePrompts = candidatePromptsData?.data as CandidatePromptsResponse | undefined

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-32 bg-slate-200 dark:bg-slate-800 rounded-lg" />
        <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-lg" />
      </div>
    )
  }

  if (!prompt) {
    return (
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-slate-400 mb-4" />
          <p className="text-slate-500">Prompt not found</p>
          <Button asChild className="mt-4">
            <Link to="/prompts">Back to Prompts</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  const statusConfig = matchStatusConfig[prompt.match_status as keyof typeof matchStatusConfig] || matchStatusConfig.pending
  const StatusIcon = statusConfig.icon

  return (
    <div className="space-y-6 max-w-4xl animate-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/prompts">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white line-clamp-1">
            {prompt.raw_text}
          </h2>
          <div className="flex items-center gap-2 mt-1">
            <Badge className={cn(
              "text-xs capitalize",
              intentColors[prompt.intent_label as keyof typeof intentColors] || intentColors.unknown
            )}>
              {prompt.intent_label}
            </Badge>
            <Badge variant="outline" className={cn("text-xs", statusConfig.textColor)}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {statusConfig.label}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Status Card */}
          <Card className="border-slate-200 dark:border-slate-800">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <div className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center",
                  statusConfig.color,
                  "bg-opacity-20"
                )}>
                  <StatusIcon className={cn("w-4 h-4", statusConfig.textColor)} />
                </div>
                Match Status
              </CardTitle>
              <CardDescription>{statusConfig.description}</CardDescription>
            </CardHeader>
            {prompt.best_match_score && (
              <CardContent className="pt-0">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-slate-500">Best match score:</span>
                  <Progress value={prompt.best_match_score * 100} className="flex-1 h-2" />
                  <span className="text-sm font-bold">
                    {Math.round(prompt.best_match_score * 100)}%
                  </span>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Why This Intent? - AI Analysis */}
          {intentExplanation && (
            <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-violet-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-violet-500" />
                  Why This Intent?
                  <Badge className="bg-gradient-to-r from-violet-500 to-purple-500 text-white text-[10px] font-medium">
                    <Sparkles className="w-3 h-3 mr-1" />
                    AI
                  </Badge>
                </CardTitle>
                <CardDescription>
                  AI-powered classification
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* AI Explanation */}
                <div className="p-3 rounded-lg bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-200 dark:border-violet-800">
                  <p className="text-sm text-slate-700 dark:text-slate-300">
                    {intentExplanation.explanation}
                  </p>
                </div>

                {/* Classification Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-violet-50 dark:bg-violet-900/20">
                    <div className="flex items-center gap-2 text-xs text-violet-600 dark:text-violet-400 mb-1">
                      <Zap className="w-3.5 h-3.5" />
                      Intent Type
                    </div>
                    <Badge className={cn(
                      "capitalize",
                      intentColors[intentExplanation.intent] || intentColors.unknown
                    )}>
                      {intentExplanation.intent.replace('_', ' ')}
                    </Badge>
                  </div>
                  <div className="p-3 rounded-lg bg-violet-50 dark:bg-violet-900/20">
                    <div className="flex items-center gap-2 text-xs text-violet-600 dark:text-violet-400 mb-1">
                      <Target className="w-3.5 h-3.5" />
                      AI Confidence
                    </div>
                    <span className="text-lg font-bold text-slate-900 dark:text-white">
                      {Math.round(intentExplanation.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {/* Transaction Score from AI */}
                <div className="pt-2 border-t border-violet-200 dark:border-violet-700">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-violet-600 dark:text-violet-400">Transaction Likelihood</span>
                    <span className={cn(
                      "font-bold",
                      intentExplanation.transaction_score >= 0.7 ? "text-emerald-500" :
                      intentExplanation.transaction_score >= 0.4 ? "text-amber-500" : "text-slate-500"
                    )}>
                      {Math.round(intentExplanation.transaction_score * 100)}%
                    </span>
                  </div>
                  <Progress value={intentExplanation.transaction_score * 100} className="h-2" />
                  <p className="text-xs text-slate-500 mt-2">
                    {intentExplanation.transaction_score >= 0.7 
                      ? "High likelihood of leading to a purchase or booking"
                      : intentExplanation.transaction_score >= 0.4
                      ? "Moderate purchase consideration - user may convert"
                      : "Low immediate conversion intent - primarily informational"
                    }
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Pattern Detection - Rule-based */}
          {intentExplanation?.signals && intentExplanation.signals.length > 0 && (
            <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-slate-400">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Info className="w-5 h-5 text-slate-500" />
                  Keyword Detection
                  <Badge variant="outline" className="text-[10px] text-slate-500">
                    Rule-Based
                  </Badge>
                </CardTitle>
                <CardDescription>
                  Keywords detected by pattern matching
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {intentExplanation.signals.map((signal, i) => (
                    <Badge 
                      key={i} 
                      variant="outline" 
                      className="text-xs font-mono bg-slate-50 dark:bg-slate-800"
                    >
                      {signal.replace('Matched: ', '').replace('AI: ', '')}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Matches */}
          {prompt.matches && prompt.matches.length > 0 && (
            <Card className="border-slate-200 dark:border-slate-800">
              <CardHeader>
                <CardTitle className="text-lg">
                  Content Matches ({prompt.matches.length})
                </CardTitle>
                <CardDescription>
                  Pages that match this prompt
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {prompt.matches.map((match, i) => (
                  <MatchCard key={i} match={match} />
                ))}
              </CardContent>
            </Card>
          )}

          {/* Opportunity */}
          {prompt.opportunity && (
            <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-amber-500">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-amber-500" />
                  Content Opportunity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-700 dark:text-slate-300">
                  {(prompt.opportunity as Record<string, unknown>).reason as string || 'This prompt represents a content opportunity.'}
                </p>
                <Button asChild className="mt-4">
                  <Link to="/opportunities">View All Opportunities</Link>
                </Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right column - Metadata */}
        <div className="space-y-6">
          {/* Scores */}
          <Card className="border-slate-200 dark:border-slate-800">
            <CardHeader>
              <CardTitle className="text-lg">Scores & Metrics</CardTitle>
              <CardDescription className="text-xs">From CSV import data</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Popularity - from CSV */}
              {prompt.popularity_score !== null && (
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-slate-500">
                      <BarChart3 className="w-4 h-4" />
                      Popularity
                    </span>
                    <span className="font-bold">
                      {Math.round(prompt.popularity_score * 100)}%
                    </span>
                  </div>
                  <Progress value={prompt.popularity_score * 100} className="mt-2 h-2" />
                  <p className="text-[10px] text-slate-400 mt-1">From CSV data</p>
                </div>
              )}

              {/* Sentiment - from CSV */}
              <Separator />
              <div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Sentiment</span>
                  {prompt.sentiment_score === null || prompt.sentiment_score === undefined ? (
                    <span className="text-slate-400 italic text-xs">Not available</span>
                  ) : prompt.sentiment_score === 0 ? (
                    <span className="text-slate-500 font-medium">Neutral</span>
                  ) : (
                    <span className={cn(
                      "font-bold",
                      prompt.sentiment_score > 0 ? "text-emerald-500" : "text-red-500"
                    )}>
                      {prompt.sentiment_score > 0 ? 'Positive' : 'Negative'} ({prompt.sentiment_score > 0 ? '+' : ''}{prompt.sentiment_score.toFixed(2)})
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 mt-1">From CSV data</p>
              </div>

              <Separator />

              {/* Semantic Match - from all-MiniLM-L6-v2 */}
              {prompt.best_match_score && (
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400">
                      <Sparkles className="w-4 h-4" />
                      Semantic Match
                    </span>
                    <span className="font-bold">
                      {Math.round(prompt.best_match_score * 100)}%
                    </span>
                  </div>
                  <Progress value={prompt.best_match_score * 100} className="mt-2 h-2" />
                  <p className="text-[10px] text-cyan-500 mt-1">all-MiniLM-L6-v2 embeddings</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card className="border-slate-200 dark:border-slate-800">
            <CardHeader>
              <CardTitle className="text-lg">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-3">
                <Hash className="w-4 h-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Word Count</p>
                  <p className="text-sm font-medium text-slate-900 dark:text-white">
                    {prompt.raw_text.split(/\s+/).length} words
                  </p>
                </div>
              </div>

              {prompt.topic && (
                <div className="flex items-center gap-3">
                  <MessageSquareText className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Topic</p>
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {prompt.topic}
                    </p>
                  </div>
                </div>
              )}

              {prompt.language && (
                <div className="flex items-center gap-3">
                  <Languages className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Language</p>
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {prompt.language.toUpperCase()}
                    </p>
                  </div>
                </div>
              )}

              {prompt.region && (
                <div className="flex items-center gap-3">
                  <MapPin className="w-4 h-4 text-slate-400" />
                  <div>
                    <p className="text-xs text-slate-500">Region</p>
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {prompt.region}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Candidate Prompts Section */}
          {prompt.matches && prompt.matches.length > 0 && (
            <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-emerald-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wand2 className="w-4 h-4 text-emerald-500" />
                    Candidate Prompts
                  </div>
                  <Button 
                    variant={showCandidatePrompts ? "secondary" : "default"}
                    size="sm"
                    onClick={() => setShowCandidatePrompts(!showCandidatePrompts)}
                    className={cn(
                      "text-xs h-7",
                      !showCandidatePrompts && "bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                    )}
                  >
                    {showCandidatePrompts ? 'Hide' : 'Generate'}
                  </Button>
                </CardTitle>
                <CardDescription className="text-xs">
                  AI-generated prompts for LLM citations
                </CardDescription>
              </CardHeader>
              {showCandidatePrompts && (
                <CardContent className="pt-0 space-y-3">
                  {candidatePromptsLoading || candidatePromptsFetching ? (
                    <div className="flex items-center gap-2 py-4">
                      <Loader2 className="w-4 h-4 animate-spin text-emerald-500" />
                      <span className="text-xs text-slate-500">Generating...</span>
                    </div>
                  ) : candidatePrompts && candidatePrompts.prompts.length > 0 ? (
                    <div className="space-y-2">
                      {candidatePrompts.prompts.map((cp, i) => (
                        <div 
                          key={i} 
                          className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700"
                        >
                          <p className="text-xs text-slate-700 dark:text-slate-300 mb-1.5">
                            "{cp.text}"
                          </p>
                          <div className="flex items-center gap-1.5">
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "text-[10px] px-1.5 py-0",
                                cp.transaction_score >= 0.7 ? "border-emerald-300 text-emerald-600" :
                                cp.transaction_score >= 0.4 ? "border-amber-300 text-amber-600" : 
                                "border-slate-300 text-slate-500"
                              )}
                            >
                              {Math.round(cp.transaction_score * 100)}%
                            </Badge>
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 capitalize">
                              {cp.intent}
                            </Badge>
                          </div>
                        </div>
                      ))}
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="w-full text-xs h-7"
                        onClick={handleRegenerateCandidatePrompts}
                        disabled={candidatePromptsFetching}
                      >
                        <RefreshCw className={cn("w-3 h-3 mr-1", candidatePromptsFetching && "animate-spin")} />
                        Regenerate
                      </Button>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-4">
                      No prompts generated
                    </p>
                  )}
                </CardContent>
              )}
            </Card>
          )}

          {/* Core Web Vitals Section */}
          {prompt.matches && prompt.matches.length > 0 && (
            <Card className="border-slate-200 dark:border-slate-800 border-l-4 border-l-violet-500">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-violet-500" />
                    Core Web Vitals
                  </div>
                  <Button 
                    variant={showCWV ? "secondary" : "default"}
                    size="sm"
                    onClick={() => setShowCWV(!showCWV)}
                    className={cn(
                      "text-xs h-7",
                      !showCWV && "bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600"
                    )}
                  >
                    {showCWV ? 'Hide' : 'Analyze'}
                  </Button>
                </CardTitle>
                <CardDescription className="text-xs">
                  PageSpeed Insights metrics
                </CardDescription>
              </CardHeader>
              {showCWV && (
                <CardContent className="pt-0 space-y-3">
                  {cwvLoading || cwvFetching ? (
                    <div className="flex items-center gap-2 py-4">
                      <Loader2 className="w-4 h-4 animate-spin text-violet-500" />
                      <span className="text-xs text-slate-500">Fetching CWV...</span>
                    </div>
                  ) : cwvResults && cwvResults.length > 0 ? (
                    <div className="space-y-2">
                      {cwvResults.slice(0, 2).map((result, i) => (
                        <div 
                          key={i} 
                          className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700"
                        >
                          <a 
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline truncate block mb-1.5"
                          >
                            {result.title || result.url}
                          </a>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {result.cwv.performance_score !== null && (
                              <Badge 
                                variant="outline" 
                                className={cn(
                                  "text-[10px] px-1.5 py-0",
                                  result.cwv.performance_score >= 90 ? "border-emerald-300 text-emerald-600" :
                                  result.cwv.performance_score >= 50 ? "border-amber-300 text-amber-600" : 
                                  "border-red-300 text-red-600"
                                )}
                              >
                                Score: {result.cwv.performance_score}
                              </Badge>
                            )}
                            <CWVScoreBadge score={result.cwv.lcp_score} label="LCP" />
                            <CWVScoreBadge score={result.cwv.cls_score} label="CLS" />
                          </div>
                        </div>
                      ))}
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="w-full text-xs h-7"
                        onClick={handleRefreshCWV}
                        disabled={cwvFetching}
                      >
                        <RefreshCw className={cn("w-3 h-3 mr-1", cwvFetching && "animate-spin")} />
                        Refresh
                      </Button>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 text-center py-4">
                      No CWV data available
                    </p>
                  )}
                </CardContent>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}


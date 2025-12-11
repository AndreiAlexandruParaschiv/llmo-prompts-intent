import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Swords,
  TrendingUp,
  Target,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Lightbulb,
  Zap,
  Trophy,
  ArrowRight,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { competitiveApi, HighIntentPrompt, CompetitiveAnalysis } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

function PromptAnalysisCard({ 
  prompt,
  onAnalyze,
  isAnalyzing 
}: { 
  prompt: HighIntentPrompt
  onAnalyze: (promptId: string) => void
  isAnalyzing: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [analysis, setAnalysis] = useState<{
    competitors: Array<{ url: string; title: string; snippet: string }>
    ai_analysis: CompetitiveAnalysis | null
    our_content: { url: string; title: string; snippet: string }
  } | null>(null)

  const handleAnalyze = async () => {
    try {
      const response = await competitiveApi.analyzePrompt(prompt.id)
      setAnalysis({
        competitors: response.data.competitors,
        ai_analysis: response.data.ai_analysis,
        our_content: response.data.our_content
      })
      setExpanded(true)
    } catch (error) {
      console.error('Analysis failed:', error)
    }
  }

  return (
    <Card className={cn(
      "border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-200",
      prompt.transaction_score >= 0.7 && "border-l-4 border-l-emerald-500"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold text-slate-900 dark:text-white">
              {prompt.text}
            </CardTitle>
            <CardDescription className="mt-1 flex items-center gap-3 text-xs">
              {prompt.topic && (
                <Badge variant="outline" className="text-xs">
                  {prompt.topic}
                </Badge>
              )}
              {prompt.intent_label && (
                <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 text-xs">
                  {prompt.intent_label}
                </Badge>
              )}
            </CardDescription>
          </div>
          <div className="flex flex-col items-end gap-2 flex-shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Transaction Likelihood</span>
              <Badge className={cn(
                "text-sm font-bold",
                prompt.transaction_score >= 0.7 
                  ? "bg-emerald-500 text-white" 
                  : prompt.transaction_score >= 0.5 
                    ? "bg-amber-500 text-white"
                    : "bg-slate-500 text-white"
              )}>
                {Math.round(prompt.transaction_score * 100)}%
              </Badge>
            </div>
            {prompt.best_match && (
              <span className="text-xs text-slate-500">
                Match: {Math.round(prompt.best_match.score * 100)}%
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0 space-y-4">
        {/* Our matching content */}
        {prompt.best_match && (
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 mb-2">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="font-medium">Your Content</span>
            </div>
            <a 
              href={prompt.best_match.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-sm text-blue-700 dark:text-blue-300 hover:underline flex items-center gap-1"
            >
              {prompt.best_match.title || prompt.best_match.url}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}

        {/* Analyze button or results */}
        {!analysis ? (
          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="w-full bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing competitors...
              </>
            ) : (
              <>
                <Swords className="w-4 h-4 mr-2" />
                Analyze Competition
              </>
            )}
          </Button>
        ) : (
          <div className="space-y-4">
            {/* Toggle for detailed view */}
            <div 
              className="flex items-center justify-between cursor-pointer p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-800"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Competitive Analysis Results
                </span>
                <Badge variant="outline" className="text-xs">
                  {analysis.competitors.length} competitors found
                </Badge>
              </div>
              {expanded ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </div>

            {expanded && (
              <div className="space-y-4">
                {/* Competitors */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                    <Swords className="w-4 h-4 text-red-500" />
                    Competitor Results
                  </h4>
                  {analysis.competitors.length > 0 ? (
                    <div className="space-y-2">
                      {analysis.competitors.map((comp, idx) => (
                        <div 
                          key={idx}
                          className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                        >
                          <a 
                            href={comp.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-red-700 dark:text-red-300 hover:underline flex items-center gap-1"
                          >
                            {comp.title}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 line-clamp-2">
                            {comp.snippet}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">No competitor results found</p>
                  )}
                </div>

                {/* AI Analysis */}
                {analysis.ai_analysis && (
                  <div className="space-y-4 p-4 rounded-lg bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-200 dark:border-violet-800">
                    <div className="flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-violet-500" />
                      <span className="font-medium text-slate-700 dark:text-slate-300">AI Recommendations</span>
                      <Badge className={cn(
                        "text-xs",
                        analysis.ai_analysis.priority === 'high' 
                          ? "bg-red-500 text-white" 
                          : analysis.ai_analysis.priority === 'medium'
                            ? "bg-amber-500 text-white"
                            : "bg-slate-500 text-white"
                      )}>
                        {analysis.ai_analysis.priority} priority
                      </Badge>
                    </div>

                    {/* Competitive Gaps */}
                    {analysis.ai_analysis.competitive_gap.length > 0 && (
                      <div>
                        <h5 className="text-xs font-medium text-red-600 dark:text-red-400 mb-2 flex items-center gap-1">
                          <XCircle className="w-3.5 h-3.5" />
                          Competitive Gaps
                        </h5>
                        <ul className="space-y-1">
                          {analysis.ai_analysis.competitive_gap.map((gap, idx) => (
                            <li key={idx} className="text-sm text-slate-600 dark:text-slate-400 flex items-start gap-2">
                              <span className="text-red-500 mt-1">•</span>
                              {gap}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Our Strengths */}
                    {analysis.ai_analysis.our_strengths.length > 0 && (
                      <div>
                        <h5 className="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Your Strengths
                        </h5>
                        <ul className="space-y-1">
                          {analysis.ai_analysis.our_strengths.map((strength, idx) => (
                            <li key={idx} className="text-sm text-slate-600 dark:text-slate-400 flex items-start gap-2">
                              <span className="text-emerald-500 mt-1">•</span>
                              {strength}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommendations */}
                    {analysis.ai_analysis.recommendations.length > 0 && (
                      <div>
                        <h5 className="text-xs font-medium text-violet-600 dark:text-violet-400 mb-2 flex items-center gap-1">
                          <Zap className="w-3.5 h-3.5" />
                          Actions to Take
                        </h5>
                        <div className="space-y-2">
                          {analysis.ai_analysis.recommendations.map((rec, idx) => (
                            <div 
                              key={idx} 
                              className="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-start justify-between gap-2"
                            >
                              <span className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-2">
                                <ArrowRight className="w-3.5 h-3.5 text-violet-500 flex-shrink-0" />
                                {rec.action}
                              </span>
                              <div className="flex gap-1 flex-shrink-0">
                                <Badge variant="outline" className={cn(
                                  "text-[10px]",
                                  rec.impact === 'high' ? "border-emerald-500 text-emerald-600" : ""
                                )}>
                                  {rec.impact} impact
                                </Badge>
                                <Badge variant="outline" className={cn(
                                  "text-[10px]",
                                  rec.effort === 'low' ? "border-blue-500 text-blue-600" : ""
                                )}>
                                  {rec.effort} effort
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* CTA Recommendation */}
                    {analysis.ai_analysis.cta_recommendation && (
                      <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
                        <h5 className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">
                          Suggested Call-to-Action
                        </h5>
                        <p className="text-sm text-slate-700 dark:text-slate-300">
                          "{analysis.ai_analysis.cta_recommendation}"
                        </p>
                      </div>
                    )}

                    {/* Content Suggestions */}
                    {analysis.ai_analysis.content_suggestions && (
                      <div className="text-sm text-slate-600 dark:text-slate-400 border-t border-violet-200 dark:border-violet-700 pt-3 mt-3">
                        <strong className="text-slate-700 dark:text-slate-300">Content Improvements: </strong>
                        {analysis.ai_analysis.content_suggestions}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function CompetitiveAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { selectedProjectId } = useProjectStore()
  const { toast } = useToast()
  
  const [page, setPage] = useState(1)
  const [minScore, setMinScore] = useState(searchParams.get('min_score') || '50')
  const [matchStatus, setMatchStatus] = useState(searchParams.get('status') || 'answered')
  const [analyzingId, setAnalyzingId] = useState<string | null>(null)
  const pageSize = 20

  const projectId = searchParams.get('project_id') || selectedProjectId

  // Get summary stats
  const { data: summary } = useQuery({
    queryKey: ['competitive-summary', projectId, minScore],
    queryFn: async () => {
      if (!projectId) return null
      const response = await competitiveApi.getSummary(projectId, parseInt(minScore) / 100)
      return response.data
    },
    enabled: !!projectId,
  })

  // Get high-intent prompts
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['competitive-prompts', projectId, minScore, matchStatus, page],
    queryFn: async () => {
      if (!projectId) return null
      const response = await competitiveApi.getHighIntentPrompts({
        project_id: projectId,
        min_transaction_score: parseInt(minScore) / 100,
        match_status: matchStatus,
        page,
        page_size: pageSize,
      })
      return response.data
    },
    enabled: !!projectId,
  })

  const handleFilterChange = (key: string, value: string) => {
    if (key === 'min_score') setMinScore(value)
    if (key === 'status') setMatchStatus(value)
    setPage(1)
    const params = new URLSearchParams(searchParams)
    params.set(key, value)
    setSearchParams(params)
  }

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <Swords className="w-16 h-16 text-slate-300 mb-4" />
        <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          No Project Selected
        </h2>
        <p className="text-slate-500 dark:text-slate-400">
          Choose a project from the sidebar to analyze competitive position.
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <AlertTriangle className="w-16 h-16 text-red-400 mb-4" />
        <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          Error Loading Data
        </h2>
        <p className="text-slate-500 dark:text-slate-400 mb-4">
          {(error as Error).message}
        </p>
        <Button onClick={() => refetch()}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Swords className="w-7 h-7 text-violet-500" />
            Competitive Analysis
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Compare your high-intent transactional content against competitors
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Min Transaction Score Filter */}
          <Select value={minScore} onValueChange={(v) => handleFilterChange('min_score', v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Min intent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="50">≥50% intent</SelectItem>
              <SelectItem value="60">≥60% intent</SelectItem>
              <SelectItem value="70">≥70% intent</SelectItem>
              <SelectItem value="80">≥80% intent</SelectItem>
            </SelectContent>
          </Select>

          {/* Match Status Filter */}
          <Select value={matchStatus} onValueChange={(v) => handleFilterChange('status', v)}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="answered">Answered</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
              <SelectItem value="all">All</SelectItem>
            </SelectContent>
          </Select>
          
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => refetch()}
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
                <Target className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.total_high_intent}</p>
                <p className="text-xs text-slate-500">High-Intent Prompts</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.answered_high_intent}</p>
                <p className="text-xs text-slate-500">With Content Match</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/30">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {Math.round(summary.avg_transaction_score * 100)}%
                </p>
                <p className="text-xs text-slate-500">Avg Transaction Score</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center shadow-lg shadow-red-500/30">
                <Swords className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{summary.partial_high_intent}</p>
                <p className="text-xs text-slate-500">Needs Improvement</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Top Topics */}
      {summary?.top_topics && summary.top_topics.length > 0 && (
        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Top High-Intent Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {summary.top_topics.map((topic, idx) => (
                <Badge key={idx} variant="outline" className="text-sm">
                  {topic.topic} <span className="ml-1 text-slate-400">({topic.count})</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prompts List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="border-slate-200 dark:border-slate-800">
              <CardContent className="p-6">
                <div className="space-y-3">
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-20 w-full" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : data?.prompts.length === 0 ? (
        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-12 text-center">
            <Target className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
              No High-Intent Prompts Found
            </h3>
            <p className="text-slate-500 dark:text-slate-400">
              Try lowering the minimum transaction score filter to see more results.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {data?.prompts.map((prompt) => (
            <PromptAnalysisCard 
              key={prompt.id} 
              prompt={prompt}
              onAnalyze={() => {}}
              isAnalyzing={analyzingId === prompt.id}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total > pageSize && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
          <p className="text-sm text-slate-500">
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, data.total)} of {data.total}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p + 1)}
              disabled={page * pageSize >= data.total}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}


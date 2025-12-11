import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  FileQuestion,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Loader2,
  Target,
  Users,
  Tag,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { pagesApi, OrphanPage } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { cn } from '@/lib/utils'
import { useToast } from '@/components/ui/use-toast'

const intentColors: Record<string, string> = {
  transactional: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  informational: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  commercial: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  navigational: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  comparison: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
}

function OrphanPageCard({ 
  page, 
  onGenerateSuggestions 
}: { 
  page: OrphanPage
  onGenerateSuggestions: (pageId: string) => void 
}) {
  const [expanded, setExpanded] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerateSuggestions = async () => {
    setIsGenerating(true)
    try {
      await onGenerateSuggestions(page.id)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Card className={cn(
      "border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-200",
      page.match_status === 'no_matches' && "border-l-4 border-l-red-500"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold text-slate-900 dark:text-white truncate">
              {page.title || 'Untitled Page'}
            </CardTitle>
            <CardDescription className="mt-1 flex items-center gap-2 text-xs">
              <a 
                href={page.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline flex items-center gap-1 truncate max-w-md"
              >
                {page.url}
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
              </a>
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge variant={page.match_status === 'no_matches' ? 'destructive' : 'secondary'}>
              {page.match_status === 'no_matches' ? 'No Matches' : `${page.best_match_score}% best`}
            </Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0 space-y-4">
        {page.meta_description && (
          <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
            {page.meta_description}
          </p>
        )}
        
        {/* AI Suggestions */}
        {page.ai_suggestion ? (
          <div className="space-y-3">
            <div 
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setExpanded(!expanded)}
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-500" />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  AI Suggested Prompts
                </span>
                <Badge className="bg-gradient-to-r from-violet-500 to-purple-500 text-white text-[10px]">
                  AI
                </Badge>
              </div>
              {expanded ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </div>
            
            {expanded && (
              <div className="space-y-4 p-4 rounded-lg bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-200 dark:border-violet-800">
                {/* Content Summary */}
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  {page.ai_suggestion.content_summary}
                </div>
                
                {/* Suggested Prompts */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs text-violet-600 dark:text-violet-400">
                    <Search className="w-3.5 h-3.5" />
                    <span className="font-medium">Candidate Prompts</span>
                  </div>
                  <div className="space-y-2">
                    {page.ai_suggestion.suggested_prompts.map((prompt, idx) => (
                      <div 
                        key={idx}
                        className="flex items-start gap-2 p-2 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
                      >
                        <span className="text-xs text-slate-400 font-mono mt-0.5">{idx + 1}.</span>
                        <span className="text-sm text-slate-700 dark:text-slate-300">{prompt}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* Metadata Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-violet-200 dark:border-violet-700">
                  {/* Primary Intent */}
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-violet-500" />
                    <div className="text-xs">
                      <span className="text-slate-500">Intent: </span>
                      <Badge className={cn(
                        "text-[10px] capitalize",
                        intentColors[page.ai_suggestion.primary_intent] || 'bg-slate-100 text-slate-700'
                      )}>
                        {page.ai_suggestion.primary_intent}
                      </Badge>
                    </div>
                  </div>
                  
                  {/* Target Audience */}
                  <div className="flex items-start gap-2">
                    <Users className="w-4 h-4 text-violet-500 mt-0.5" />
                    <div className="text-xs">
                      <span className="text-slate-500">Audience: </span>
                      <span className="text-slate-700 dark:text-slate-300">
                        {page.ai_suggestion.target_audience}
                      </span>
                    </div>
                  </div>
                  
                  {/* Keywords */}
                  <div className="flex items-start gap-2">
                    <Tag className="w-4 h-4 text-violet-500 mt-0.5" />
                    <div className="flex flex-wrap gap-1">
                      {page.ai_suggestion.top_keywords?.slice(0, 3).map((keyword, idx) => (
                        <Badge 
                          key={idx} 
                          variant="outline" 
                          className="text-[10px] bg-violet-50 dark:bg-violet-900/20"
                        >
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {!expanded && (
              <div className="flex flex-wrap gap-2">
                {page.ai_suggestion.suggested_prompts.slice(0, 2).map((prompt, idx) => (
                  <Badge 
                    key={idx} 
                    variant="outline" 
                    className="text-xs bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-700"
                  >
                    "{prompt.substring(0, 40)}{prompt.length > 40 ? '...' : ''}"
                  </Badge>
                ))}
                {page.ai_suggestion.suggested_prompts.length > 2 && (
                  <Badge variant="secondary" className="text-xs">
                    +{page.ai_suggestion.suggested_prompts.length - 2} more
                  </Badge>
                )}
              </div>
            )}
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateSuggestions}
            disabled={isGenerating}
            className="w-full"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Generating suggestions...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate AI Suggestions
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

export default function OrphanPages() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { selectedProjectId } = useProjectStore()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  
  const [page, setPage] = useState(1)
  const [threshold, setThreshold] = useState(searchParams.get('threshold') || '50')
  const pageSize = 20

  const projectId = searchParams.get('project_id') || selectedProjectId

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['orphan-pages', projectId, threshold, page],
    queryFn: async () => {
      if (!projectId) return null
      const response = await pagesApi.getOrphanPages({
        project_id: projectId,
        min_match_threshold: parseInt(threshold) / 100,
        page,
        page_size: pageSize,
        include_suggestions: true,
      })
      return response.data
    },
    enabled: !!projectId,
  })

  const generateSuggestionsMutation = useMutation({
    mutationFn: (pageId: string) => pagesApi.generateOrphanSuggestions(pageId),
    onSuccess: (response) => {
      toast({
        title: 'Success',
        description: 'Suggestions generated successfully',
      })
      // Update the cache with the new suggestion
      queryClient.setQueryData(
        ['orphan-pages', projectId, threshold, page],
        (oldData: typeof data) => {
          if (!oldData) return oldData
          return {
            ...oldData,
            orphan_pages: oldData.orphan_pages.map((p: OrphanPage) => 
              p.id === response.data.page_id 
                ? { ...p, ai_suggestion: response.data.suggestion }
                : p
            ),
          }
        }
      )
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to generate suggestions',
        variant: 'destructive',
      })
    },
  })

  const handleThresholdChange = (value: string) => {
    setThreshold(value)
    setPage(1)
    const params = new URLSearchParams(searchParams)
    params.set('threshold', value)
    setSearchParams(params)
  }

  if (!projectId) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <FileQuestion className="w-16 h-16 text-slate-300 mb-4" />
        <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          No Project Selected
        </h2>
        <p className="text-slate-500 dark:text-slate-400">
          Choose a project from the sidebar to view orphan pages.
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
            <FileQuestion className="w-7 h-7 text-amber-500" />
            Orphan Pages
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Pages that don't match any user prompts well — discover potential content opportunities
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Threshold Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <Select value={threshold} onValueChange={handleThresholdChange}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Match threshold" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">Below 30% match</SelectItem>
                <SelectItem value="50">Below 50% match</SelectItem>
                <SelectItem value="70">Below 70% match</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => refetch()}
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/30">
                <FileQuestion className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{data.total}</p>
                <p className="text-xs text-slate-500">Orphan Pages</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center shadow-lg shadow-red-500/30">
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {data.orphan_pages.filter(p => p.match_status === 'no_matches').length}
                </p>
                <p className="text-xs text-slate-500">No Matches At All</p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-slate-200 dark:border-slate-800">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-lg shadow-violet-500/30">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {data.ai_enabled ? 'Enabled' : 'Disabled'}
                </p>
                <p className="text-xs text-slate-500">AI Suggestions</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Page List */}
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
      ) : data?.orphan_pages.length === 0 ? (
        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-12 text-center">
            <FileQuestion className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
              No Orphan Pages Found
            </h3>
            <p className="text-slate-500 dark:text-slate-400">
              All your pages have good matches with user prompts. Great job!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {data?.orphan_pages.map((page) => (
            <OrphanPageCard 
              key={page.id} 
              page={page}
              onGenerateSuggestions={(pageId) => generateSuggestionsMutation.mutate(pageId)}
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


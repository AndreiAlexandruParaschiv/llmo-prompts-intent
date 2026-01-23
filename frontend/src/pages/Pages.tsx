import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Globe,
  Search,
  ExternalLink,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Play,
  Languages,
  Code,
  Link2,
  Download,
  Sparkles,
  Loader2,
  Upload,
  ChevronDown,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { pagesApi, projectsApi, Page } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

function PageCard({ page }: { page: Page }) {
  return (
    <Card className="border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-200">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
            <Globe className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <a
                href={page.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-cyan-600 dark:text-cyan-400 hover:underline truncate"
              >
                {page.url}
              </a>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            </div>
            
            {page.title && (
              <p className="text-slate-900 dark:text-white font-medium mt-1 line-clamp-1">
                {page.title}
              </p>
            )}
            
            {page.meta_description && (
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                {page.meta_description}
              </p>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-3 mt-3">
              {page.status_code && (
                <Badge 
                  variant={page.status_code.startsWith('2') ? 'default' : 'destructive'}
                  className="text-xs"
                >
                  {page.status_code}
                </Badge>
              )}

              {page.word_count && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <FileText className="w-3.5 h-3.5" />
                  {page.word_count} words
                </span>
              )}

              {page.hreflang_tags && page.hreflang_tags.length > 0 && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Languages className="w-3.5 h-3.5" />
                  {page.hreflang_tags.length} langs
                </span>
              )}

              {page.structured_data && page.structured_data.length > 0 && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Code className="w-3.5 h-3.5" />
                  JSON-LD
                </span>
              )}

              {page.crawled_at && (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="w-3.5 h-3.5" />
                  {format(new Date(page.crawled_at), 'MMM d, h:mm a')}
                </span>
              )}
            </div>

            {/* MCP Checks */}
            {page.mcp_checks && Object.keys(page.mcp_checks).length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {Object.entries(page.mcp_checks).map(([key, value]) => (
                  <Badge 
                    key={key} 
                    variant="outline" 
                    className={cn(
                      "text-xs",
                      value ? "border-emerald-500 text-emerald-600" : "border-slate-300 text-slate-500"
                    )}
                  >
                    {value ? <CheckCircle2 className="w-3 h-3 mr-1" /> : null}
                    {key.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Pages() {
  const { selectedProjectId } = useProjectStore()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [filterType, setFilterType] = useState<string | null>(null)
  
  // Reset page when search or filter changes
  const handleSearchChange = (value: string) => {
    setSearch(value)
    setPage(1)
  }
  
  const handleFilterChange = (filter: string | null) => {
    setFilterType(filter === filterType ? null : filter) // Toggle off if clicking same filter
    setPage(1)
  }

  // Fetch pages
  const { data, isLoading } = useQuery({
    queryKey: ['pages', { projectId: selectedProjectId, search, filterType, page }],
    queryFn: () => pagesApi.list({
      project_id: selectedProjectId || undefined,
      search: search || undefined,
      filter_type: filterType || undefined,
      page,
      page_size: 20,
    }),
  })

  // Fetch pages stats
  const { data: statsData } = useQuery({
    queryKey: ['pages-stats', selectedProjectId],
    queryFn: () => pagesApi.getStats(selectedProjectId || undefined),
  })

  // Fetch crawl jobs
  const { data: crawlJobsData } = useQuery({
    queryKey: ['crawl-jobs', selectedProjectId],
    queryFn: () => pagesApi.getCrawlJobs(selectedProjectId || undefined),
    enabled: !!selectedProjectId,
  })
  
  const pageStats = statsData?.data

  // File input ref for CSV crawl
  const csvFileInputRef = useRef<HTMLInputElement>(null)

  // Start crawl mutation
  const crawlMutation = useMutation({
    mutationFn: () => projectsApi.startCrawl(selectedProjectId!),
    onSuccess: () => {
      toast({ title: 'Crawl started', description: 'Pages are being crawled in the background.' })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs'] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start crawl', description: error.message, variant: 'destructive' })
    },
  })

  // Crawl from CSV mutation (with SEO keyword data)
  const csvCrawlMutation = useMutation({
    mutationFn: (file: File) => projectsApi.crawlFromCsv(selectedProjectId!, file),
    onSuccess: (response) => {
      const data = response.data
      toast({ 
        title: 'CSV Crawl Started', 
        description: `Crawling ${data.urls_to_crawl} URLs. ${data.urls_with_seo_data} have SEO keyword data.` 
      })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs'] })
      queryClient.invalidateQueries({ queryKey: ['pages'] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start CSV crawl', description: error.message, variant: 'destructive' })
    },
  })

  // Handle CSV file selection for crawl
  const handleCsvFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      csvCrawlMutation.mutate(file)
    }
    e.target.value = ''
  }

  // Generate candidate prompts batch mutation
  const generatePromptsMutation = useMutation({
    mutationFn: (regenerate: boolean = false) => 
      pagesApi.generateCandidatePromptsBatch(selectedProjectId!, regenerate, 5),
    onSuccess: (response) => {
      const data = response.data
      if (data.status === 'processing') {
        toast({ 
          title: 'Generating Candidate Prompts', 
          description: `Processing ${data.pages_queued} pages. This may take a few minutes.` 
        })
      } else if (data.status === 'no_pages') {
        toast({ title: 'No Pages to Process', description: data.message })
      }
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to generate prompts', description: error.message, variant: 'destructive' })
    },
  })

  // Export candidate prompts as CSV
  const handleExportCandidatePrompts = async () => {
    if (!selectedProjectId) return
    try {
      const response = await pagesApi.exportCandidatePromptsCsv(selectedProjectId)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `candidate-prompts-${selectedProjectId}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
      toast({ title: 'Export Complete', description: 'Candidate prompts CSV downloaded successfully.' })
    } catch (error) {
      toast({ title: 'Export failed', description: 'No candidate prompts found. Generate prompts first.', variant: 'destructive' })
    }
  }

  const pages = data?.data?.pages || []
  const total = data?.data?.total || 0
  const pageSize = 20
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Crawled Pages</h2>
          <p className="text-slate-500 dark:text-slate-400">
            {total} pages {selectedProjectId ? 'in this project' : 'across all projects'}
          </p>
        </div>
        {selectedProjectId && (
          <div className="flex items-center gap-2">
            {/* Candidate Prompts Actions */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Sparkles className="w-4 h-4" />
                  Candidate Prompts
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem 
                  onClick={() => generatePromptsMutation.mutate(false)}
                  disabled={generatePromptsMutation.isPending}
                >
                  {generatePromptsMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 mr-2" />
                  )}
                  Generate for All Pages
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={() => generatePromptsMutation.mutate(true)}
                  disabled={generatePromptsMutation.isPending}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Regenerate All
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleExportCandidatePrompts}>
                  <Download className="w-4 h-4 mr-2" />
                  Export as CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Hidden file input for CSV crawl */}
            <input
              type="file"
              ref={csvFileInputRef}
              onChange={handleCsvFileSelect}
              accept=".csv"
              className="hidden"
            />
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  disabled={crawlMutation.isPending || csvCrawlMutation.isPending}
                  className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600"
                >
                  {(crawlMutation.isPending || csvCrawlMutation.isPending) ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Crawl
                  <ChevronDown className="w-4 h-4 ml-2" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => crawlMutation.mutate()}>
                  <Play className="w-4 h-4 mr-2" />
                  Start Crawl (from domains)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => csvFileInputRef.current?.click()}>
                  <Upload className="w-4 h-4 mr-2" />
                  Crawl from CSV (with keywords)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* Search */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by URL or title..."
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats - clickable filters */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card 
          className={cn(
            "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
            filterType === null && "ring-2 ring-cyan-500"
          )}
          onClick={() => handleFilterChange(null)}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                <Globe className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {pageStats?.total || total}
                </p>
                <p className="text-xs text-slate-500">Total Pages</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={cn(
            "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
            filterType === 'successful' && "ring-2 ring-cyan-500"
          )}
          onClick={() => handleFilterChange('successful')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {pageStats?.successful || 0}
                </p>
                <p className="text-xs text-slate-500">Successful (2xx)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={cn(
            "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
            filterType === 'failed' && "ring-2 ring-cyan-500"
          )}
          onClick={() => handleFilterChange('failed')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {pageStats?.failed || 0}
                </p>
                <p className="text-xs text-slate-500">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={cn(
            "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
            filterType === 'with_jsonld' && "ring-2 ring-cyan-500"
          )}
          onClick={() => handleFilterChange('with_jsonld')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                <Code className="w-5 h-5 text-violet-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {pageStats?.with_jsonld || 0}
                </p>
                <p className="text-xs text-slate-500">With JSON-LD</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card 
          className={cn(
            "border-slate-200 dark:border-slate-800 cursor-pointer hover:shadow-md transition-all",
            filterType === 'with_hreflang' && "ring-2 ring-cyan-500"
          )}
          onClick={() => handleFilterChange('with_hreflang')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <Languages className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {pageStats?.with_hreflang || 0}
                </p>
                <p className="text-xs text-slate-500">Multi-language</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pages List */}
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
      ) : pages.length === 0 ? (
        <Card className="border-dashed border-2 border-slate-200 dark:border-slate-800">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Globe className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              No pages crawled yet
            </h3>
            <p className="text-slate-500 text-center max-w-sm mb-4">
              {selectedProjectId 
                ? 'Start a crawl to index pages from your target domains.'
                : 'Select a project to view and crawl pages.'}
            </p>
            {selectedProjectId && (
              <div className="flex gap-2">
                <Button
                  onClick={() => crawlMutation.mutate()}
                  disabled={crawlMutation.isPending || csvCrawlMutation.isPending}
                >
                  <Play className="w-4 h-4 mr-2" />
                  Start Crawl
                </Button>
                <Button
                  variant="outline"
                  onClick={() => csvFileInputRef.current?.click()}
                  disabled={crawlMutation.isPending || csvCrawlMutation.isPending}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Crawl from CSV
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {pages.map((p) => (
              <PageCard key={p.id} page={p} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
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


import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Upload, 
  Globe, 
  Sparkles, 
  Settings,
  Play,
  RefreshCw,
  MessageSquareText,
  Lightbulb,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  Link as LinkIcon,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { projectsApi, csvApi, pagesApi, jobsApi, Project, ProjectStats, CSVImport } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'

function OverviewTab({ project, stats }: { project: Project; stats?: ProjectStats }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [showUrlImport, setShowUrlImport] = useState(false)
  const [urlsText, setUrlsText] = useState('')
  const [matchTaskId, setMatchTaskId] = useState<string | null>(null)
  const [matchProgress, setMatchProgress] = useState<{processed: number, total: number, matched: number, opportunities: number} | null>(null)
  
  // Get active imports
  const { data: importsData } = useQuery({
    queryKey: ['csv-imports', project.id],
    queryFn: () => csvApi.list(project.id),
    refetchInterval: 3000, // Poll every 3 seconds
  })
  
  const activeImport = importsData?.data?.imports?.find?.((imp: CSVImport) => 
    imp.status === 'processing'
  )
  
  // Get active crawl jobs
  const { data: crawlJobsData } = useQuery({
    queryKey: ['crawl-jobs', project.id],
    queryFn: () => pagesApi.getCrawlJobs(project.id),
    refetchInterval: 5000, // Poll every 5 seconds
  })
  
  const activeCrawl = crawlJobsData?.data?.crawl_jobs?.find?.((job: any) => 
    job.status === 'running' || job.status === 'pending'
  )
  
  // Calculate step completion
  const importComplete = (stats?.total_prompts || 0) > 0
  const crawlComplete = (stats?.total_pages || 0) > 0
  const matchComplete = Object.keys(stats?.by_match_status || {}).some(k => k !== 'PENDING' && k !== 'pending')
  const opportunitiesCount = Object.values(stats?.opportunities_by_status || {}).reduce((a, b) => (a as number) + (b as number), 0) as number

  const crawlMutation = useMutation({
    mutationFn: () => projectsApi.startCrawl(project.id),
    onSuccess: () => {
      toast({ title: 'Crawl started', description: 'Pages are being crawled in the background.' })
      queryClient.invalidateQueries({ queryKey: ['project', project.id] })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs', project.id] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start crawl', description: error.message, variant: 'destructive' })
    },
  })
  
  const cancelCrawlMutation = useMutation({
    mutationFn: (jobId: string) => pagesApi.cancelCrawlJob(jobId),
    onSuccess: () => {
      toast({ title: 'Crawl cancelled', description: 'The crawl job has been stopped.' })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs', project.id] })
      queryClient.invalidateQueries({ queryKey: ['project-stats', project.id] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to cancel crawl', description: error.message, variant: 'destructive' })
    },
  })

  const importUrlsMutation = useMutation({
    mutationFn: (urls: string[]) => pagesApi.importUrls(project.id, urls),
    onSuccess: (response) => {
      toast({ 
        title: 'URL import started', 
        description: `Crawling ${response.data.url_count} URLs in the background.`
      })
      setShowUrlImport(false)
      setUrlsText('')
      queryClient.invalidateQueries({ queryKey: ['project', project.id] })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs', project.id] })
      queryClient.invalidateQueries({ queryKey: ['project-stats', project.id] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to import URLs', description: error.message, variant: 'destructive' })
    },
  })

  const handleUrlImport = () => {
    const urls = urlsText
      .split('\n')
      .map(u => u.trim())
      .filter(u => u && !u.startsWith('#'))
    
    if (urls.length === 0) {
      toast({ title: 'No URLs', description: 'Please enter at least one URL.', variant: 'destructive' })
      return
    }
    
    importUrlsMutation.mutate(urls)
  }

  // File input ref for CSV crawl
  const csvCrawlInputRef = useRef<HTMLInputElement>(null)
  
  // File input ref for example prompts import
  const examplePromptsInputRef = useRef<HTMLInputElement>(null)
  
  // State for CSV crawl limit (top N pages by traffic)
  const [csvCrawlLimit, setCsvCrawlLimit] = useState<number | undefined>(200)

  // Crawl from CSV mutation (with SEO keyword data)
  const csvCrawlMutation = useMutation({
    mutationFn: (file: File) => projectsApi.crawlFromCsv(project.id, file, csvCrawlLimit),
    onSuccess: (response) => {
      const data = response.data
      const limitMsg = data.limit_applied 
        ? ` (top ${data.limit_applied} of ${data.total_urls_in_csv} by traffic)` 
        : ''
      toast({ 
        title: 'CSV Crawl Started', 
        description: `Crawling ${data.urls_to_crawl} URLs${limitMsg}. ${data.urls_with_seo_data} have SEO keyword data.` 
      })
      queryClient.invalidateQueries({ queryKey: ['crawl-jobs', project.id] })
      queryClient.invalidateQueries({ queryKey: ['project-stats', project.id] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start CSV crawl', description: error.message, variant: 'destructive' })
    },
  })

  // Handle CSV file selection for crawl
  const handleCsvCrawlSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      csvCrawlMutation.mutate(file)
    }
    e.target.value = ''
  }

  // Import example prompts mutation (for few-shot learning)
  const importExamplesMutation = useMutation({
    mutationFn: (file: File) => projectsApi.importExamplePrompts(project.id, file),
    onSuccess: (response) => {
      const data = response.data
      toast({ 
        title: 'Example Prompts Imported', 
        description: data.message
      })
      queryClient.invalidateQueries({ queryKey: ['project', project.id] })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to import examples', description: error.message, variant: 'destructive' })
    },
  })

  // Handle example prompts file selection
  const handleExamplePromptsSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      importExamplesMutation.mutate(file)
    }
    e.target.value = ''
  }

  const matchMutation = useMutation({
    mutationFn: () => projectsApi.runMatching(project.id),
    onSuccess: (response) => {
      const taskId = response.data?.task_id
      toast({ title: 'Matching started', description: 'Comparing prompts to crawled pages...' })
      setMatchTaskId(taskId)
      setMatchProgress({ processed: 0, total: stats?.total_prompts || 0, matched: 0, opportunities: 0 })
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to start matching', description: error.message, variant: 'destructive' })
    },
  })
  
  // Poll for match job status
  const { data: matchJobData } = useQuery({
    queryKey: ['match-job', matchTaskId],
    queryFn: () => jobsApi.getStatus(matchTaskId!),
    enabled: !!matchTaskId,
    refetchInterval: 2000, // Poll every 2 seconds
  })
  
  // Update match progress and detect completion
  useEffect(() => {
    if (!matchJobData?.data) return
    
    const job = matchJobData.data
    if (job.status === 'PROGRESS' && job.progress) {
      setMatchProgress(job.progress)
    } else if (job.ready) {
      // Job completed
      setMatchTaskId(null)
      setMatchProgress(null)
      queryClient.invalidateQueries({ queryKey: ['project-stats', project.id] })
      if (job.result?.opportunities > 0) {
        toast({ 
          title: 'Matching complete', 
          description: `Found ${job.result.opportunities} content opportunities!` 
        })
      } else {
        toast({ title: 'Matching complete', description: 'All prompts matched to existing content.' })
      }
    }
  }, [matchJobData, project.id, queryClient, toast])

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total Prompts</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">
                  {stats?.total_prompts || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <MessageSquareText className="w-6 h-6 text-cyan-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Crawled Pages</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">
                  {stats?.total_pages || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <Globe className="w-6 h-6 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Opportunities</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">
                  {Object.values(stats?.opportunities_by_status || {}).reduce((a, b) => a + b, 0)}
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <Lightbulb className="w-6 h-6 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Workflow Steps */}
      {/* Optional: Import Example Prompts for better AI generation */}
      <Card className="border-violet-200 dark:border-violet-800 bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-900/10 dark:to-purple-900/10">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-violet-600 dark:text-violet-400" />
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 dark:text-white">Human Prompt Examples</h4>
                <p className="text-sm text-slate-500">
                  Import real human prompts to improve AI-generated candidate prompts
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Hidden file input */}
              <input
                type="file"
                ref={examplePromptsInputRef}
                onChange={handleExamplePromptsSelect}
                accept=".csv"
                className="hidden"
              />
              <Button
                variant="outline"
                onClick={() => examplePromptsInputRef.current?.click()}
                disabled={importExamplesMutation.isPending}
                className="border-violet-300 hover:bg-violet-100 dark:border-violet-700 dark:hover:bg-violet-900/30"
              >
                {importExamplesMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4 mr-2" />
                )}
                Import Examples
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader>
          <CardTitle>Analysis Workflow</CardTitle>
          <CardDescription>
            Follow these steps to complete your content gap analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Step 1: Import */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-slate-200 dark:border-slate-800">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                activeImport
                  ? "bg-cyan-500 text-white"
                  : importComplete
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 dark:bg-slate-700 text-slate-500"
              )}>
                {activeImport ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : importComplete ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : "1"}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-slate-900 dark:text-white">Import Prompts</h4>
                <p className="text-sm text-slate-500 mt-1">
                  {activeImport 
                    ? `Processing ${activeImport.filename}... ${activeImport.processed_rows || 0}/${activeImport.total_rows || '?'} rows`
                    : importComplete
                    ? `${stats?.total_prompts?.toLocaleString()} prompts imported`
                    : 'Upload your CSV file containing prompts and metadata'
                  }
                </p>
                {activeImport && (
                  <div className="mt-2">
                    <Progress 
                      value={activeImport.total_rows ? (activeImport.processed_rows / activeImport.total_rows) * 100 : 0} 
                      className="h-1" 
                    />
                  </div>
                )}
              </div>
              <Button 
                asChild 
                variant={importComplete ? "outline" : "default"}
                disabled={!!activeImport}
              >
                <Link to={`/projects/${project.id}/import`}>
                  {activeImport ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Upload className="w-4 h-4 mr-2" />
                  )}
                  {activeImport ? 'Processing...' : importComplete ? 'Import More' : 'Import CSV'}
                </Link>
              </Button>
            </div>

            {/* Step 2: Crawl */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-slate-200 dark:border-slate-800">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                activeCrawl
                  ? "bg-cyan-500 text-white"
                  : crawlComplete
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 dark:bg-slate-700 text-slate-500"
              )}>
                {activeCrawl ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : crawlComplete ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : "2"}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-slate-900 dark:text-white">Crawl Target Domains</h4>
                <p className="text-sm text-slate-500 mt-1">
                  {activeCrawl 
                    ? `Crawling in progress... ${activeCrawl.crawled_urls || 0}/${activeCrawl.total_urls || '?'} pages`
                    : crawlComplete
                    ? `${stats?.total_pages?.toLocaleString()} pages crawled`
                    : 'Crawl your website(s) or import specific URLs'
                  }
                </p>
                {project.target_domains?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {project.target_domains.map((domain, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">{domain}</Badge>
                    ))}
                  </div>
                )}
                {activeCrawl && (
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center gap-2">
                      <Progress value={activeCrawl.total_urls ? (activeCrawl.crawled_urls / activeCrawl.total_urls) * 100 : 0} className="h-1 flex-1" />
                      <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-red-500 hover:bg-red-50" onClick={() => cancelCrawlMutation.mutate(activeCrawl.id)} disabled={cancelCrawlMutation.isPending}>
                        {cancelCrawlMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Stop'}
                      </Button>
                    </div>
                    <p className="text-xs text-slate-400">{activeCrawl.failed_urls > 0 ? `${activeCrawl.failed_urls} failed • ` : ''}Click Stop to finish early</p>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Dialog open={showUrlImport} onOpenChange={setShowUrlImport}>
                  <DialogTrigger asChild>
                    <Button 
                      variant="outline"
                      disabled={activeCrawl}
                    >
                      <LinkIcon className="w-4 h-4 mr-2" />
                      Import URLs
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>Import URL List</DialogTitle>
                      <DialogDescription>
                        Paste a list of URLs to crawl (one per line). This is faster than full site crawling.
                      </DialogDescription>
                    </DialogHeader>
                    <textarea
                      className="w-full h-64 p-3 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:bg-slate-900 dark:border-slate-700"
                      placeholder={"https://example.com/page1\nhttps://example.com/page2\nhttps://example.com/page3\n# Lines starting with # are ignored"}
                      value={urlsText}
                      onChange={(e) => setUrlsText(e.target.value)}
                    />
                    <div className="text-sm text-slate-500">
                      {urlsText.split('\n').filter(u => u.trim() && !u.trim().startsWith('#')).length} URLs detected
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setShowUrlImport(false)}>
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleUrlImport}
                        disabled={importUrlsMutation.isPending}
                      >
                        {importUrlsMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Globe className="w-4 h-4 mr-2" />
                        )}
                        Start Crawling
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
                {/* Hidden file input for CSV crawl */}
                <input
                  type="file"
                  ref={csvCrawlInputRef}
                  onChange={handleCsvCrawlSelect}
                  accept=".csv"
                  className="hidden"
                />
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      variant="outline"
                      disabled={csvCrawlMutation.isPending || activeCrawl}
                      title="Upload Ahrefs/SEMrush CSV with URLs and keyword data"
                    >
                      {csvCrawlMutation.isPending ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Upload className="w-4 h-4 mr-2" />
                      )}
                      Crawl from CSV
                      <ChevronDown className="w-4 h-4 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => { setCsvCrawlLimit(100); setTimeout(() => csvCrawlInputRef.current?.click(), 0); }}>
                      Top 100 pages by traffic
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setCsvCrawlLimit(200); setTimeout(() => csvCrawlInputRef.current?.click(), 0); }}>
                      Top 200 pages by traffic
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setCsvCrawlLimit(300); setTimeout(() => csvCrawlInputRef.current?.click(), 0); }}>
                      Top 300 pages by traffic
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setCsvCrawlLimit(500); setTimeout(() => csvCrawlInputRef.current?.click(), 0); }}>
                      Top 500 pages by traffic
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setCsvCrawlLimit(undefined); setTimeout(() => csvCrawlInputRef.current?.click(), 0); }}>
                      All pages (no limit)
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button 
                  variant={crawlComplete ? "outline" : "default"}
                  onClick={() => crawlMutation.mutate()}
                  disabled={crawlMutation.isPending || activeCrawl || project.target_domains?.length === 0}
                >
                  {crawlMutation.isPending || activeCrawl ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Globe className="w-4 h-4 mr-2" />
                  )}
                  {activeCrawl ? 'Crawling...' : crawlComplete ? 'Re-crawl' : 'Crawl Site'}
                </Button>
              </div>
            </div>

            {/* Step 3: Match */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-slate-200 dark:border-slate-800">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                matchTaskId || matchMutation.isPending
                  ? "bg-cyan-500 text-white"
                  : matchComplete
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 dark:bg-slate-700 text-slate-500"
              )}>
                {matchTaskId || matchMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : matchComplete ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : "3"}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-slate-900 dark:text-white">Match & Analyze</h4>
                <p className="text-sm text-slate-500 mt-1">
                  {matchTaskId || matchMutation.isPending
                    ? matchProgress 
                      ? `Comparing prompts to ${stats?.total_pages || 0} pages... ${matchProgress.processed}/${matchProgress.total} prompts analyzed`
                      : 'Starting analysis...'
                    : matchComplete
                    ? `${stats?.by_match_status?.answered || 0} prompts answered, ${stats?.by_match_status?.partial || 0} partial matches, ${opportunitiesCount} opportunities`
                    : 'Compare prompts to crawled pages and identify content gaps'
                  }
                </p>
                {(matchTaskId || matchMutation.isPending) && matchProgress && (
                  <div className="mt-2 space-y-1">
                    <Progress 
                      value={matchProgress.total > 0 ? (matchProgress.processed / matchProgress.total) * 100 : 0} 
                      className="h-2" 
                    />
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{matchProgress.matched} matched</span>
                      <span>{matchProgress.opportunities} opportunities found</span>
                    </div>
                  </div>
                )}
                {matchComplete && !matchTaskId && (
                  <div className="flex gap-4 mt-2 text-xs">
                    <span className="text-emerald-600">✓ {stats?.by_match_status?.answered || 0} answered</span>
                    <span className="text-amber-600">◐ {stats?.by_match_status?.partial || 0} partial</span>
                    <span className="text-red-600">○ {stats?.by_match_status?.gap || 0} gaps</span>
                  </div>
                )}
              </div>
              <Button 
                variant={matchComplete ? "outline" : "default"}
                onClick={() => matchMutation.mutate()}
                disabled={matchMutation.isPending || !!matchTaskId || (stats?.total_prompts || 0) === 0 || (stats?.total_pages || 0) === 0}
              >
                {matchMutation.isPending || matchTaskId ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                {matchMutation.isPending || matchTaskId ? 'Matching...' : matchComplete ? 'Re-match' : 'Run Matching'}
              </Button>
            </div>

            {/* Step 4: Review */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-slate-200 dark:border-slate-800">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                opportunitiesCount > 0
                  ? "bg-emerald-500 text-white"
                  : "bg-slate-200 dark:bg-slate-700 text-slate-500"
              )}>
                {opportunitiesCount > 0 ? <CheckCircle2 className="w-5 h-5" /> : "4"}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-slate-900 dark:text-white">Review Opportunities</h4>
                <p className="text-sm text-slate-500 mt-1">
                  {opportunitiesCount > 0
                    ? `${opportunitiesCount} opportunities ready for review`
                    : 'Explore prioritized content opportunities'
                  }
                </p>
              </div>
              <Button 
                asChild 
                variant={opportunitiesCount > 0 ? "default" : "outline"}
                disabled={opportunitiesCount === 0}
              >
                <Link to={`/opportunities?project_id=${project.id}`}>
                  <Lightbulb className="w-4 h-4 mr-2" />
                  {opportunitiesCount > 0 ? `View ${opportunitiesCount} Opportunities` : 'View Opportunities'}
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ImportsTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['csv-imports', projectId],
    queryFn: () => csvApi.list(projectId),
    // Poll every 3 seconds if any import is processing
    refetchInterval: (query) => {
      const imports = query.state.data?.data?.imports || []
      const hasProcessing = imports.some((imp: CSVImport) => imp.status === 'processing')
      return hasProcessing ? 3000 : false
    },
  })

  const imports = data?.data?.imports || []

  if (isLoading) {
    return <div className="animate-pulse space-y-4">
      {[...Array(2)].map((_, i) => (
        <div key={i} className="h-20 bg-slate-200 dark:bg-slate-800 rounded-lg" />
      ))}
    </div>
  }

  if (imports.length === 0) {
    return (
      <Card className="border-dashed border-2">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Upload className="w-12 h-12 text-slate-400 mb-4" />
          <p className="text-slate-500">No imports yet</p>
          <Button asChild className="mt-4">
            <Link to={`/projects/${projectId}/import`}>Import CSV</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {imports.map((imp: CSVImport) => (
        <Card key={imp.id} className="border-slate-200 dark:border-slate-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center",
                  imp.status === 'completed' ? "bg-emerald-100 dark:bg-emerald-900/30" :
                  imp.status === 'failed' ? "bg-red-100 dark:bg-red-900/30" :
                  "bg-slate-100 dark:bg-slate-800"
                )}>
                  {imp.status === 'processing' ? (
                    <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
                  ) : imp.status === 'completed' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : imp.status === 'failed' ? (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                  ) : (
                    <Upload className="w-5 h-5 text-slate-500" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-slate-900 dark:text-white">{imp.filename}</p>
                  <p className="text-xs text-slate-500">
                    {imp.status === 'completed' && imp.processed_rows 
                      ? `${imp.processed_rows.toLocaleString()} prompts imported`
                      : imp.status === 'processing'
                      ? `Processing... ${imp.processed_rows || 0} / ${imp.total_rows || '?'} rows`
                      : imp.status === 'failed'
                      ? imp.error_message || 'Processing failed'
                      : `${imp.total_rows?.toLocaleString() || '?'} rows`
                    } • {format(new Date(imp.created_at), 'MMM d, yyyy h:mm a')}
                  </p>
                </div>
              </div>
              <Badge variant={
                imp.status === 'completed' ? 'default' :
                imp.status === 'failed' ? 'destructive' : 'secondary'
              }>
                {imp.status}
              </Badge>
            </div>
            {imp.status === 'processing' && (
              <div className="mt-3">
                <Progress 
                  value={imp.total_rows ? (imp.processed_rows / imp.total_rows) * 100 : 0} 
                  className="h-1"
                />
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function SettingsTab({ project }: { project: Project }) {
  return (
    <Card className="border-slate-200 dark:border-slate-800">
      <CardHeader>
        <CardTitle>Project Settings</CardTitle>
        <CardDescription>Configure your project settings</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Project Name</label>
          <p className="text-slate-700 dark:text-slate-300">{project.name}</p>
        </div>
        <div>
          <label className="text-sm font-medium">Description</label>
          <p className="text-slate-700 dark:text-slate-300">{project.description || 'No description'}</p>
        </div>
        <div>
          <label className="text-sm font-medium">Target Domains</label>
          <div className="flex flex-wrap gap-2 mt-1">
            {project.target_domains?.map((domain, i) => (
              <Badge key={i} variant="secondary">{domain}</Badge>
            ))}
          </div>
        </div>
        <div>
          <label className="text-sm font-medium">Created</label>
          <p className="text-slate-700 dark:text-slate-300">
            {format(new Date(project.created_at), 'MMMM d, yyyy h:mm a')}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const { setSelectedProjectId } = useProjectStore()

  const { data: projectData, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  })

  const { data: statsData } = useQuery({
    queryKey: ['project-stats', projectId],
    queryFn: () => projectsApi.getStats(projectId!),
    enabled: !!projectId,
    refetchInterval: 5000, // Poll every 5 seconds to update stats during processing
  })

  // Set as selected project when viewing
  useEffect(() => {
    if (projectId) {
      setSelectedProjectId(projectId)
    }
  }, [projectId, setSelectedProjectId])

  const project = projectData?.data
  const stats = statsData?.data as ProjectStats | undefined

  if (projectLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 w-48 bg-slate-200 dark:bg-slate-800 rounded-lg" />
        <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-lg" />
      </div>
    )
  }

  if (!project) {
    return (
      <Card className="border-slate-200 dark:border-slate-800">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-slate-400 mb-4" />
          <p className="text-slate-500">Project not found</p>
          <Button asChild className="mt-4">
            <Link to="/projects">Back to Projects</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg">
            <MessageSquareText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">{project.name}</h2>
            {project.description && (
              <p className="text-slate-500 dark:text-slate-400">{project.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="imports">Imports</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <OverviewTab project={project} stats={stats} />
        </TabsContent>
        <TabsContent value="imports">
          <ImportsTab projectId={project.id} />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsTab project={project} />
        </TabsContent>
      </Tabs>
    </div>
  )
}


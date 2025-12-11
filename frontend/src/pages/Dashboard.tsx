import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { 
  MessageSquareText, 
  Globe, 
  Lightbulb, 
  TrendingUp,
  ArrowRight,
  FolderKanban,
  Target,
  Sparkles,
  AlertCircle,
} from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { projectsApi, ProjectStats } from '@/services/api'
import { useProjectStore } from '@/stores/projectStore'
import { cn } from '@/lib/utils'

function StatCard({ 
  title, 
  value, 
  description, 
  icon: Icon, 
  trend,
  color = 'cyan',
  href 
}: { 
  title: string
  value: string | number
  description?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: { value: number; label: string }
  color?: 'cyan' | 'emerald' | 'violet' | 'amber'
  href?: string
}) {
  const colorMap = {
    cyan: 'from-cyan-500 to-blue-500 shadow-cyan-500/30',
    emerald: 'from-emerald-500 to-teal-500 shadow-emerald-500/30',
    violet: 'from-violet-500 to-purple-500 shadow-violet-500/30',
    amber: 'from-amber-500 to-orange-500 shadow-amber-500/30',
  }

  const content = (
    <Card className="group relative overflow-hidden border-slate-200 dark:border-slate-800 hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 to-white dark:from-slate-900 dark:to-slate-800" />
      <CardContent className="relative p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            {description && (
              <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
            )}
            {trend && (
              <div className="flex items-center gap-1">
                <TrendingUp className={cn(
                  "w-3 h-3",
                  trend.value >= 0 ? "text-emerald-500" : "text-red-500"
                )} />
                <span className={cn(
                  "text-xs font-medium",
                  trend.value >= 0 ? "text-emerald-500" : "text-red-500"
                )}>
                  {trend.value > 0 ? '+' : ''}{trend.value}%
                </span>
                <span className="text-xs text-slate-400">{trend.label}</span>
              </div>
            )}
          </div>
          <div className={cn(
            "w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center shadow-lg",
            colorMap[color]
          )}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
        {href && (
          <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <ArrowRight className="w-4 h-4 text-slate-400" />
          </div>
        )}
      </CardContent>
    </Card>
  )

  if (href) {
    return <Link to={href}>{content}</Link>
  }

  return content
}

// Map raw intent values to clean display labels (comprehensive taxonomy)
const intentLabelMap: Record<string, string> = {
  // Lowercase (from backend)
  'transactional': 'Transactional',
  'navigational': 'Navigational',
  'informational': 'Informational',
  'commercial': 'Commercial',
  'exploratory': 'Exploratory',
  'comparison': 'Comparison',
  'troubleshooting': 'Troubleshooting',
  'opinion_seeking': 'Opinion Seeking',
  'emotional': 'Emotional',
  'procedural': 'Procedural',
  'regulatory': 'Regulatory',
  'brand_monitoring': 'Brand Monitoring',
  'meta': 'Meta',
  'unknown': 'Unknown',
  // Uppercase variants
  'TRANSACTIONAL': 'Transactional',
  'NAVIGATIONAL': 'Navigational',
  'INFORMATIONAL': 'Informational',
  'COMMERCIAL': 'Commercial',
  'EXPLORATORY': 'Exploratory',
  'COMPARISON': 'Comparison',
  'TROUBLESHOOTING': 'Troubleshooting',
  'OPINION_SEEKING': 'Opinion Seeking',
  'EMOTIONAL': 'Emotional',
  'PROCEDURAL': 'Procedural',
  'REGULATORY': 'Regulatory',
  'BRAND_MONITORING': 'Brand Monitoring',
  'META': 'Meta',
  'UNKNOWN': 'Unknown',
}

// Hex colors for pie chart (matching the intent taxonomy)
const intentHexColors: Record<string, string> = {
  'Transactional': '#10b981',      // emerald-500
  'Commercial': '#f59e0b',          // amber-500
  'Comparison': '#f97316',          // orange-500
  'Informational': '#3b82f6',       // blue-500
  'Navigational': '#8b5cf6',        // violet-500
  'Exploratory': '#06b6d4',         // cyan-500
  'Procedural': '#6366f1',          // indigo-500
  'Troubleshooting': '#ef4444',     // red-500
  'Opinion Seeking': '#ec4899',     // pink-500
  'Emotional': '#f43f5e',           // rose-500
  'Regulatory': '#64748b',          // slate-500
  'Brand Monitoring': '#a855f7',    // purple-500
  'Meta': '#14b8a6',                // teal-500
  'Unknown': '#9ca3af',             // gray-400
}

function IntentChart({ data }: { data: Record<string, number> }) {
  // Clean up the intent labels and merge duplicates
  const cleanedData: Record<string, number> = {}
  Object.entries(data).forEach(([intent, count]) => {
    const cleanLabel = intentLabelMap[intent] || intent.replace('IntentLabel.', '').toLowerCase()
    const displayLabel = cleanLabel.charAt(0).toUpperCase() + cleanLabel.slice(1).toLowerCase()
    cleanedData[displayLabel] = (cleanedData[displayLabel] || 0) + count
  })
  
  const total = Object.values(cleanedData).reduce((a, b) => a + b, 0)
  
  // Convert to recharts format and sort by count descending
  const chartData = Object.entries(cleanedData)
    .map(([name, value]) => ({
      name,
      value,
      percentage: total > 0 ? ((value / total) * 100).toFixed(1) : '0',
      color: intentHexColors[name] || '#9ca3af'
    }))
    .sort((a, b) => b.value - a.value)

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; value: number; percentage: string } }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white dark:bg-slate-800 px-3 py-2 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700">
          <p className="font-medium text-slate-900 dark:text-white">{data.name}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {data.value} prompts ({data.percentage}%)
          </p>
        </div>
      )
    }
    return null
  }

  // Custom legend
  const CustomLegend = ({ payload }: { payload?: Array<{ value: string; color: string }> }) => {
    if (!payload) return null
    return (
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-4">
        {payload.map((entry, index) => {
          const item = chartData.find(d => d.name === entry.value)
          return (
            <div key={index} className="flex items-center gap-2 text-xs">
              <div 
                className="w-3 h-3 rounded-full flex-shrink-0" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-slate-600 dark:text-slate-400 truncate">
                {entry.value}
              </span>
              <span className="text-slate-400 dark:text-slate-500 ml-auto">
                {item?.value}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400">
        No data available
      </div>
    )
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="40%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// Hex colors for match status chart
const matchStatusHexColors: Record<string, string> = {
  'Answered': '#10b981',      // emerald-500
  'Partial Match': '#f59e0b', // amber-500
  'Content Gap': '#ef4444',   // red-500
  'Pending': '#94a3b8',       // slate-400
}

const matchStatusLabels: Record<string, string> = {
  'answered': 'Answered',
  'partial': 'Partial Match',
  'gap': 'Content Gap',
  'pending': 'Pending',
}

function MatchStatusChart({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0)
  
  // Convert to recharts format
  const chartData = Object.entries(data)
    .filter(([_, value]) => value > 0) // Only show non-zero values
    .map(([status, value]) => {
      const label = matchStatusLabels[status] || status
      return {
        name: label,
        value,
        percentage: total > 0 ? ((value / total) * 100).toFixed(1) : '0',
        color: matchStatusHexColors[label] || '#94a3b8'
      }
    })
    .sort((a, b) => b.value - a.value)

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; value: number; percentage: string } }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white dark:bg-slate-800 px-3 py-2 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700">
          <p className="font-medium text-slate-900 dark:text-white">{data.name}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {data.value} prompts ({data.percentage}%)
          </p>
        </div>
      )
    }
    return null
  }

  // Custom legend
  const CustomLegend = ({ payload }: { payload?: Array<{ value: string; color: string }> }) => {
    if (!payload) return null
    return (
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-4">
        {payload.map((entry, index) => {
          const item = chartData.find(d => d.name === entry.value)
          return (
            <div key={index} className="flex items-center gap-2 text-xs">
              <div 
                className="w-3 h-3 rounded-full flex-shrink-0" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-slate-600 dark:text-slate-400 truncate">
                {entry.value}
              </span>
              <span className="text-slate-400 dark:text-slate-500 ml-auto">
                {item?.value}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400">
        No data available
      </div>
    )
  }

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="40%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Dashboard() {
  const { selectedProjectId } = useProjectStore()
  
  // Debug: Log selected project
  console.log('Dashboard - selectedProjectId:', selectedProjectId)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['project-stats', selectedProjectId],
    queryFn: async () => {
      if (!selectedProjectId) return null
      const response = await projectsApi.getStats(selectedProjectId)
      return response.data as ProjectStats
    },
    enabled: !!selectedProjectId,
    refetchOnMount: true,
    staleTime: 0, // Always refetch when component mounts
  })

  if (!selectedProjectId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-2xl shadow-cyan-500/30">
          <FolderKanban className="w-10 h-10 text-white" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            Welcome to LLMO Prompt Analyzer
          </h2>
          <p className="text-slate-500 dark:text-slate-400 max-w-md">
            Select or create a project to start analyzing content gaps and opportunities.
          </p>
        </div>
        <Button asChild size="lg" className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600">
          <Link to="/projects">
            <FolderKanban className="w-4 h-4 mr-2" />
            Go to Projects
          </Link>
        </Button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-20 bg-slate-200 dark:bg-slate-800 rounded-lg" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Prompts"
          value={stats?.total_prompts || 0}
          description="Imported from CSV"
          icon={MessageSquareText}
          color="cyan"
          href="/prompts"
        />
        <StatCard
          title="Crawled Pages"
          value={stats?.total_pages || 0}
          description="From target domains"
          icon={Globe}
          color="emerald"
          href="/pages"
        />
        <StatCard
          title="Content Gaps"
          value={Object.values(stats?.opportunities_by_status || {}).reduce((a, b) => a + b, 0)}
          description="Opportunities identified"
          icon={Lightbulb}
          color="violet"
          href="/opportunities"
        />
        <StatCard
          title="High Priority"
          value={stats?.high_priority_count || stats?.opportunities_by_status?.new || 0}
          description="Requiring attention"
          icon={Target}
          color="amber"
          href="/opportunities"
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Intent Distribution */}
        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              Intent Distribution
            </CardTitle>
            <CardDescription>
              Classification of prompts by search intent
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.by_intent && Object.keys(stats.by_intent).length > 0 ? (
              <IntentChart data={stats.by_intent} />
            ) : (
              <p className="text-sm text-slate-500 text-center py-8">
                No intent data available yet
              </p>
            )}
          </CardContent>
        </Card>

        {/* Match Status */}
        <Card className="border-slate-200 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                <Target className="w-4 h-4 text-white" />
              </div>
              Content Coverage
            </CardTitle>
            <CardDescription>
              How well your content matches user prompts
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats?.by_match_status && Object.keys(stats.by_match_status).length > 0 ? (
              <MatchStatusChart data={stats.by_match_status} />
            ) : (
              <p className="text-sm text-slate-500 text-center py-8">
                Run matching to see coverage data
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
          <CardDescription>
            Common tasks to manage your content gap analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Button variant="outline" asChild className="justify-start h-auto py-4">
              <Link to={`/projects/${selectedProjectId}/import`}>
                <div className="flex flex-col items-start gap-1">
                  <span className="font-medium">Import Prompts</span>
                  <span className="text-xs text-slate-500">Upload CSV data</span>
                </div>
              </Link>
            </Button>
            <Button variant="outline" asChild className="justify-start h-auto py-4">
              <Link to={`/projects/${selectedProjectId}`}>
                <div className="flex flex-col items-start gap-1">
                  <span className="font-medium">Start Crawl</span>
                  <span className="text-xs text-slate-500">Scan target domains</span>
                </div>
              </Link>
            </Button>
            <Button variant="outline" asChild className="justify-start h-auto py-4">
              <Link to="/opportunities">
                <div className="flex flex-col items-start gap-1">
                  <span className="font-medium">View Opportunities</span>
                  <span className="text-xs text-slate-500">Prioritized content gaps</span>
                </div>
              </Link>
            </Button>
            <Button variant="outline" asChild className="justify-start h-auto py-4">
              <Link to="/prompts?match_status=gap">
                <div className="flex flex-col items-start gap-1">
                  <span className="font-medium">Content Gaps</span>
                  <span className="text-xs text-slate-500">Unmatched prompts</span>
                </div>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


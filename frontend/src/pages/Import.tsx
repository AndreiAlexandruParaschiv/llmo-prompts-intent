import { useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { 
  Upload, 
  FileSpreadsheet, 
  Check, 
  X, 
  ChevronRight,
  AlertCircle,
  Loader2,
  ArrowLeft,
  HelpCircle,
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
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { csvApi, projectsApi } from '@/services/api'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

interface ColumnMapping {
  prompt: string | null
  topic: string | null
  region: string | null
  popularity: string | null
  sentiment: string | null
  visibility_score: string | null
  sources_urls: string | null
  source_types: string | null
}

const MAPPING_FIELDS = [
  { key: 'prompt', label: 'Prompt Text', required: true, description: 'The main query/prompt text' },
  { key: 'topic', label: 'Topic', required: false, description: 'Category or topic of the prompt' },
  { key: 'region', label: 'Region', required: false, description: 'Geographic region (e.g., US, EU, APAC)' },
  { key: 'popularity', label: 'Popularity', required: false, description: 'Search volume or popularity (Low/Medium/High)' },
  { key: 'sentiment', label: 'Sentiment', required: false, description: 'Sentiment (Positive/Neutral/Negative)' },
  { key: 'visibility_score', label: 'Visibility Score', required: false, description: 'Brand visibility percentage' },
  { key: 'sources_urls', label: 'Source URLs', required: false, description: 'URLs of sources (semicolon-separated)' },
  { key: 'source_types', label: 'Source Types', required: false, description: 'Content types (semicolon-separated)' },
]

function UploadStep({ 
  onUpload, 
  isUploading 
}: { 
  onUpload: (file: File) => void
  isUploading: boolean 
}) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0])
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: isUploading,
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all",
        isDragActive 
          ? "border-cyan-500 bg-cyan-50 dark:bg-cyan-950/20" 
          : "border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500",
        isUploading && "opacity-50 cursor-not-allowed"
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-4">
        <div className={cn(
          "w-16 h-16 rounded-2xl flex items-center justify-center transition-colors",
          isDragActive 
            ? "bg-cyan-100 dark:bg-cyan-900" 
            : "bg-slate-100 dark:bg-slate-800"
        )}>
          {isUploading ? (
            <Loader2 className="w-8 h-8 text-cyan-500 animate-spin" />
          ) : (
            <Upload className={cn(
              "w-8 h-8",
              isDragActive ? "text-cyan-500" : "text-slate-400"
            )} />
          )}
        </div>
        <div>
          <p className="text-lg font-medium text-slate-900 dark:text-white">
            {isDragActive ? 'Drop your CSV here' : 'Drag & drop your CSV file'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            or click to browse files
          </p>
        </div>
        <Badge variant="secondary" className="text-xs">
          Supported: .csv files up to 50MB
        </Badge>
      </div>
    </div>
  )
}

function MappingStep({
  columns,
  suggestedMapping,
  onProcess,
  isProcessing,
}: {
  columns: string[]
  suggestedMapping: ColumnMapping
  onProcess: (mapping: ColumnMapping) => void
  isProcessing: boolean
}) {
  const [mapping, setMapping] = useState<ColumnMapping>(suggestedMapping)

  const updateMapping = (field: string, value: string | null) => {
    setMapping(prev => ({ ...prev, [field]: value }))
  }

  const isValid = mapping.prompt !== null

  return (
    <div className="space-y-6">
      {/* Column Mapping */}
      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg">Map Columns</CardTitle>
          <CardDescription>
            Match your CSV columns to the expected fields
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {MAPPING_FIELDS.map((field) => (
              <div key={field.key} className="flex items-center gap-4">
                <div className="w-40 flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {field.label}
                  </span>
                  {field.required && (
                    <span className="text-red-500">*</span>
                  )}
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="text-xs">{field.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
                <Select
                  value={mapping[field.key as keyof ColumnMapping] || 'none'}
                  onValueChange={(value) => updateMapping(field.key, value === 'none' ? null : value)}
                >
                  <SelectTrigger className="w-64">
                    <SelectValue placeholder="Select column..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">-- Not mapped --</SelectItem>
                    {columns.map((col) => (
                      <SelectItem key={col} value={col}>{col}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {mapping[field.key as keyof ColumnMapping] && (
                  <Check className="w-4 h-4 text-emerald-500" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Action */}
      <div className="flex justify-end gap-4">
        <Button
          onClick={() => onProcess(mapping)}
          disabled={!isValid || isProcessing}
          className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Process CSV
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

export default function Import() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const [step, setStep] = useState<'upload' | 'mapping' | 'processing'>('upload')
  const [uploadData, setUploadData] = useState<{
    importId: string
    columns: string[]
    totalRows: number
    suggestedMapping: ColumnMapping
  } | null>(null)

  // Get project details
  const { data: projectData } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => csvApi.upload(projectId!, file),
    onSuccess: (response) => {
      const data = response.data
      setUploadData({
        importId: data.import_id,
        columns: data.columns,
        totalRows: data.total_rows,
        suggestedMapping: data.suggested_mapping || {
          prompt: null,
          topic: null,
          region: null,
          popularity: null,
          sentiment: null,
          visibility_score: null,
          sources_urls: null,
          source_types: null,
        },
      })
      setStep('mapping')
      toast({ title: 'File uploaded successfully' })
    },
    onError: (error: Error) => {
      toast({ 
        title: 'Upload failed', 
        description: error.message, 
        variant: 'destructive' 
      })
    },
  })

  // Process mutation
  const processMutation = useMutation({
    mutationFn: (mapping: ColumnMapping) => 
      csvApi.process(uploadData!.importId, mapping as unknown as Record<string, string>),
    onSuccess: () => {
      toast({ 
        title: 'Processing started', 
        description: 'Your prompts are being processed in the background.' 
      })
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['csv-imports', projectId] })
      navigate(`/projects/${projectId}`)
    },
    onError: (error: Error) => {
      toast({ 
        title: 'Processing failed', 
        description: error.message, 
        variant: 'destructive' 
      })
    },
  })

  const project = projectData?.data

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/projects/${projectId}`}>
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </Button>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Import Prompts</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Upload CSV data for {project?.name || 'project'}
          </p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-4">
        {['Upload', 'Map Columns', 'Process'].map((label, i) => {
          const stepIndex = ['upload', 'mapping', 'processing'].indexOf(step)
          const isCompleted = i < stepIndex
          const isCurrent = i === stepIndex

          return (
            <div key={label} className="flex items-center gap-3">
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                isCompleted && "bg-emerald-500 text-white",
                isCurrent && "bg-cyan-500 text-white",
                !isCompleted && !isCurrent && "bg-slate-200 dark:bg-slate-700 text-slate-500"
              )}>
                {isCompleted ? <Check className="w-4 h-4" /> : i + 1}
              </div>
              <span className={cn(
                "text-sm font-medium",
                isCurrent ? "text-slate-900 dark:text-white" : "text-slate-500"
              )}>
                {label}
              </span>
              {i < 2 && (
                <div className={cn(
                  "w-12 h-0.5",
                  i < stepIndex ? "bg-emerald-500" : "bg-slate-200 dark:bg-slate-700"
                )} />
              )}
            </div>
          )
        })}
      </div>

      {/* Content */}
      {step === 'upload' && (
        <UploadStep 
          onUpload={(file) => uploadMutation.mutate(file)}
          isUploading={uploadMutation.isPending}
        />
      )}

      {step === 'mapping' && uploadData && (
        <MappingStep
          columns={uploadData.columns}
          suggestedMapping={uploadData.suggestedMapping}
          onProcess={(mapping) => processMutation.mutate(mapping)}
          isProcessing={processMutation.isPending}
        />
      )}
    </div>
  )
}


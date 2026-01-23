import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Project {
  id: string
  name: string
  description: string | null
  target_domains: string[]
  crawl_config: Record<string, unknown>
  created_at: string
  updated_at: string
  prompt_count: number
  page_count: number
  opportunity_count: number
}

export interface CSVImport {
  id: string
  project_id: string
  filename: string
  status: string
  total_rows: number | null
  processed_rows: number
  failed_rows: number
  error_message: string | null
  column_mapping: Record<string, string>
  job_id: string | null
  created_at: string
}

export interface Prompt {
  id: string
  raw_text: string
  normalized_text: string | null
  topic: string | null
  category: string | null
  region: string | null
  language: string | null
  popularity_score: number | null
  sentiment_score: number | null
  visibility_score: number | null
  intent_label: string
  transaction_score: number
  match_status: string
  best_match_score: number | null
  extra_data: Record<string, unknown>
  created_at: string
  matches?: PromptMatch[]
  opportunity?: Record<string, unknown>
  cwv_assessment?: CWVAssessment
}

export interface PromptMatch {
  page_id: string
  page_url: string
  page_title: string | null
  similarity_score: number
  match_type: string
  matched_snippet: string | null
}

export interface Page {
  id: string
  project_id: string
  url: string
  canonical_url: string | null
  status_code: string | null
  title: string | null
  meta_description: string | null
  word_count: string | null
  structured_data: unknown[]
  mcp_checks: Record<string, unknown>
  hreflang_tags: Array<{ lang: string; url: string }>
  crawled_at: string | null
  created_at: string
}

export interface ContentSuggestion {
  title?: string
  content_type?: string
  outline?: string[]
  cta_suggestion?: string
  seo_keywords?: string[]
  priority_reason?: string
}

export interface Opportunity {
  id: string
  prompt_id: string
  priority_score: number
  difficulty_score: number | null
  difficulty_factors: Record<string, unknown>
  recommended_action: string
  reason: string | null
  status: string
  assigned_to: string | null
  notes: string | null
  content_suggestion: ContentSuggestion
  related_page_ids: string[]
  created_at: string
  prompt_text?: string
  prompt_topic?: string
  prompt_intent?: string
  prompt_transaction_score?: number
  prompt_popularity_score?: number
  prompt_sentiment_score?: number
}

export interface ProjectStats {
  total_prompts: number
  total_pages: number
  by_intent: Record<string, number>
  by_match_status: Record<string, number>
  by_language: Record<string, number>
  opportunities_by_status: Record<string, number>
  opportunities_by_action: Record<string, number>
}

// Projects
export const projectsApi = {
  list: () => api.get<{ projects: Project[]; total: number }>('/projects/'),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  create: (data: { name: string; description?: string; target_domains?: string[] }) =>
    api.post<Project>('/projects/', data),
  update: (id: string, data: Partial<Project>) => api.patch<Project>(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
  getStats: (id: string) => api.get<ProjectStats>(`/projects/${id}/stats`),
  startCrawl: (id: string, startUrls?: string[]) =>
    api.post(`/projects/${id}/crawl`, { start_urls: startUrls }),
  crawlFromCsv: (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{
      crawl_job_id: string
      task_id: string
      status: string
      urls_to_crawl: number
      urls_with_seo_data: number
    }>(`/projects/${id}/crawl-from-csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importExamplePrompts: (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{
      status: string
      prompts_imported: number
      prompts_skipped: number
      total_examples: number
      branded_count: number
      generic_count: number
      message: string
    }>(`/projects/${id}/import-example-prompts`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getExamplePrompts: (id: string) =>
    api.get<{
      prompts: Array<{
        prompt: string
        topic: string
        category: string
        origin: string
      }>
      total: number
      branded_count: number
      generic_count: number
      topics: string[]
    }>(`/projects/${id}/example-prompts`),
  runMatching: (id: string) => api.post(`/projects/${id}/match`),
}

// CSV Imports
export const csvApi = {
  upload: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/csv/upload/${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  process: (importId: string, columnMapping: Record<string, string>) =>
    api.post(`/csv/${importId}/process`, { column_mapping: columnMapping }),
  get: (importId: string) => api.get<CSVImport>(`/csv/${importId}`),
  list: (projectId?: string) =>
    api.get<{ imports: CSVImport[] }>('/csv/', { params: { project_id: projectId } }),
}

// Intent explanation response type
export interface IntentExplanation {
  prompt_text: string
  intent: string
  transaction_score: number
  confidence: number
  signals: string[]
  explanation: string
}

// Prompts
export const promptsApi = {
  list: (params: {
    project_id?: string
    topic?: string
    language?: string
    intent_label?: string
    match_status?: string
    min_transaction_score?: number
    search?: string
    page?: number
    page_size?: number
  }) => api.get<{ prompts: Prompt[]; total: number; page: number; pages: number }>('/prompts/', { params }),
  get: (id: string) => api.get<Prompt>(`/prompts/${id}`),
  getTopics: (projectId?: string) =>
    api.get<{ topics: Record<string, number> }>('/prompts/topics/list', {
      params: { project_id: projectId },
    }),
  getLanguages: (projectId?: string) =>
    api.get<{ languages: Record<string, number> }>('/prompts/languages/list', {
      params: { project_id: projectId },
    }),
  explainIntent: (id: string) => api.get<IntentExplanation>(`/prompts/${id}/explain-intent`),
  reclassify: (id: string) => api.post(`/prompts/${id}/reclassify/`),
  reclassifyWithAI: (projectId: string) => 
    api.post(`/prompts/reclassify-with-ai/`, null, { params: { project_id: projectId } }),
}

// Orphan page types
export interface OrphanPageSuggestion {
  suggested_prompts: string[]
  primary_intent: string
  target_audience: string
  content_summary: string
  top_keywords: string[]
}

export interface OrphanPage {
  id: string
  url: string
  title: string | null
  meta_description: string | null
  word_count: string | null
  best_match_score: number | null
  match_status: 'no_matches' | 'low_match'
  crawled_at: string | null
  ai_suggestion?: OrphanPageSuggestion
}

// Candidate Prompts types
export interface CandidatePrompt {
  text: string
  transaction_score: number
  intent: string
  funnel_stage?: string  // awareness, consideration, decision
  topic?: string
  sub_topic?: string
  audience_persona?: string
  reasoning: string
  target_audience?: string  // Legacy field
  citation_trigger?: string
}

export interface CandidatePromptsResponse {
  page_id: string
  page_url: string
  page_title: string | null
  page_topic?: string
  page_summary?: string
  prompts: CandidatePrompt[]
  generated_at: string | null
  cached: boolean
}

// Pages
export const pagesApi = {
  list: (params: { project_id?: string; search?: string; filter_type?: string; page?: number; page_size?: number }) =>
    api.get<{ pages: Page[]; total: number }>('/pages/', { params }),
  get: (id: string) => api.get<Page>(`/pages/${id}`),
  getStats: (projectId?: string) =>
    api.get<{
      total: number
      successful: number
      failed: number
      with_jsonld: number
      with_hreflang: number
      by_status_code: Record<string, number>
    }>('/pages/stats', { params: { project_id: projectId } }),
  crawlUrl: (projectId: string, url: string) =>
    api.post(`/pages/${projectId}/crawl-url`, null, { params: { url } }),
  importUrls: (projectId: string, urls: string[]) =>
    api.post(`/pages/${projectId}/import-urls`, urls),
  getCrawlJobs: (projectId?: string) =>
    api.get('/pages/crawl-jobs/list', { params: { project_id: projectId } }),
  cancelCrawlJob: (jobId: string) =>
    api.post(`/pages/crawl-jobs/${jobId}/cancel`),
  generateMissingEmbeddings: (projectId: string) =>
    api.post(`/pages/generate-missing-embeddings`, null, { params: { project_id: projectId } }),
  getOrphanPages: (params: { 
    project_id: string
    min_match_threshold?: number
    page?: number
    page_size?: number
    include_suggestions?: boolean
  }) =>
    api.get<{
      orphan_pages: OrphanPage[]
      total: number
      page: number
      page_size: number
      min_match_threshold: number
      ai_enabled: boolean
    }>('/pages/orphan-pages', { params }),
  generateOrphanSuggestions: (pageId: string) =>
    api.post<{
      page_id: string
      url: string
      title: string
      suggestion: OrphanPageSuggestion
    }>(`/pages/orphan-pages/${pageId}/generate-suggestions`),
  getCandidatePrompts: (pageId: string, regenerate?: boolean, numPrompts?: number) =>
    api.get<CandidatePromptsResponse>(`/pages/${pageId}/candidate-prompts`, {
      params: { regenerate, num_prompts: numPrompts }
    }),
  exportCandidatePromptsCsv: (projectId: string, includePagesWithoutPrompts?: boolean) =>
    api.get('/pages/export/candidate-prompts', {
      params: { project_id: projectId, include_pages_without_prompts: includePagesWithoutPrompts },
      responseType: 'blob'
    }),
  generateCandidatePromptsBatch: (projectId: string, regenerate?: boolean, numPrompts?: number, limit?: number) =>
    api.post<{ status: string; task_id?: string; pages_queued: number; message: string }>(
      '/pages/generate-candidate-prompts-batch',
      null,
      { params: { project_id: projectId, regenerate, num_prompts: numPrompts, limit } }
    ),
  listCandidatePrompts: (params: {
    project_id: string
    prompt_category?: string
    intent?: string
    funnel_stage?: string
    search?: string
    page?: number
    page_size?: number
  }) =>
    api.get<{
      prompts: Array<{
        page_id: string
        page_url: string
        page_title: string | null
        page_topic: string
        page_summary: string
        brand_name: string
        product_category: string
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
      }>
      total: number
      page: number
      page_size: number
      stats: {
        total_prompts: number
        by_prompt_category: Record<string, number>
        by_intent: Record<string, number>
        by_funnel_stage: Record<string, number>
        by_audience: Record<string, number>
      }
    }>('/pages/candidate-prompts/list', { params }),
  getCandidatePromptsStats: (projectId: string) =>
    api.get<{
      total_pages: number
      pages_with_prompts: number
      pages_without_prompts: number
      total_prompts: number
      avg_prompts_per_page: number
      by_prompt_category: Record<string, number>
      by_intent: Record<string, number>
      by_funnel_stage: Record<string, number>
      generation_progress: number
    }>('/pages/candidate-prompts/stats', { params: { project_id: projectId } }),
  cancelCandidatePromptsGeneration: (projectId: string) =>
    api.post<{ status: string; task_id?: string; message: string }>(
      '/pages/cancel-candidate-prompts-generation',
      null,
      { params: { project_id: projectId } }
    ),
  importSeoKeywords: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{ status: string; pages_updated: number; urls_not_found: number; message: string }>(
      '/pages/import-seo-keywords',
      formData,
      {
        params: { project_id: projectId },
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    )
  },
}

// Opportunities
export const opportunitiesApi = {
  list: (params: {
    project_id?: string
    status?: string
    recommended_action?: string
    min_priority?: number
    max_priority?: number
    page?: number
    page_size?: number
  }) =>
    api.get<{
      opportunities: Opportunity[]
      total: number
      by_status: Record<string, number>
      by_action: Record<string, number>
    }>('/opportunities/', { params }),
  get: (id: string) => api.get<Opportunity>(`/opportunities/${id}`),
  update: (id: string, data: { status?: string; notes?: string }) =>
    api.patch<Opportunity>(`/opportunities/${id}`, data),
  exportCsv: (projectId: string) =>
    api.get(`/opportunities/export/csv`, { params: { project_id: projectId }, responseType: 'blob' }),
  exportJson: (projectId: string) =>
    api.get(`/opportunities/export/json`, { params: { project_id: projectId }, responseType: 'blob' }),
  regenerateSuggestions: (projectId: string) =>
    api.post(`/opportunities/${projectId}/regenerate-suggestions/`),
  generateSuggestion: (opportunityId: string) =>
    api.post<Opportunity>(`/opportunities/${opportunityId}/generate-suggestion`),
}

// Competitive Analysis types
export interface CompetitorResult {
  url: string
  title: string
  snippet: string
}

export interface CompetitiveAnalysis {
  competitive_gap: string[]
  our_strengths: string[]
  top_competitor: string
  competitor_advantages: string[]
  recommendations: Array<{
    action: string
    impact: string
    effort: string
  }>
  content_suggestions: string
  cta_recommendation: string
  priority: string
}

export interface HighIntentPrompt {
  id: string
  text: string
  topic: string | null
  transaction_score: number
  popularity_score: number | null
  intent_label: string | null
  match_status: string | null
  best_match_score: number | null
  best_match: {
    url: string
    title: string
    snippet: string
    score: number
  } | null
}

// Competitive Analysis
export const competitiveApi = {
  getSummary: (projectId: string, minTransactionScore?: number) =>
    api.get<{
      total_high_intent: number
      answered_high_intent: number
      partial_high_intent: number
      avg_transaction_score: number
      top_topics: Array<{ topic: string; count: number }>
    }>('/competitive/summary', {
      params: { project_id: projectId, min_transaction_score: minTransactionScore }
    }),
  getHighIntentPrompts: (params: {
    project_id: string
    min_transaction_score?: number
    match_status?: string
    topic?: string
    page?: number
    page_size?: number
  }) =>
    api.get<{
      prompts: HighIntentPrompt[]
      total: number
      page: number
      page_size: number
      topic?: string
    }>('/competitive/high-intent-prompts', { params }),
  analyzePrompt: (promptId: string) =>
    api.post<{
      prompt_id: string
      prompt_text: string
      transaction_score: number
      intent_label: string | null
      our_content: { url: string; title: string; snippet: string }
      match_score: number
      competitors: CompetitorResult[]
      ai_analysis: CompetitiveAnalysis | null
      ai_enabled: boolean
    }>(`/competitive/analyze/${promptId}`),
}

// Jobs
export const jobsApi = {
  getStatus: (jobId: string) => api.get(`/jobs/${jobId}`),
  cancel: (jobId: string) => api.delete(`/jobs/${jobId}`),
}

// CWV Assessment types
export interface CWVAssessment {
  status: 'passed' | 'failed' | 'partial' | 'unknown'
  performance_score: number | null
  has_data: boolean
  message: string | null
  lcp_ok: boolean | null
  inp_ok: boolean | null
  cls_ok: boolean | null
}

// Core Web Vitals types
export interface CWVMetrics {
  lcp: number | null  // Largest Contentful Paint (ms)
  lcp_score: 'good' | 'needs-improvement' | 'poor' | null
  fid: number | null  // First Input Delay (ms)
  fid_score: 'good' | 'needs-improvement' | 'poor' | null
  inp: number | null  // Interaction to Next Paint (ms)
  inp_score: 'good' | 'needs-improvement' | 'poor' | null
  cls: number | null  // Cumulative Layout Shift
  cls_score: 'good' | 'needs-improvement' | 'poor' | null
  fcp: number | null  // First Contentful Paint (ms)
  fcp_score: 'good' | 'needs-improvement' | 'poor' | null
  ttfb: number | null  // Time to First Byte (ms)
  ttfb_score: 'good' | 'needs-improvement' | 'poor' | null
  performance_score: number | null  // 0-100
  has_field_data: boolean
  error: string | null
  fetched_at?: string
  strategy?: string
}

export interface CWVPageResult {
  page_id: string
  url: string
  title: string | null
  similarity_score: number
  cached: boolean
  cwv: CWVMetrics
}

// Core Web Vitals API
export const cwvApi = {
  getForPage: (pageId: string, refresh?: boolean, strategy?: string) =>
    api.get<{ page_id: string; url: string; cached: boolean; cwv: CWVMetrics }>(
      `/cwv/page/${pageId}`,
      { params: { refresh, strategy } }
    ),
  getForUrl: (url: string, strategy?: string) =>
    api.get<{ url: string; cwv: CWVMetrics }>(
      '/cwv/url',
      { params: { url, strategy } }
    ),
  getForPrompt: (promptId: string, refresh?: boolean, strategy?: string, limit?: number) =>
    api.get<{ prompt_id: string; matches: CWVPageResult[] }>(
      `/cwv/prompt/${promptId}`,
      { params: { refresh, strategy, limit: limit || 2 } }
    ),
  getStatus: () =>
    api.get<{ enabled: boolean; api_configured: boolean; message: string }>('/cwv/status'),
}

export default api


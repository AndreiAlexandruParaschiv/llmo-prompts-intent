# LLMO Prompts Intent Analyzer

A **Prompt-to-Content Gap Analysis Platform** that helps identify content opportunities by analyzing user prompts against existing website content.

![Platform Overview](docs/screenshot.png)

## Features

### 📊 Prompt Analysis
- **CSV Import**: Upload prompt data with metadata (topic, region, popularity, sentiment)
- **Language Detection**: Automatic language identification using ML
- **Intent Classification**: Categorize prompts as Transactional, Informational, or Navigational
- **Transaction Scoring**: Identify high-value commercial opportunities

### 🌐 Website Crawling
- **Playwright-based Crawler**: Full JavaScript rendering support
- **Content Extraction**: Main content, structured data, meta tags
- **MCP Checks**: CTAs, forms, reviews, canonical URLs, hreflang tags
- **Rate Limiting**: Polite crawling with configurable delays

### 🎯 Semantic Matching
- **Vector Embeddings**: sentence-transformers for semantic understanding
- **pgvector Integration**: Fast similarity search at scale
- **Match Classification**: Answered, Partial, or Gap status

### 💡 Opportunity Prioritization
- **Priority Scoring**: Based on popularity, transaction intent, sentiment
- **Recommended Actions**: Create content, update pages, optimize conversion
- **Export Options**: CSV and JSON export for reporting

## Tech Stack

### Backend
- **FastAPI** - Modern async Python API framework
- **PostgreSQL + pgvector** - Vector database for embeddings
- **Redis + Celery** - Background task processing
- **Playwright** - Headless browser for crawling
- **sentence-transformers** - Local embedding generation

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **TailwindCSS** - Utility-first styling
- **shadcn/ui** - Beautiful UI components
- **React Query** - Server state management
- **Zustand** - Client state management

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Using Docker Compose

1. **Clone the repository**
```bash
git clone https://github.com/your-org/llmo-prompts-intent.git
cd llmo-prompts-intent
```

2. **Start the services**
```bash
docker-compose up -d
```

3. **Access the application**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Local Development

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the server
uvicorn main:app --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://llmo:llmo_dev_password@localhost:5432/llmo_prompts

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# NLP
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Matching Thresholds
MATCH_THRESHOLD_ANSWERED=0.75
MATCH_THRESHOLD_PARTIAL=0.50
TRANSACTIONAL_THRESHOLD=0.6

# Optional: OpenAI for enhanced analysis
OPENAI_API_KEY=sk-...
```

## Usage Guide

### 1. Create a Project
1. Navigate to **Projects**
2. Click **New Project**
3. Enter project name and target domains (e.g., `example.com, blog.example.com`)

### 2. Import Prompts
1. Go to your project's **Import** page
2. Upload a CSV file with your prompt data
3. Map columns to expected fields:
   - `prompt` (required): The user query text
   - `topic`: Category/topic classification
   - `region`: Geographic region
   - `popularity`: Low/Medium/High or numeric score
   - `sentiment`: Positive/Neutral/Negative
4. Click **Process CSV**

### 3. Crawl Target Domains
1. From the project overview, click **Start Crawl**
2. The crawler will index pages from your target domains
3. Monitor progress in the **Imports** tab

### 4. Run Matching
1. Click **Run Matching** to match prompts to pages
2. Each prompt gets classified as:
   - ✅ **Answered**: Content exists (similarity ≥ 75%)
   - ⚠️ **Partial**: Some coverage (similarity 50-75%)
   - 🎯 **Gap**: No matching content

### 5. Review Opportunities
1. Navigate to **Opportunities**
2. Filter by status, action type, or priority
3. Export results for your content team

## CSV Format

Your prompt CSV should include these columns (names are auto-detected):

| Column | Description | Values |
|--------|-------------|--------|
| `Prompt` | User search query | Text |
| `Topic` | Category | Text |
| `Region` | Market/Geography | US, EU, APAC, etc. |
| `Popularity` | Search volume | Low, Medium, High |
| `Sentiment` | User sentiment | Positive, Neutral, Negative |
| `Visibility Score` | Brand visibility | Percentage (e.g., 45%) |
| `Sources URLs` | Reference URLs | Semicolon-separated |

## API Documentation

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `GET /api/projects/{id}` - Get project details
- `POST /api/projects/{id}/crawl` - Start crawl
- `POST /api/projects/{id}/match` - Run matching

### CSV Import
- `POST /api/csv/upload/{project_id}` - Upload CSV
- `POST /api/csv/{import_id}/process` - Process with mapping
- `GET /api/csv/{import_id}` - Get import status

### Prompts
- `GET /api/prompts` - List prompts (with filters)
- `GET /api/prompts/{id}` - Get prompt with matches

### Opportunities
- `GET /api/opportunities` - List opportunities
- `PATCH /api/opportunities/{id}` - Update status
- `GET /api/opportunities/export/csv` - Export CSV

Full API documentation available at `/api/docs`

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │
│  (React + TS)   │     │    (FastAPI)    │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
              │ PostgreSQL│ │  Redis  │ │  Celery   │
              │ + pgvector│ │         │ │  Worker   │
              └───────────┘ └─────────┘ └───────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with ❤️ for content strategists and SEO teams.


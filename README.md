# LLMO Prompts Intent Analyzer

A **Prompt-to-Content Gap Analysis Platform** that helps identify content opportunities by analyzing user prompts against existing website content. Powered by AI to provide intelligent recommendations.

## 🚀 Quick Start (5 minutes)

### Prerequisites

- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)

### Step 1: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/AndreiAlexandruParaschiv/llmo-prompts-intent.git
cd llmo-prompts-intent

# Create environment file
cp .env.example .env
```

### Step 2: Add Your API Keys (Optional but Recommended)

Edit the `.env` file to add your Azure OpenAI credentials for AI-enhanced features. See `.env.example` for the template.

> **Note:** The app works without Azure OpenAI using rule-based classification. AI features are optional but recommended for better accuracy.

### Step 3: Start the Application

```bash
docker-compose up -d
```

Wait about 60 seconds for all services to initialize.

### Step 4: Access the App

Open your browser and go to: **http://localhost:5173**

That's it! 🎉

---

## 📖 How to Use

### Workflow Overview

```
1. Create Project → 2. Import Prompts (CSV) → 3. Crawl Website → 4. Match & Analyze → 5. Review Opportunities
```

### Step 1: Create a Project

1. Go to **Projects** in the sidebar
2. Click **New Project**
3. Enter:
   - **Name**: e.g., "My Website Analysis"
   - **Target Domains**: e.g., `example.com, blog.example.com`
4. Click **Create**

### Step 2: Import Your Prompts

1. Click on your project
2. Go to the **Imports** tab
3. Click **Import CSV**
4. Upload your CSV file with prompts
5. Map the columns:
   - `Prompt` → The search query (required)
   - `Topic` → Category
   - `Popularity` → Search volume (Low/Medium/High or numeric)
   - `Sentiment` → User sentiment (-1 to 1 or Positive/Neutral/Negative)
6. Click **Process CSV**

**Example CSV format:**
```csv
Prompt,Topic,Region,Popularity,Sentiment
"How to reset my password",account,US,High,0.5
"What is your return policy",returns,UK,Medium,0.0
"Best product for beginners",products,US,Medium,0.7
```

### Step 3: Crawl Your Website

1. From the project **Overview** tab
2. Click **Start Crawl**
3. Wait for the crawl to complete (progress shown in real-time)

### Step 4: Match Prompts to Content

1. Click **Match & Analyze**
2. The system will:
   - Generate embeddings for all content
   - Find semantic matches between prompts and pages
   - Classify each prompt as Answered/Partial/Gap
   - Generate AI content suggestions for gaps

### Step 5: Review Opportunities

1. Go to **Opportunities** in the sidebar
2. Filter by:
   - **Priority**: High (70+), Medium (40-69), Low (0-39)
   - **Status**: New, In Progress, Completed
   - **Action**: Create Content, Expand Content, Add CTA
3. Click on any opportunity to see AI recommendations
4. **Export** results as CSV or JSON for your team

---

## ✨ Features

### 🤖 AI-Powered Analysis (with Azure OpenAI)
- **Intent Classification**: 13 intent categories (Transactional, Informational, Commercial, etc.)
- **"Why This Intent?"**: Detailed AI explanation for each classification
- **Content Suggestions**: Title, outline, keywords, and CTA recommendations
- **Bulk Reclassification**: Reclassify all prompts with one click

### 📊 Prompt Analysis
- **CSV Import**: Upload prompt data with metadata
- **Language Detection**: Automatic language identification
- **Transaction Scoring**: Identify high-value commercial opportunities
- **Popularity & Sentiment**: Factor into prioritization

### 🌐 Website Crawling
- **JavaScript Rendering**: Full Playwright-based crawling
- **Content Extraction**: Main content, structured data, meta tags
- **Deduplication**: Automatic duplicate page handling
- **Rate Limiting**: Polite crawling with configurable delays

### 🎯 Semantic Matching
- **Vector Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **pgvector**: Fast similarity search at scale
- **Match Status**: Answered (75%+), Partial (50-75%), Gap (<50%)

### 💡 Opportunity Prioritization
- **Smart Scoring**: Popularity (40%) + Transaction (30%) + Sentiment (20%) - Difficulty (10%)
- **Action Types**: Create Content, Expand Content, Add CTA, Improve Ranking
- **Export**: CSV with all AI suggestions included

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

See `.env.example` for all available options. Key settings:

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI endpoint URL | For AI features |
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key | For AI features |
| `AZURE_COMPLETION_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`) | For AI features |

> **Note:** Database credentials are pre-configured in `docker-compose.yml` for local development. For production, use secure passwords and environment-specific configuration.

### Without Azure OpenAI

The app works without Azure OpenAI using rule-based classification:
- Intent detection uses keyword patterns
- Content suggestions are template-based
- All core features remain functional

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                    React + TypeScript                        │
│                    http://localhost:5173                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│                    FastAPI + Python                          │
│                    http://localhost:8000                     │
└─────────────────────────────────────────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Redis       │  │  Celery Worker  │
│   + pgvector    │  │    (cache)      │  │  (background)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  Azure OpenAI   │
                                          │    (optional)   │
                                          └─────────────────┘
```

---

## 🛠️ Development Setup

### Running Locally (without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start PostgreSQL and Redis (via Docker)
docker-compose up -d postgres redis

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Celery Worker

```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info
```

---

## 📡 API Reference

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/projects` | Create project |
| `GET` | `/api/projects` | List projects |
| `GET` | `/api/projects/{id}` | Get project details |
| `GET` | `/api/projects/{id}/stats` | Get project statistics |
| `POST` | `/api/projects/{id}/crawl` | Start website crawl |
| `POST` | `/api/projects/{id}/match` | Run prompt matching |

### Prompts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/prompts` | List prompts with filters |
| `GET` | `/api/prompts/{id}` | Get prompt with matches |
| `GET` | `/api/prompts/{id}/explain-intent` | Get AI intent explanation |
| `POST` | `/api/prompts/reclassify-all` | Reclassify all with AI |

### Opportunities
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/opportunities` | List opportunities |
| `PATCH` | `/api/opportunities/{id}` | Update status |
| `GET` | `/api/opportunities/export/csv` | Export as CSV |
| `GET` | `/api/opportunities/export/json` | Export as JSON |
| `POST` | `/api/opportunities/regenerate-suggestions` | Regenerate AI suggestions |

Full interactive docs: **http://localhost:8000/api/docs**

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Restart everything
docker-compose down && docker-compose up -d
```

### Database connection errors

```bash
# Recreate database
docker-compose down -v
docker-compose up -d
```

### AI features not working

1. Check your `.env` file has correct Azure OpenAI credentials
2. Verify the deployment name matches your Azure setup
3. Check backend logs: `docker-compose logs -f backend`

### Crawl stuck or slow

- The crawler respects rate limits (1 request/second by default)
- Check if target site is blocking requests
- View worker logs: `docker-compose logs -f celery-worker`

---

## 📊 CSV Export Fields

The opportunities CSV export includes:

| Field | Description |
|-------|-------------|
| Priority Score | 0-100 overall priority |
| Prompt | Original user query |
| Topic | Category/topic |
| Intent | Classification (transactional, informational, etc.) |
| Transaction Score | 0-1 likelihood of conversion |
| Recommended Action | create_content, expand_content, add_cta, improve_ranking |
| Reason | Why this action is recommended |
| Status | new, in_progress, completed, dismissed |
| Difficulty Score | 0-1 implementation difficulty |
| AI Suggested Title | GPT-4o generated title |
| AI Content Type | Suggested format (FAQ, guide, landing page) |
| AI Outline | Key points to cover |
| AI Call to Action | Suggested CTA text |
| AI Keywords | Recommended keywords |
| AI Priority Reason | Why this is important |

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with ❤️ for GW

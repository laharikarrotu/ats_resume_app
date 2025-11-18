# ATS Resume Generator 🚀

> **Full-Stack AI-Powered Resume Optimization Tool**  
> Built with FastAPI, LLM (OpenAI/Gemini), Vector Search, and Modern Web Stack

---

## 🎯 Project Overview

This is a **production-ready, recruiter-impressive ATS (Applicant Tracking System) resume generator** that:

- **Extracts job-specific keywords** from job descriptions using LLMs (OpenAI/Gemini)
- **Generates ATS-optimized resumes** in Word (.docx) format with intelligent keyword injection
- **Provides a modern web UI** for recruiters and job seekers
- **Uses vector embeddings** to match candidate experience with job requirements (RAG)
- **Maintains 1-page C3 resume format** for maximum ATS compatibility

**Perfect for showcasing:** Full-Stack Development, ML/LLM Engineering, and Production-Ready Software Architecture.

---

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  Web Browser │  │   Mobile UI  │  │   API Client        │  │
│  │  (HTML/JS)   │  │   (Future)   │  │   (cURL/Postman)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘  │
└─────────┼──────────────────┼──────────────────────┼────────────┘
          │                  │                      │
          │  HTTP/REST       │                      │
          └──────────────────┼──────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                    FastAPI Application Layer                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (Uvicorn)                                │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │   Routes    │  │   Middleware │  │   Auth/JWT   │  │  │
│  │  │  /generate  │  │   (CORS,     │  │   (Future)   │  │  │
│  │  │  /download  │  │    Logging)  │  │              │  │  │
│  │  │  /health    │  │              │  │              │  │  │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  │  │
│  └─────────┼─────────────────┼──────────────────┼──────────┘  │
└────────────┼─────────────────┼──────────────────┼─────────────┘
             │                 │                  │
┌────────────┼─────────────────┼──────────────────┼─────────────┐
│    ┌───────▼───────┐  ┌──────▼───────┐  ┌──────▼──────┐      │
│    │   Business    │  │   LLM Client │  │   Vector    │      │
│    │   Logic       │  │   (OpenAI/   │  │   Search    │      │
│    │   Layer       │  │   Gemini)    │  │   (RAG)     │      │
│    │               │  │              │  │             │      │
│    │  • Resume     │  │  • Keyword   │  │  • Embed    │      │
│    │    Generator  │  │    Extract   │  │    JD       │      │
│    │  • Template   │  │  • Bullet    │  │  • Match    │      │
│    │    Engine     │  │    Rewrite   │  │    Exp.     │      │
│    │  • Formatting │  │  • STAR      │  │  • Retrieve │      │
│    └───────┬───────┘  └──────┬───────┘  └──────┬──────┘      │
│            │                  │                 │             │
┌────────────┼──────────────────┼─────────────────┼─────────────┐
│    ┌───────▼────────┐  ┌──────▼──────┐  ┌──────▼──────┐     │
│    │   Data Layer   │  │   Storage   │  │   External  │     │
│    │                │  │             │  │   Services  │     │
│    │  • PostgreSQL  │  │  • Vector   │  │             │     │
│    │    (Future)    │  │    DB       │  │  • OpenAI   │     │
│    │  • Pydantic    │  │    (Chroma/ │  │    API      │     │
│    │    Models      │  │    Qdrant)  │  │  • Gemini   │     │
│    │  • File System │  │             │  │    API      │     │
│    └────────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### Resume Generation Flowchart

```
┌──────────────────────────────────────────────────────────────┐
│                    USER INPUT                                 │
│  1. Paste Job Description (JD)                                │
│  2. Optionally: Upload existing resume / experience data      │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              STEP 1: JOB DESCRIPTION PROCESSING               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • Validate JD format (Pydantic)                      │   │
│  │  • Preprocess text (clean, normalize)                 │   │
│  │  • Extract metadata (title, company, location)        │   │
│  └────────────────────┬──────────────────────────────────┘   │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│          STEP 2: LLM KEYWORD EXTRACTION                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  OpenAI/Gemini API Call:                              │   │
│  │  • Prompt: "Extract 20-40 skills/keywords from JD"   │   │
│  │  • Model: gpt-4o-mini / gemini-pro                   │   │
│  │  • Output: JSON array of keywords                     │   │
│  └────────────────────┬──────────────────────────────────┘   │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│        STEP 3: VECTOR SEARCH (RAG) - OPTIONAL                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  IF user has uploaded experience data:                │   │
│  │  • Embed JD keywords using sentence-transformers      │   │
│  │  • Query vector DB for matching experience bullets    │   │
│  │  • Retrieve top 5-10 most relevant experience items   │   │
│  └────────────────────┬──────────────────────────────────┘   │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│          STEP 4: RESUME GENERATION                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • Load template (c3_template.docx) or create new     │   │
│  │  • Inject keywords into "Key Skills" section          │   │
│  │  • Format with python-docx (1-page limit)            │   │
│  │  • Apply ATS-friendly formatting                      │   │
│  └────────────────────┬──────────────────────────────────┘   │
└───────────────────────┼──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              STEP 5: OUTPUT                                   │
│  • Save DOCX to outputs/ directory                           │
│  • Return file download link or direct file response         │
│  • Log generation metadata (for analytics)                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Core Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI | High-performance async API + auto-generated docs |
| **LLM Provider** | OpenAI / Google Gemini | Keyword extraction, bullet rewriting, STAR formatting |
| **Document Generation** | python-docx | Word (.docx) resume creation with precise formatting |
| **Vector Search** | sentence-transformers + Chroma/Qdrant | RAG for matching experience with job requirements |
| **Validation** | Pydantic v2 | Type-safe API request/response validation |
| **Templating** | Jinja2 | Dynamic HTML generation for web UI |

### Frontend Stack (Future)

| Technology | Purpose |
|-----------|---------|
| **HTML5 + Tailwind CSS** | Modern, responsive web UI |
| **Vanilla JS / Alpine.js** | Lightweight interactivity (no heavy frameworks) |
| **Fetch API** | Async API calls to FastAPI backend |

### Infrastructure & DevOps

| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerization for portable deployment |
| **Docker Compose** | Multi-service orchestration (app + DB + vector DB) |
| **GitHub Actions** | CI/CD pipeline (tests → build → deploy) |
| **PostgreSQL** (Future) | Persistent storage for user accounts, job history |
| **Prometheus / Grafana** (Future) | Metrics and observability |

### ML/LLM Stack

| Technology | Purpose |
|-----------|---------|
| **OpenAI API** | GPT-4o-mini for cost-effective keyword extraction |
| **sentence-transformers** | Generate embeddings for JD and experience bullets |
| **Chroma / Qdrant** | Vector database for semantic search |

---

## 📁 Project Structure

```
ats_resume_app/
│
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore rules
├── Dockerfile                     # Docker container config
├── docker-compose.yml             # Multi-service orchestration (Future)
│
├── resume_templates/              # Word template files
│   └── c3_template.docx           # C3 format resume template
│
├── outputs/                       # Generated resumes (gitignored)
│   └── .gitkeep
│
├── src/                           # Application source code
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── models.py                  # Pydantic models for validation
│   ├── resume_generator.py        # Core Word generation logic
│   ├── llm_client.py              # OpenAI/Gemini API integration
│   ├── vector_search.py           # RAG/vector search (Future)
│   └── utils.py                   # Helper functions
│
├── static/                        # Static assets
│   └── styles.css                 # CSS styles
│
├── templates/                     # HTML templates
│   └── index.html                 # Main web UI
│
├── tests/                         # Test suite (Future)
│   ├── test_resume_generator.py
│   ├── test_llm_client.py
│   └── conftest.py
│
└── .github/                       # CI/CD workflows
    └── workflows/
        └── ci.yml                 # GitHub Actions pipeline
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip
- (Optional) Docker + Docker Compose

### Local Development

1. **Clone and navigate to the project:**
```bash
cd ats_resume_app
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set environment variables:**
```bash
# On Windows PowerShell:
$env:OPENAI_API_KEY = "sk-your-key-here"

# On Linux/Mac:
export OPENAI_API_KEY="sk-your-key-here"
```

5. **Run the application:**
```bash
uvicorn src.main:app --reload
```

6. **Open in browser:**
- Web UI: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

### Docker Deployment

```bash
# Build image
docker build -t ats-resume-app .

# Run container
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-your-key ats-resume-app
```

### Cloud Deployment

This app can be deployed to various platforms:

- **Railway** (Recommended) - Best for FastAPI apps
- **Render** - Easy deployment with auto-scaling
- **Vercel** - Serverless functions (limited for long-running tasks)
- **Fly.io** - Global distribution

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

**Quick Deploy to Railway:**
1. Push code to GitHub
2. Go to https://railway.app and sign up with GitHub
3. Create new project → Deploy from GitHub repo
4. Add `OPENAI_API_KEY` environment variable in Variables tab
5. Railway auto-deploys! Get your URL from Settings → Domains

**📚 See [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) for detailed instructions.**

---

## 📊 API Endpoints

### Web UI
- `GET /` - Main HTML interface

### API Endpoints
- `POST /generate_resume/` - Generate resume from form data (returns DOCX file)
- `POST /api/generate_resume` - Generate resume from JSON (returns metadata + download link)
- `GET /download/{filename}` - Download generated resume
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)

### Example API Usage

```bash
# JSON API
curl -X POST "http://localhost:8000/api/generate_resume" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Looking for a Python developer with FastAPI experience..."
  }'
```

---

## 🎯 Roadmap & Features

### ✅ Phase 1: Core MVP (Current)
- [x] Basic FastAPI server
- [x] LLM keyword extraction (placeholder)
- [x] DOCX resume generation
- [x] Simple web UI
- [x] Docker support

### 🔄 Phase 2: Production-Ready (Next Steps)
- [ ] **OpenAI Integration** - Real LLM keyword extraction
- [ ] **Enhanced Resume Generation** - Better formatting, STAR bullets
- [ ] **Vector Search (RAG)** - Match experience with job requirements
- [ ] **PostgreSQL Database** - User accounts, job history
- [ ] **JWT Authentication** - Secure multi-user access
- [ ] **Logging & Metrics** - Structured logging, Prometheus metrics

### 🚀 Phase 3: Advanced Features
- [ ] **Multiple Resume Templates** - Choose from C3, modern, creative
- [ ] **Batch Processing** - Generate resumes for multiple job descriptions
- [ ] **Resume Analytics** - ATS score, keyword match percentage
- [ ] **CI/CD Pipeline** - Automated testing and deployment
- [ ] **Cloud Deployment** - Deploy to AWS/GCP/Azure

---

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest tests/

# With coverage
pytest --cov=src tests/
```

---

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM features | Yes (for production) |
| `GEMINI_API_KEY` | Google Gemini API key (alternative) | Optional |
| `DATABASE_URL` | PostgreSQL connection string (future) | No |
| `JWT_SECRET` | Secret key for JWT auth (future) | No |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- LLM powered by [OpenAI](https://openai.com/) / [Google Gemini](https://ai.google.dev/)
- Document generation using [python-docx](https://python-docx.readthedocs.io/)

---

## 📞 Contact & Support

For questions, issues, or suggestions, please open an issue on GitHub.

---

**Built with ❤️ for Full-Stack and ML/LLM Engineers**

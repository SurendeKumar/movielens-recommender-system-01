# Movie Recommender System

A conversational AI movie assistant built with **FastAPI**, **SQLite**, and **Large Language Models (LLMs)**.  

The system combines structured data retrieval (SQLite) with natural language generation (LLMs) to provide interactive, conversational answers about movies.

---

## Features

- Local **SQLite** database (movies, genres, ratings, cast, director, overview)  
- Dataset ingestion from **MovieLens 100K** or **TMDB 5000**  
- REST API with **FastAPI** and auto-generated docs  
- Hybrid approach: **SQL for accuracy** + **LLM for conversational responses**  
- Deployable with **Docker**  

---

## Project Structure

```
movie-recommender_system-01/
│
├── movie_reccommender_system/        # Core agent logic (intents, LLM orchestration)
    └──data_ingestor/      # Dataset ingestion scripts
    ├── db/
         └── movies.db      # SQLite database (generated after ingestion)
    ├── utilities/          # Helper scripts (logging, config, prompts)
    ├── data_raw/           # Raw datasets (unzipped Kaggle/TMDB files)
    ├── llm_cient/          # LLM Client for conversation recommender system
├── tests/              # Unit & integration tests
├── router/             # FastAPI routers (API endpoints)
├── app.py              # FastAPI entrypoint
├── startup.sh          # Startup script
├── Dockerfile          # Docker build file
├── docker-compose.yml  # Docker Compose config
├── .env                # Environment variables (DB path, LLM config, API keys)
├── pyproject.toml      # Python dependencies - pkg manager
└── README.md           # outline the package details
```

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/SurendeKumar/movielens-recommender-system-01
cd movielens-recommender-system-01
```

### 2. Create a virtual environment
```bash
- python -m venv .venv

- Install with editable mode: pip install -e .
- Install with editable mode and also extra dependencies under .dev inside tom file (mainly for testing)

```

Activate it:

- **macOS/Linux**
  ```bash
  source .venv/bin/activate
  ```
- **Windows (PowerShell)**
  ```powershell
  .venv\Scripts\activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download dataset
- Download **MovieLens 100K** or **TMDB 5000 Movie Dataset** from Kaggle  
- Unzip the files  
- Place them into the `data_raw/` directory  

### 5. Run data ingestion
```bash
python -m data_ingestor.load_data
```

This step will:
- Parse the raw dataset  
- Normalize movies, genres, and ratings  
- Create and populate the SQLite database at:
  ```
  db/movies.db
  ```

### 6. Start the FastAPI application
```bash
uvicorn app:app --reload
```

## API Endpoints

- `POST /query` → Ask natural language questions (*“Tell me about Inception”*)  
- `GET /movies/{movie_id}` → Retrieve structured details about a movie  
- `GET /recommendations` → Recommend movies with filters (genre, year, rating)  

---

## LLM Integration

Supports multiple providers (via `.env` config):  
- **Hugging Face Transformers** (local or hosted)  
- **Ollama** (local inference)  
- **OpenAI API** (`gpt-4o-mini`, `gpt-4.1`)  

LLMs are used to:  
- Phrase results conversationally  
- Explain recommendations  
- Handle ambiguous queries with clarifying questions  

---

## Running with Docker

Build and start with Docker Compose:
```bash
docker-compose up --build
```

---

## Testing

Run tests with:
```bash
pytest tests/
```

---

## Roadmap

- [ ] Add semantic search with embeddings (FAISS/pgvector)  
- [ ] Enhance query parsing with LLM-based slot extraction  
- [ ] Add personalization (history-based recommendations)  
- [ ] Improve explanation style with prompt tuning  

---

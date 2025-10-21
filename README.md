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
- Install with editable mode and also extra dependencies under .dev inside tom file (mainly for testing): pip install -e .[dev]

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
pip install -e .
pip install -e .[dev]
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
./startup.ps1 (Windows (PowerShell))
./startup.sh (macOS/Linux - save .ps1 as .sh)
```


## 7. Running with Docker

Build and start with Docker Compose:
```bash
docker-compose up --build
```


## API Endpoints

Part 1: **Data Ingestion**
----------------------------

Goal: Get MovieLens data into your SQLite DB, normalize genres, and compute stats.

### Steps:

1.  uvicorn app:app --reload (assuming your entrypoint is app.py with app = FastAPI())
    
2.  OR run everything in one go:
    
    *   POST /ingest/data-insertion → loads u.item + u.data → inserts movies and ratings.
        
    *   POST /ingest/genres → builds genres + movie\_genres.
        
    *   POST /ingest/movie-ratings-stats → computes avg\_rating + num\_ratings.
        
    
    *   POST /ingest/data-ingestor → runs all 3 steps in sequence.
        
        
3.  **Check results in logs/DB**
    
    *   Logs show inserted counts, genres created, movies updated.
        
    *   sqlite3 movie\_reccommender\_system/db/movies.dbsqlite> .tablessqlite> SELECT COUNT(\*) FROM movies;
        

Part 2: **Query Processing**
------------------------------

Goal: Parse natural language queries → detect intent + slots → run SQL to fetch results.

### Steps:

1.  **Keep FastAPI app running** (same as above).
    
2.  **Call query endpoints:**
    
    *   { "text": "recommend action movies from 2020" }
        
    *   { "text": "recommend action movies from 2020", "limit": 5 }
        
3.  **Check logs**
    
    *   You’ll see info logs for parsing, SQL execution, and number of rows returned.


Part 3: **LLM Integration**
Supports multiple providers (via `.env` config):  
- **Hugging Face llama**

LLMs are used only for movie recommendations

---


## Run Flow in Order
--------------------

So when starting fresh, the order is:

1.  **Ingest data**
    
    * Call POST /ingest/data-ingestor once.
        
    * Confirms DB is ready with movies, ratings, genres, stats.
  
2. **Query processing**

    * Call POST /query/parse (if you want to debug parser).

    * Call POST /query/execute to actually get movie results.

---


## Testing

Run tests with:
```bash
pytest tests/
```

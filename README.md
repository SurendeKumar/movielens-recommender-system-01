# Movie Recommender System

A conversational AI movie assistant built with **FastAPI**, **SQLite**, and **Large Language Models (LLMs) using meta-llama/Llama-3.2-3B-Instruct with Hugging Face**.  

The system combines structured data retrieval (SQLite) with natural language generation (LLMs) to provide interactive, conversational answers about movies.

---

## Features

- Local **SQLite** database (movies, genres, ratings, cast, director, overview)  
- Dataset ingestion from **MovieLens 100K** or **TMDB 5000**  
- REST API with **FastAPI** and auto-generated docs  
- LLM (meta-llama/Llama-3.2-3B-Instruct) for conversational responses  

---

## Project Structure

```
movie-recommender-system-01/
│
├── movie_reccommender_system/                          # Core agent logic (intents, LLM orchestration)
└── data_ingestor/                                      # Data Ingestor module
            └── data_raw/                               # Raw datasets (unzipped Kaggle/TMDB files)
            └── data_loader.py                          # load Movielens data for ingestion
            └── db_ingestor.py                          # ingest movielens data into SQLite DB
            └── data_ingestor_main.py                   # driver class for movielens data ingestion 
    ├── db/
        └── movies.db                                   # SQLite database (generated after ingestion)
        └── db_select.py                                # collecting stats for basic EDA.
    ├── query_processor                                 # Query Processor module
        └── query_preprocessing.py                      # query preprocessor
        └── rule_based_parser.py                        # query rule based parser 
        └── query_processor_main                        # driver class for user's query processings

    ├── query_responder                                 # LLM Query Responder module
        └── llm_preprocessing.py                        # preprocessing before LLM inference
    └── llm_context_builder.py                          # context builder before LLM inference
        └── llm_edgecase_handling.py                    # handle the edgecase before LLM inference
        └── llm_conversational_renderer.py              # render conversational tasks before LLM inference
        └── llm_prompt_builder.py                       # LLM prompt builder
        └── llm_cient.py                                # LLM Client for conversation recommender system

    ├── response_basemodel_validator                    # pydantic basemodel validation module
        └── data_ingestor_model.py                      # requet/response validation for data ingestor
        └── query_response_model.py                     # request/response validation for query processor
        └──llm_response_model.py                        # erequest/respons validation for LLM client


├── tests/                                              # Unittest 
    └── test_data_ingestion                             # TestSuite - data_ingestor module
        └── test_data_loader.py                         # data loader
    └── test_db_ingestor.py                             # db_ingestor
        └── test_data_ingestor_main.py                  # data_ingestor_main
    └── test_query_processor                            # TestSuite - Query processor module
    └── test_query_preprocessing.py                     # quer preprocessing
        └── test_rule_based_parser.py                   # query rule based parser
        └── test_query_processor_main.py                # query_processor main integration
    └── test_query_responder                            # TestSuite - LLM client Repsonder
        └── test_llm_preprocessing_and_context.py       # llm preprocessing & context builder
        └── test_llm_edgecase_handling.py               # llm edgecase handling
        └── test_llm_conversational_renderer.py         # llm conversational renderer
        └── test_llm_prompt_builder.py                  # LLM prompt builder
        └── test_llm_client.py                          # LLM client for conversational inference


├── router/                                             # FastAPI routers (API endpoints)
    └── data_ingestor_router.py                         # (testing & exploration purposes) data ingestor controller
    └── query_processor_router.py                       # (testing & exploration purposes) query processor controller 
    └── hf_llama_inference_router.py                    # (testing & exploration purposes) llm inference controller
    └── movie_recommender_sys_router.py                 # Main router - Movielens Recommender Router (POST)
├── app.py                                              # FastAPI entrypoint
├── movie_reccommender_client.py                        # CLI client to trigger the Recommender system
├──.gitignore                                           # git system file
├── startup.ps1                                         # Startup script
├── .env                                                # Environment variables (DB path, LLM config, API keys)
├── pyproject.toml                                      # Python dependencies - pkg manager
└── README.md                                           # outline the package details
```

---

## API Endpoints

1.  **Data Ingestion**
----------------------------

    *   API Endpoint: POST api/movielens/recommender
        
        
2.  **Sample payload:**
    
    *   { "text": "recommend action movies from 1997" }

    *   { "text": "recommend action movies from 1998", "limit": 5 }

    *   {"text": "recommend action movies from 1997 with rating at least 3"}

    *   {"text": "top 5 action since 1998"}
        
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
- Download **MovieLens 100K** or **TMDB 5000 Movie Dataset** from [Kaggle](https://www.kaggle.com/datasets/prajitdatta/movielens-100k-dataset/data)  
- Unzip the files  
- Place under the folder data_ingestor/data_raw/ -> this is how it should look like -> data_ingestor/data_raw/archive/ml-100k/**files


### 5. Start the FastAPI application
```bash
uvicorn app:app --reload
./startup.ps1 (Windows (PowerShell))
```

---


## TestSuite Coverage Highlights

## Data Ingestion

### data_loader
- Raw files can be loaded into DataFrames.

### db_ingestor
- Insert movies + ratings into SQLite successfully.
- Create normalized genre tables (`genres`, `movie_genres`).
- Compute and update movie rating stats (`avg_rating`, `num_ratings`).

### data_ingestor_main
- End-to-end workflow with `MovieLensSqliteIngestor`:
  - Insert data.
  - Normalize genres.
  - Update rating stats.
  - Orchestrate all steps together with success/failure handling.


## Query Processor

### query_preprocessing
- Convert user query text to lowercase and strip spaces.
- Split queries into words.
- Detect valid 4-digit years.
- Parse float values safely from text.
- Extract year values from date text (end of string, embedded, or none).

### rules_based_parser
- Detect "top N" (digits, words, default fallback).
- Extract year values (single year, since, ranges with hyphen / to / between).
- Extract minimum rating constraints with comparators (`≥` / `≤`).
- Identify genres (single and multi-word forms).
- Extract movie titles from quotes or phrases (`about`, `like`, `who directed/starred`).
- Parse complete user queries into structured intents (`GET_DETAILS`, `SIMILAR_MOVIES`, `TOP_N`, `RECOMMEND_BY_FILTER`).

### query_processor_main
- Connect to SQLite database.
- Convert SQL rows into normalized response models.
- Run queries by intent:
  - `GET_DETAILS` – title lookup.
  - `RECOMMEND_BY_FILTER` – genres, year filters, ratings.
  - `TOP_N` – delegate to recommend logic.
  - `SIMILAR_MOVIES` – shared genres with a base title.
- Dispatcher `query_executor` routes to correct query handler.
- Output handler normalizes results into `{intent, slots, results}` with raw results list.


## LLM Responder

### llm_preprocessing
- Validate executor payload shape (`intent`, `slots`, `results`).
- Cast slot types (years → int, ratings → float).
- Normalize result rows (ids, titles, years, ratings, genres).
- De-duplicate by `movieId`.
- Sort and cap results per intent.

### llm_context_builder
- Build compact `filters_text` (intent hint, genres, time window, rating bounds, seed title).
- Derive `time_window` (`in`, `since`, `until`, `between`).
- Derive `rating_bounds` (`=`, `≥`, `≤`, `between`).
- Collect lightweight context: `result_count`, `seed_title`, `titles`.

### llm_edgecase_handling
- Detect flags: `no_results`, `overflow`, `sparse_quality`, `seed_missing`, `thin_metadata`, `ties_possible`.
- Diversify on overflow (round-robin by primary genre) and cap.
- Apply quality floor by `num_ratings` threshold.
- Annotate context with `edge_notes`, `suggestions`, `sampled_from`.

### llm_prompt_builder
- Build deterministic LLM prompt (system guidance, context line, found count).
- Compile fact lines (title, year, rating, count, genres) up to limit.
- Support tone and item caps.

### llm_conversational_renderer
- Render human answer per intent: `TOP_N`, `RECOMMEND_BY_FILTER`, `GET_DETAILS`, `SIMILAR_MOVIES`.
- Compact title briefs and full sentences.
- Natural joins for short lists; robust fallbacks.

### llm_client
- End-to-end assembly: preprocessing → context → edge handling → prompt → conversational answer.
- Deterministic, no external LLM dependency; timing metrics captured.


# TestSuite Execution

### Run as individual tests
```bash
# Part 1 – Data Ingestion
python tests/test_data_ingestion/test_data_loader.py
python tests/test_data_ingestion/test_db_ingestor.py
python tests/test_data_ingestion/test_data_ingestor_main.py

# Part 2 – Query Processor
python tests/test_query_processor/test_query_preprocessing.py
python tests/test_query_processor/test_rule_based_parser.py
python tests/test_query_processor/test_query_processor_main.py

# Part 3 – LLM Responder
python tests/test_query_responder/test_llm_preprocessing_and_context.py
python tests/test_query_responder/test_llm_edgecase_handling.py
python tests/test_query_responder/test_llm_prompt_builder.py
python tests/test_query_responder/test_llm_conversational_renderer.py
python tests/test_query_responder/test_llm_client.py
```

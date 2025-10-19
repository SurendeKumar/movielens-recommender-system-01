# Dockerfile
# ---- Base image ----
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# system deps - add build tools only in the builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Builder: build wheels for the app
FROM base AS builder
WORKDIR /build

# copy pyproject + source package
COPY pyproject.toml README.md ./
COPY movie_reccommender_system ./movie_reccommender_system

# upgrade pip and build wheels (app wheel + all deps)
RUN python -m pip install --upgrade pip wheel build \
 && python -m pip wheel --no-deps --wheel-dir /wheels . \
 && python -m pip wheel --wheel-dir /wheels .

# # ---- Final runtime image ----
# FROM python:3.11-slim AS runtime
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     # where your app will look for the SQLite DB (mount a volume here)
#     DB_PATH=/data/movies.db

# create a non-root user
RUN useradd -m appuser
WORKDIR /app

# copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir /wheels/*

# copy the rest of the project (routers, entrypoint, etc.)
COPY app.py ./app.py
COPY router ./router

# expose API port
EXPOSE 8000

# run with uvicorn (adjust workers as needed)
USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

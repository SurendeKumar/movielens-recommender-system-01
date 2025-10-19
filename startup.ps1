
# upgrade pip (safe step inside container)
pip install --upgrade pip
# install the package in editable mode ->includes deps from pyproject.toml 
pip install -e .

# Start FastAPI app with uvicorn
python -m uvicorn app:app --host 0.0.0.0 --port 8000

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BACKEND_URL=http://127.0.0.1:8000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . ./

EXPOSE 7860

CMD ["bash", "-lc", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & exec streamlit run frontend/app.py --server.port 7860 --server.address 0.0.0.0 --server.headless true --server.enableXsrfProtection false --server.enableCORS false --server.maxUploadSize 50"]
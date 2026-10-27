FROM python:3.12-slim

WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# only what the service needs at runtime
COPY app/ app/
COPY static/ static/
COPY modelfiles/ modelfiles/
COPY seed/ seed/
COPY docs/user_guide.md docs/user_guide.md

# the database lives in a volume; the model server runs outside the container (Ollama on the host by default)
ENV INVOICE_DB_PATH=/service/data/invoices.db \
    LLM_BASE_URL=http://host.docker.internal:11434/v1
VOLUME /service/data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"
CMD ["python", "-m", "uvicorn", "api:app", "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]

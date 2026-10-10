FROM python:3.12-slim

WORKDIR /app


# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY tests /app/tests

# Copy transcript corpus for ingestion on startup
COPY data /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

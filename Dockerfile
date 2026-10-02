FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend /app/backend
COPY analytics /app/analytics
COPY database /app/database
COPY data /app/data

# Environment configuration
ENV MONGODB_URI=mongodb://localhost:27017
ENV MONGODB_DB_NAME=stratos
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

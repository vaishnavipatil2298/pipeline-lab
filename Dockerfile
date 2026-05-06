# Use a slim Python base to keep the image small.
FROM python:3.11-slim

# Set working directory inside the container.
WORKDIR /app

# Install dependencies first (this layer caches as long as requirements.txt doesn't change).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY app ./app

# FastAPI listens on 8000 by default.
EXPOSE 8000

# Run with uvicorn. Use 0.0.0.0 so the container is reachable from outside.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

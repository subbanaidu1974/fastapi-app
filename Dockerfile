# Use official Python slim image
FROM python:3.11-slim

# Set working dir inside container
WORKDIR /app

# Copy requirements first for caching
COPY app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app/ .

# Expose port
EXPOSE 8000

# Run the app with reload for dev (use uvicorn for production without reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

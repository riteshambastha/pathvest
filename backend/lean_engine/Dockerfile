# LEAN Backtest Engine Docker Container
# Python 3.12 base with LEAN dependencies

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ../requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy LEAN engine code
COPY . /app/lean_engine/

# Copy backend app (for schemas)
COPY ../app /app/app/

# Set Python path
ENV PYTHONPATH=/app:/app/lean_engine:$PYTHONPATH

# Create directories for data and results
RUN mkdir -p /app/lean_engine/data \
    /app/lean_engine/results \
    /app/lean_engine/cache

# Volume mounts for data persistence
VOLUME ["/app/lean_engine/data", "/app/lean_engine/results"]

# Expose port for API (if running API in container)
EXPOSE 8000

# Default command (can be overridden)
CMD ["python", "-m", "lean_engine.worker.backtest_worker"]


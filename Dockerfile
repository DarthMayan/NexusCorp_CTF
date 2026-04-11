FROM python:3.12-slim

LABEL maintainer="UPMX Ethical Hacking Team"
LABEL description="NEXUS Corp CTF Platform"

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite databases
RUN mkdir -p /app/data

# Environment
ENV FLASK_APP=app/main.py
ENV SECRET_KEY=change_me_in_production
ENV RATE_LIMIT=120
ENV RATE_WINDOW=60

# Initialize databases on build
RUN python -c "import sys; sys.path.insert(0,'.'); from app.main import init_databases; init_databases()"

EXPOSE 5000

# Run with Gunicorn for production
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.main:app"]

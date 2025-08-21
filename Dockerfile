FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy code (flat layout)
COPY core.py cli.py __init__.py /app/

# Default working directory for mounted files and ignore file discovery
WORKDIR /work

# Ensure our code is importable when running by module or path
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "/app/cli.py"]

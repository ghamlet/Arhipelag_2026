# syntax=docker.io/docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /drone_vision

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models models
COPY scripts scripts

CMD ["python", "scripts/main.py"]

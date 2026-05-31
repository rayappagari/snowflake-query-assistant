FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend /app/frontend/dist ./frontend/dist
EXPOSE 8000
# 2 workers: enough for concurrency on Railway Hobby plan.
# For shared rate-limit/cache state across workers, add Redis and increase workers.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2

FROM node:20-alpine AS web-build
WORKDIR /app/web-ui
COPY web-ui/package.json web-ui/package-lock.json ./
RUN npm ci
COPY web-ui/index.html web-ui/tsconfig.json web-ui/tsconfig.node.json web-ui/vite.config.ts ./
COPY web-ui/src ./src
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY python ./python
RUN pip install --no-cache-dir ./python
COPY --from=web-build /app/web-ui/dist ./web-ui/dist
ENV PYTHONUNBUFFERED=1 MOVIE_AGENT_ROOT=/app WEB_UI_DIST_DIR=/app/web-ui/dist
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["uvicorn", "movie_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]

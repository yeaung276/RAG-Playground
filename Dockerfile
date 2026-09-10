# ---- stage 1: build the admin console (and widget.js, same build) ----
FROM node:20-slim AS admin-builder
WORKDIR /build

COPY admin/package.json admin/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY admin/ .
RUN yarn build


# ---- stage 2: runtime ----
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/
COPY --from=admin-builder /build/dist ./admin/dist

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "--frozen", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]

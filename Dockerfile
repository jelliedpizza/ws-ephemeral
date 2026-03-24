FROM python:3.11-alpine

# Install uv for blazingly fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies (uses uv.lock for deterministic builds)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY src ./src

# Switch to non-root user
RUN chown -R appuser:appgroup /app
USER appuser

# Run the async orchestration loop
CMD ["uv", "run", "python", "src/app.py"]

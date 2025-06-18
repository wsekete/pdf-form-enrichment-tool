# Multi-stage build for PDF Form Enrichment Tool
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r pdfuser && useradd -r -g pdfuser pdfuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Copy application code
COPY pdf_form_editor/ ./pdf_form_editor/
COPY config/ ./config/
COPY training_data/ ./training_data/
COPY setup.py .
COPY README.md .

# Install the application
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/temp /app/logs /app/output && \
    chown -R pdfuser:pdfuser /app

# Switch to non-root user
USER pdfuser

# Expose MCP server port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import pdf_form_editor; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "pdf_form_editor.mcp_server"]

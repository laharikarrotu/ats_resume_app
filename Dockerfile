# ═══════════════════════════════════════════════════════════
# ATS Resume App — Multi-stage Docker build
# ═══════════════════════════════════════════════════════════
# Supports both DOCX and PDF (LaTeX) resume generation.
# PDF requires texlive — use BUILD_ARG to enable:
#   docker build --build-arg INSTALL_LATEX=true -t ats-resume .
# ═══════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

# Build arg to optionally install LaTeX (adds ~400MB)
ARG INSTALL_LATEX=false

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Conditionally install LaTeX for PDF generation
RUN if [ "$INSTALL_LATEX" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output directory
RUN mkdir -p outputs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

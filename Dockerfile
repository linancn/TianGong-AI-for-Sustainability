# syntax=docker/dockerfile:1.5
#
# Build arguments:
#   INSTALL_NODE=true      # include Node.js 22 for AntV chart workflows
#   INSTALL_PANDOC=true    # include Pandoc + minimal LaTeX for PDF/DOCX export
#   INSTALL_GRID_INTENSITY=true  # install uk-grid-intensity CLI extras
#   INSTALL_CODEX=true     # install the @openai/codex CLI (npm global package)

FROM python:3.12-slim

ARG INSTALL_NODE="false"
ARG INSTALL_PANDOC="false"
ARG INSTALL_GRID_INTENSITY="false"
ARG INSTALL_CODEX="true"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:/workspace/.venv/bin:${PATH}" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    CODEX_HOME="/workspace/.codex"

WORKDIR /workspace

RUN mkdir -p "${CODEX_HOME}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        libffi-dev \
        libssl-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Optional: Node.js 22 for chart verification workflows and Codex CLI
RUN if [ "${INSTALL_NODE}" = "true" ] || [ "${INSTALL_CODEX}" = "true" ]; then \
        set -eux; \
        curl -fsSL https://deb.nodesource.com/setup_22.x | bash -; \
        apt-get update; \
        apt-get install -y --no-install-recommends nodejs; \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Optional: Pandoc + minimal LaTeX for PDF/DOCX export pipelines
RUN if [ "${INSTALL_PANDOC}" = "true" ]; then \
        set -eux; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            pandoc \
            texlive-latex-base; \
        rm -rf /var/lib/apt/lists/*; \
    fi

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY specs ./specs
COPY tasks ./tasks
COPY AGENTS.md AGENTS_CN.md README.md README_CN.md SETUP_GUIDE.md SETUP_GUIDE_CN.md ./
COPY scripts ./scripts

RUN uv sync --frozen --group dev

# Optional: install carbon intensity CLI extras
RUN if [ "${INSTALL_GRID_INTENSITY}" = "true" ]; then \
        uv sync --frozen; \
    fi

# Optional: install the Codex CLI (requires Node.js)
RUN if [ "${INSTALL_CODEX}" = "true" ]; then \
        set -eux; \
        npm install -g @openai/codex; \
        codex --version; \
    fi

ENTRYPOINT ["uv", "run"]
CMD ["tiangong-research", "--help"]

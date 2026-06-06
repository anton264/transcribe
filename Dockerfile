# ── Base image with CUDA support for GPU transcription ────────────────────────
FROM docker.io/pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir flask -r requirements.txt

# ── Application code ────────────────────────────────────────────────────────
COPY . .

# ── Create runtime directories ──────────────────────────────────────────────
RUN mkdir -p uploads outputs cache

# ── Expose the Flask port ────────────────────────────────────────────────────
EXPOSE 5001

# ── Run the app ──────────────────────────────────────────────────────────────
CMD ["python", "app.py"]

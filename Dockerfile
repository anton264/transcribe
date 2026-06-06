# ── Base image with CUDA support for GPU transcription ────────────────────────
FROM docker.io/pytorch/pytorch:2.12.0-cuda13.2-cudnn9-runtime

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

# ── Chromium dependencies for md-to-pdf (Puppeteer) ─────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Tell Puppeteer to use the system Chromium instead of downloading its own
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# Pre-install md-to-pdf globally so npx doesn't re-download each time
RUN npm install -g md-to-pdf

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir flask -r requirements.txt

# ── Application code ────────────────────────────────────────────────────────
COPY . .

# ── Create runtime directories ──────────────────────────────────────────────
RUN mkdir -p uploads outputs cache

# ── Expose the Flask port ────────────────────────────────────────────────────
EXPOSE 5001

# ── Run the app ──────────────────────────────────────────────────────────────
CMD ["python", "app.py"]

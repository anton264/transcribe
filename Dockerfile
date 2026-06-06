# ── Base image with CUDA support for GPU transcription ────────────────────────
FROM docker.io/pytorch/pytorch:2.12.0-cuda13.2-cudnn9-runtime

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    pandoc \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-xetex \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Install Eisvogel pandoc LaTeX template ───────────────────────────────────
RUN mkdir -p /usr/share/pandoc/data/templates \
    && wget -qO /usr/share/pandoc/data/templates/eisvogel.latex \
       https://raw.githubusercontent.com/Wandmalfarbe/pandoc-latex-template/master/eisvogel.tex

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

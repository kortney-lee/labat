# Shania Graphics — Puppeteer-ready Node.js image for Cloud Run
# Renders HTML/CSS templates to PNG/WEBP via headless Chrome.

FROM node:20-slim

# Install Chromium and its system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    ffmpeg \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
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
    && rm -rf /var/lib/apt/lists/*

# Tell Puppeteer to skip downloading Chrome (we use system Chromium)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

# Copy source, assets, and build
COPY tsconfig.json ./
COPY src/ ./src/
COPY assets/ ./assets/
RUN npx tsc

# Keep templates (referenced at runtime), remove TS source
# Use cp -rT to merge contents (tsc already creates dist/templates/ from .ts files)
RUN cp -rT src/templates dist/templates && npm prune --omit=dev && rm -rf src/

# Assets stay at /app/assets/ (referenced by renderHtml.ts via __dirname/../../assets)

EXPOSE 8080

CMD ["node", "dist/index.js"]

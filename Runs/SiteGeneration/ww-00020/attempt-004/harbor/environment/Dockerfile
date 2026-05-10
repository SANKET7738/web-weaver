FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_PATH=/usr/local/lib/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN npm install -g playwright \
    && mkdir -p /ms-playwright \
    && playwright install --with-deps chromium \
    && chmod -R a+rx /ms-playwright

RUN pip3 install --break-system-packages --no-cache-dir \
    beautifulsoup4 \
    playwright

RUN useradd -m -s /bin/bash agent

RUN mkdir -p /app/site /app/prompt /logs/agent /logs/verifier \
    && chown -R agent:agent /app /logs/agent

COPY --chown=agent:agent prompt /app/prompt
RUN chmod -R a+rX /app/prompt

COPY solution_assets /opt/solution
RUN chown -R root:root /opt/solution \
    && chmod -R go-rwx /opt/solution \
    && chmod 700 /opt/solution

COPY grader /opt/grader
RUN chown -R root:root /opt/grader \
    && chmod -R go-rwx /opt/grader \
    && chmod 700 /opt/grader

USER agent
WORKDIR /app

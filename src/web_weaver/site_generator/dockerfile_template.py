from web_weaver.site_generator.task_prompt import DEFAULT_PORT


def render_dockerfile(*, base_image: str) -> str:
    return f"""
FROM {base_image}

RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    python3 \\
    python3-pip \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

ENV NODE_PATH=/usr/local/lib/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN npm install -g @anthropic-ai/claude-code playwright \\
    && mkdir -p /ms-playwright \\
    && playwright install --with-deps chromium \\
    && chmod -R a+rx /ms-playwright

RUN useradd -m -s /bin/bash agent \\
    && mkdir -p /workspace/input /workspace/output/reference_site /workspace/logs /workspace/validation \\
    && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace

COPY --chown=agent:agent concept.json /workspace/input/concept.json
COPY --chown=agent:agent blueprint.json /workspace/input/blueprint.json
COPY --chown=agent:agent design_plan.json /workspace/input/design_plan.json
COPY --chown=agent:agent task.md /workspace/task.md
COPY --chown=agent:agent entrypoint.sh /workspace/entrypoint.sh
COPY --chown=agent:agent sanity_check.py /workspace/sanity_check.py
COPY --chown=agent:agent playwright_check.js /workspace/playwright_check.js

RUN chmod +x /workspace/entrypoint.sh /workspace/sanity_check.py /workspace/playwright_check.js

EXPOSE {DEFAULT_PORT}

ENTRYPOINT ["/workspace/entrypoint.sh"]
""".strip() + "\n"

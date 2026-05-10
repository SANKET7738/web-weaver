from web_weaver.site_generator.task_prompt import DEFAULT_PORT


def render_dockerfile(*, base_image: str) -> str:
    return f"""
FROM {base_image}

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    git \\
    curl \\
    ffmpeg \\
    python3 \\
    && rm -rf /var/lib/apt/lists/*

ENV NODE_PATH=/usr/local/lib/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN npm install -g @anthropic-ai/claude-code playwright \\
    && mkdir -p /ms-playwright \\
    && playwright install --with-deps chromium \\
    && chmod -R a+rx /ms-playwright

RUN useradd -m -s /bin/bash agent \\
    && mkdir -p /workspace/input /workspace/output/reference_site /workspace/logs /workspace/validation/screenshots /workspace/validation/screenrecordings /workspace/harbor /workspace/harbor_template \\
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
COPY --chown=agent:agent capture_screenshots.js /workspace/capture_screenshots.js
COPY --chown=agent:agent capture_screenrecordings.js /workspace/capture_screenrecordings.js
COPY --chown=agent:agent assemble_harbor.py /workspace/assemble_harbor.py
COPY --chown=agent:agent harbor_template /workspace/harbor_template

RUN chmod +x /workspace/entrypoint.sh /workspace/sanity_check.py /workspace/playwright_check.js /workspace/capture_screenshots.js /workspace/capture_screenrecordings.js /workspace/assemble_harbor.py

EXPOSE {DEFAULT_PORT}

ENTRYPOINT ["/workspace/entrypoint.sh"]
""".strip() + "\n"

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

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -s /bin/bash agent \\
    && mkdir -p /workspace/input /workspace/output/reference_site /workspace/logs \\
    && chown -R agent:agent /workspace

USER agent
WORKDIR /workspace

COPY --chown=agent:agent concept.json /workspace/input/concept.json
COPY --chown=agent:agent blueprint.json /workspace/input/blueprint.json
COPY --chown=agent:agent design_plan.json /workspace/input/design_plan.json
COPY --chown=agent:agent task.md /workspace/task.md
COPY --chown=agent:agent entrypoint.sh /workspace/entrypoint.sh

RUN chmod +x /workspace/entrypoint.sh

EXPOSE {DEFAULT_PORT}

ENTRYPOINT ["/workspace/entrypoint.sh"]
""".strip() + "\n"

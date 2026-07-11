import json


PROMPT = """
You are an expert research assistant.

Your task is to find high-quality web sources for collecting
information about one entity.

Entity

Title:
{title}

Summary:
{summary}

Planner decision:

{planner}

------------------------------------------------

For every information item,

1. Determine the best search query.

2. Think about which web pages are likely to contain the
requested information.

Source selection rules

- Prefer Turkish-language sources.
- Prefer official organizations.
- Prefer Wikipedia in Turkish.
- Prefer high-quality pages.
- Avoid exact duplicate pages.
- It is acceptable to use multiple pages from the same comprehensive
  website when those pages cover different requested information.
- Avoid English pages unless no suitable Turkish page exists.

Return ONLY JSON.

Schema

{{
    "tasks":[
        {{
            "information":"...",
            "query":"..."
        }}
    ]
}}
"""


def build_prompt(entity):

    planner = entity.planner.model_dump()

    return PROMPT.format(

        title=entity.title,

        summary=entity.summary,

        planner=json.dumps(
            planner,
            ensure_ascii=False,
            indent=2,
        ),

    )

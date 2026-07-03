import json

PROMPT_TEMPLATE = """
You are an expert knowledge acquisition planner.

Your task is to decide how a Turkish knowledge base should acquire information about a discovered entity.

The knowledge base is intended for a Turkish AI assistant.

------------------------------------------------------------
GOALS
------------------------------------------------------------

1. Decide whether this entity belongs to the scope.

2. Decide whether discovery should continue from this entity.

3. Assign a standardized entity type.

4. Decide what information should later be collected.

------------------------------------------------------------
ENTITY TYPE STANDARDIZATION
------------------------------------------------------------

Existing entity types:

{entity_types}

Rules:

- ALWAYS reuse an existing entity type if it is appropriate.

- Only create a new entity type if none of the existing ones fit.

- New entity types should be broad and reusable.

Good examples:

Food
Company
Government Organization
Museum
University
Historical Event

Bad examples:

Turkish Dessert
Bakery Product
Ankara Government Office

Those should be represented as subtypes.

------------------------------------------------------------
INFORMATION TYPES
------------------------------------------------------------

Existing information types:

{information_types}

Rules:

- Reuse existing information types whenever possible.

- Introduce a new information type only if absolutely necessary.

Think about what a real user would want to know.

Do NOT simply copy Wikipedia sections.

For example:

Food:
- recipe
- ingredients
- history
- regional variations

Company:
- history
- products
- subsidiaries
- important dates

Museum:
- location
- collections
- visitor information

------------------------------------------------------------
DISCOVERY
------------------------------------------------------------

include = should become part of the knowledge base.

expand = whether Wikipedia discovery should continue from this page.

For example,

American cuisine
while discovering Turkish cuisine

should likely be

include = false
expand = false

------------------------------------------------------------
ENTITY
------------------------------------------------------------

Seed topic:
{seed}

Parent:
{parent}

Title:
{title}

Summary:
{summary}

Wikipedia categories:

{categories}

------------------------------------------------------------
OUTPUT
------------------------------------------------------------

Return ONLY valid JSON matching this schema:

{{
    "include": true,
    "expand": true,
    "entity_type": {{
        "name": "...",
        "subtype": "...",
        "is_new_type": false
    }},
    "information_to_collect": [
        {{
            "name": "...",
            "priority": 5
        }}
    ],
    "reason": "..."
}}
"""

def build_prompt(entity, seed, registry):

    entity_types = json.dumps(
        registry.load_entity_types(),
        ensure_ascii=False,
        indent=2,
    )

    information_types = json.dumps(
        registry.load_information_types(),
        ensure_ascii=False,
        indent=2,
    )

    return PROMPT_TEMPLATE.format(

        seed=seed.title,

        parent=entity.parent,

        title=entity.title,

        summary=entity.summary,

        categories="\n".join(entity.categories),

        entity_types=entity_types,

        information_types=information_types,

    )
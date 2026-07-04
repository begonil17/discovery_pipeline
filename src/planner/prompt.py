import json

PROMPT_TEMPLATE = """
You are an expert knowledge acquisition planner.

Your task is to decide how a comprehensive Turkish cultural
knowledge base should acquire information about a discovered entity.

The knowledge base is intended for a Turkish AI assistant.

------------------------------------------------------------
COVERAGE-FIRST PHILOSOPHY
------------------------------------------------------------

Coverage is significantly more important than precision.

Start with these assumptions:

- include = true
- expand = true

Prefer false positives over false negatives.

When uncertain, keep and expand the entity.

An entity does not need to be famous, uniquely Turkish, or directly
about the seed topic. Indirectly related and generic entities often
connect valuable branches of the knowledge graph.

Rejecting an entity permanently removes that branch. Therefore reject
only when the page is clearly unusable or obviously unrelated to
Turkish culture and to the seed topic.

Entities that should usually be included include:

- foods, dishes, desserts, drinks, ingredients and spices
- cooking techniques, kitchen tools and culinary products
- festivals, traditions, holidays, beliefs and folklore
- cities, villages, regions, rivers, mountains and other places
- plants, flowers, animals, ecology and agricultural topics
- museums, monuments, buildings and architectural styles
- historical figures, events and periods
- ethnic groups, religions and communities
- sports, clubs, stadiums and organizations
- schools, universities and educational topics
- folk dances, instruments, artists, writers, poems and books
- crafts, clothing, textiles, mythology and transportation

Do not reject an entity merely because its title sounds generic.

------------------------------------------------------------
INCLUDE AND EXPAND POLICY
------------------------------------------------------------

Set include = false only for pages that are clearly unusable, such as:

- maintenance or administration pages
- categories, templates, files, portals or project pages
- help, user or discussion pages
- pure navigation lists with no useful subject matter
- disambiguation pages
- pages that are clearly unrelated to Turkish culture and the seed

Set expand = false only for the same clearly unusable cases.

Otherwise prefer expand = true, especially for:

- foods and ingredients
- cities, villages and regions
- plants, animals and geographical entities
- architecture, museums and monuments
- historical events, periods and people
- organizations, traditions, sports and educational topics

A page may be worth expanding even when it is only indirectly related
to the seed, because it can lead to more specific Turkish entities.

------------------------------------------------------------
ENTITY TYPE STANDARDIZATION
------------------------------------------------------------

Existing entity types:

{entity_types}

Rules:

- Reuse an existing entity type whenever it fits.
- Create a new type when needed to represent a useful entity.
- New entity types must be broad and reusable.
- Put narrow distinctions in subtype rather than creating overly
  specific entity types.

------------------------------------------------------------
INFORMATION TYPES
------------------------------------------------------------

Existing information types:

{information_types}

Rules:

- Reuse existing information types whenever possible.
- Add a new reusable information type when existing types do not cover
  useful information.
- Request all information that would make this entity useful in a
  Turkish knowledge base.
- Be comprehensive, but include only information applicable to the
  entity.
- Do not simply copy Wikipedia section headings.

Consider these information types whenever applicable:

- overview
- origin
- etymology
- history
- historical development
- timeline and important dates
- ingredients, recipe and preparation
- characteristics and classifications
- usage and products
- cultural significance
- regional variations
- geography and location
- ecology
- architecture
- notable examples
- notable people
- related traditions
- organization, responsibilities and services
- collections and visitor information

For included entities, return multiple complementary information items
when appropriate instead of requesting only a minimal description.

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
        "subtype": "..."
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

import json

PROMPT_TEMPLATE = """
You are an expert knowledge acquisition planner.

Your task is to decide how a comprehensive knowledge graph rooted at
the current seed should acquire information about a discovered entity.

The architecture has already discovered this entity from Wikipedia
links. Your job is to decide whether keeping it helps expand the graph
rooted at the seed topic.

------------------------------------------------------------
COVERAGE-FIRST PHILOSOPHY
------------------------------------------------------------

Coverage is significantly more important than precision.

Start with these assumptions:

- include = true
- expand = true

Prefer false positives over false negatives.

When uncertain, keep and expand the entity.

However, every decision must be relative to the ROOT SEED.

Always ask:

"Does this help expand the knowledge graph rooted at the seed topic?"

Do NOT ask:

"Could a Turkish user search for this?"

An entity does not need to be famous or directly about the seed topic.
Indirectly related and generic connector entities often lead to
valuable branches of the graph.

Rejecting an entity permanently removes that branch. Therefore reject
only when the page is clearly unusable or clearly outside the semantic
scope of the root seed.

For example, if the seed is "Türk mutfağı", usually include:

- foods, dishes, desserts, drinks, ingredients and spices
- cooking techniques, kitchen tools and culinary products
- Turkish, Ottoman and regional cuisines
- cities, villages and regions strongly connected to cuisine
- restaurants, chefs, food writers and culinary institutions
- agricultural products, plants, animals and geography relevant to food
- food festivals, traditions, rituals and culinary history

For the same seed, usually reject:

- unrelated foreign cuisines
- unrelated countries and cities
- unrelated sports, celebrities, companies or cultural topics

unless the page primarily discusses Turkish cuisine or is a strong
connector to Turkish cuisine.

If the seed is "Türk müziği", usually include instruments, musicians,
genres, albums, composers, festivals and theory related to Turkish
music, while rejecting unrelated foreign genres, artists and cultures.

Apply the same root-seed reasoning for every seed.

Do not reject an entity merely because its title sounds generic.
Generic entities can be useful connectors when their summary, parent,
categories or title show a plausible relationship to the seed.

------------------------------------------------------------
INCLUDE AND EXPAND POLICY
------------------------------------------------------------

Set include = false only for pages that are clearly unusable, such as:

- maintenance or administration pages
- categories, templates, files, portals or project pages
- help, user or discussion pages
- pure navigation lists with no useful subject matter
- disambiguation pages
- pages that are clearly outside the semantic scope of the root seed

Set expand = false only for the same clearly unusable cases.

Otherwise prefer expand = true, especially for:

- direct examples of the seed topic
- subtopics, traditions, people, organizations and places connected to
  the seed
- generic connector topics that are likely to lead to more specific
  seed-relevant entities
- cities, villages, regions, plants, animals and geographical entities
  when they are plausibly connected to the seed
- architecture, museums, monuments, historical events, periods, people,
  sports or educational topics when they are seed-relevant

A page may be worth expanding even when it is only indirectly related
to the seed, because it can lead to more specific seed-relevant
entities.

Global or foreign entities should be included only when the page is
primarily about the seed domain or is a strong connector into the seed
domain. Otherwise reject them, even if they are globally important.

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
  knowledge graph rooted at the seed.
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

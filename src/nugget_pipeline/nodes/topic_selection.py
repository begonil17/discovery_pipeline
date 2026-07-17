import json
from src.nugget_pipeline.config import OUTPUT_DIR, TOPIC_SELECTION_MODEL
from src.nugget_pipeline.llm.client import generate_json
from src.nugget_pipeline.schemas import TopicCandidate

TOPIC_SELECTION_DIR = OUTPUT_DIR / "topic_selection"

TOPIC_SELECTION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def topic_selection_node(state):
    print("Starting topic selection...")

    categories = state.get("categories", [])
    articles_per_focus = state.get("articles_per_focus", 2)
    extra_articles_per_category = state.get("extra_articles_per_category", 2)

    max_categories = state.get("max_categories")

    if max_categories:
        categories = categories[:max_categories]

    if not categories:
        raise ValueError("No categories provided. Please define config/categories.json.")

    prompt = f"""
        You are helping build a Turkish QA dataset for an AI assistant.

        You are given main categories. Each category contains focus points.
        A focus point should be treated as a real subtopic, not just loose guidance.

        Categories:
        {json.dumps(categories, ensure_ascii=False, indent=2)}

        For each category:
        - For each focus point, generate exactly {articles_per_focus} useful English Wikipedia article titles.
        - Then generate exactly {extra_articles_per_category} extra category-level article titles that naturally extend the whole category.

        Rules:
        - Focus points are subtopics under the main category.
        - Each focus point must receive its own article candidates.
        - A selected article title should be relevant to its specific focus point.
        - Extra category-level articles should connect to the overall category, not random topics.
        - Prefer mid-level useful topics: not too broad, not too obscure.
        - Prefer stable, factual, non-controversial English Wikipedia pages.
        - Do not duplicate article titles within or across categories.
        - Avoid the listed avoid topics for each category.
        - Avoid controversial politics, religion debates, war/conflict topics, conspiracy theories, adult content, illegal activities, and sensitive medical/legal/financial advice.

        Coverage score guidelines:
        10: Highly useful and directly covers the focus point or category.
        7-9: Important and relevant article.
        4-6: Useful supporting article.
        1-3: Too narrow or weakly relevant.

        For every article title, return:
        - title
        - source_type: "focus" or "category_extra"
        - focus_point: the focus point if source_type is "focus", otherwise null
        - coverage_score
        - reason

        Return ONLY valid JSON.

        Format:

        {{
        "Food and cooking": [
            {{
            "title": "Turkish cuisine",
            "source_type": "focus",
            "focus_point": "Turkish home cooking",
            "coverage_score": 10,
            "reason": "Directly covers Turkish home cooking and food culture."
            }},
            {{
            "title": "Cooking",
            "source_type": "category_extra",
            "focus_point": null,
            "coverage_score": 8,
            "reason": "Adds broad useful knowledge about food preparation."
            }}
        ]
        }}
        """

    topics_by_category = generate_json(
        prompt=prompt,
        model_name=TOPIC_SELECTION_MODEL,
    )

    validated_topics = {}

    for category, candidates in topics_by_category.items():
        validated_topics[category] = [
            TopicCandidate(**candidate)
            for candidate in candidates
        ]

    all_topics = []
    seen = set()

    for category_topics in validated_topics.values():
        for candidate in category_topics:
            title = candidate.title.strip()
            key = title.lower()

            if title and key not in seen:
                seen.add(key)
                all_topics.append(title)

    print(f"Finished topic selection. Selected {len(all_topics)} topics.")

    output_path = (
    TOPIC_SELECTION_DIR /
    "selected_topics.json"
)

    output_path.write_text(
        json.dumps(
            {
                category: [
                    candidate.model_dump()
                    for candidate in candidates
                ]
                for category, candidates
                in validated_topics.items()
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "topics_by_category": {
            category: [
                candidate.model_dump()
                for candidate in candidates
            ]
            for category, candidates in validated_topics.items()
        },
        "topics": all_topics,
    }




from dotenv import load_dotenv
import os

from src.config.settings import (
    SEARCH_MODEL,
)

from src.llm.client import LLMClient

from src.search.prompt import build_prompt

from src.search.schemas import SearchPlan, SearchResult

from tavily import TavilyClient

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def search_node(state):

    client = LLMClient()
    
    tavily = TavilyClient(
        api_key=os.getenv(TAVILY_API_KEY)
    )

    entities = state["discovered_entities"][:3]

    planned = []

    for entity in entities:

        print("=" * 80)
        print(entity.title)

        prompt = build_prompt(entity)

        plan = client.generate_structured(
            prompt=prompt,
            model_name=SEARCH_MODEL,
            output_model=SearchPlan,

        )

        print("Generated search queries.")

        for task in plan.tasks:

            print(f"Searching: {task.query}")

            response = tavily.search(
                query=task.query,
                max_results=5,
            )

            task.results = [

                SearchResult(
                    url=result["url"],
                    title=result["title"],
                    reason=f"Tavily score: {result.get('score', 'N/A')}",
                )

                for result in response["results"]

            ]

            print(

                f"Found {len(task.results)} urls."

            )

        entity.search_plan = plan

        planned.append(entity)

    return {

        "discovered_entities": planned

    }

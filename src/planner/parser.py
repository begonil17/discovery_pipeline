import json

from pydantic import ValidationError

from src.planner.schemas import PlannerDecision


class PlannerParser:

    @staticmethod
    def parse(response: str) -> PlannerDecision:

        response = response.strip()

        if response.startswith("```"):

            lines = response.splitlines()

            if lines[0].startswith("```"):
                lines = lines[1:]

            if lines[-1].startswith("```"):
                lines = lines[:-1]

            response = "\n".join(lines)

        return PlannerDecision.model_validate_json(
            response
        )
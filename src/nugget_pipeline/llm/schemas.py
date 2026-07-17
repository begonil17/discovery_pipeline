TOPIC_SELECTION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "category": {"type": "string"},
            "title": {"type": "string"},
            "source_type": {"type": "string"},
            "focus_point": {"type": "string"},
            "coverage_score": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": [
            "category",
            "title",
            "source_type",
            "focus_point",
            "coverage_score",
            "reason",
        ],
    },
}


NUGGET_EXTRACTION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "nugget_id": {"type": "string"},
            "text": {"type": "string"},
            "importance": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": [
            "text",
            "importance",
            "reason",
        ],
    },
}


FACT_VALIDATION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "nugget_id": {"type": "string"},
            "verdict": {"type": "string"},
            "corrected_text": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": [
            "nugget_id",
            "verdict",
            "corrected_text",
            "reason",
        ],
    },
}


STORAGE_DECISION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "nugget_id": {"type": "string"},
            "action": {"type": "string"},
            "final_text": {"type": "string"},
            "detail_level": {"type": "string"},
            "questions_per_nugget": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": [
            "nugget_id",
            "action",
            "final_text",
            "detail_level",
            "questions_per_nugget",
            "reason",
        ],
    },
}


NUGGET_QA_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "nugget_id": {"type": "string"},
            "question": {"type": "string"},
            "answer": {"type": "string"},
        },
        "required": [
            "nugget_id",
            "question",
            "answer",
        ],
    },
}

QUESTION_PARAPHRASE_SCHEMA = {
    "type": "object",
    "properties": {
        "paraphrases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "direct": {
                        "type": "string"
                    },
                    "conversational": {
                        "type": "string"
                    },
                    "indirect": {
                        "type": "string"
                    }
                },
                "required": [
                    "id",
                    "direct",
                    "conversational",
                    "indirect"
                ]
            }
        }
    },
    "required": [
        "paraphrases"
    ]
}


DEDUPE_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "duplicate_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "record_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "record_ids",
                    "reason",
                ],
            },
        },
    },
    "required": [
        "duplicate_groups",
    ],
}




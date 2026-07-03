from pydantic import BaseModel, model_validator


class Document(BaseModel):

    url: str

    title: str

    text: str

    source: str

class CleanedDocument(BaseModel):

    text: str

    @model_validator(mode="before")
    @classmethod
    def accept_text_response(cls, value):

        if isinstance(value, str):

            return {"text": value}

        return value

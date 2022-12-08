import json
from pydantic import BaseModel
from typing import List
from openai.openai_object import OpenAIObject


class GPT3Log(BaseModel):
    """
    A log of the GPT-3 response.
    """

    prompt: str
    response: OpenAIObject


class TicketClassification(BaseModel):
    """
    A classification of a ticket.
    """

    team: str
    rationale: str
    log: GPT3Log


class SearchQueries(BaseModel):
    """
    A list of search queries to run against Yext's documentation.
    """

    search_queries: List[str]
    log: GPT3Log


class UnstructuredGPTResponse(BaseModel):
    """
    A response from GPT-3 that is not structured into JSON or anything.
    """

    response: str
    log: GPT3Log


class DocumentationPreview(BaseModel):
    """
    Search Results from Yext.
    """

    md_preview: str
    search_logs: List[dict]


class TicketTriage(BaseModel):
    classification: TicketClassification
    search_queries: SearchQueries
    checklist_screening: UnstructuredGPTResponse
    documentation_preview: DocumentationPreview
    refined_documentation: UnstructuredGPTResponse

    def __repr__(self):
        return json.dumps(self.dict(), indent=2)

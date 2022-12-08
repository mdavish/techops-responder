import json
from typing import List
from models import (
    GPT3Log,
    TicketClassification,
    SearchQueries,
    UnstructuredGPTResponse,
    DocumentationPreview,
    TicketTriage,
)
from utils import (
    get_gpt3_response,
    create_team_descriptions,
    get_team_checklist,
    get_yext_results,
    generate_markdown_preview_for_search_results,
)


def classify_ticket(ticket_text: str):
    """
    Given the ticket_text, attempt to classify the ticket.
    """
    team_descriptions = create_team_descriptions()
    with open("prompts/classify.md") as file:
        prompt_template = file.read()
    prompt = prompt_template.format(
        ticket_text=ticket_text, team_descriptions=team_descriptions
    )
    response = get_gpt3_response(prompt)
    text_response = response["choices"][0]["text"]
    classification = json.loads(text_response)
    log = GPT3Log(prompt=prompt, response=response)
    return TicketClassification(**classification, log=log)


def create_search_queries(ticket_text: str) -> SearchQueries:
    """
    Given the ticket text, create a list of search queries to run against Yext's documentation.
    """
    with open("prompts/search.md") as file:
        prompt_template = file.read()
    prompt = prompt_template.format(ticket_text=ticket_text)
    response = get_gpt3_response(prompt)
    text_response = response["choices"][0]["text"]
    search_queries = json.loads(text_response)
    log = GPT3Log(prompt=prompt, response=response)
    return SearchQueries(**search_queries, log=log)


def screen_checklist(
    ticket_text: str, ticket_classification: TicketClassification
) -> UnstructuredGPTResponse:
    """
    Given the ticket text and the ticket classification, screen the checklist for the ticket.
    (Remember, this prompt does not return JSON, just text).
    """
    checklist = get_team_checklist(ticket_classification.team)
    with open("prompts/checklist.md") as file:
        prompt_template = file.read()
    prompt = prompt_template.format(
        ticket_text=ticket_text, checklist=checklist, team=ticket_classification.team
    )
    response = get_gpt3_response(prompt)
    screening = response["choices"][0]["text"]
    log = GPT3Log(prompt=prompt, response=response)
    return UnstructuredGPTResponse(response=screening, log=log)


def get_documentation(
    search_queries: List[str], max_results_per_query=3
) -> DocumentationPreview:
    """
    Given the search queries, return a markdown preview of the most relevant documentation.
    """
    all_results = []
    all_responses = []
    for query in search_queries:
        results = get_yext_results(query)
        all_results.extend(results["response"]["results"][:max_results_per_query])
        all_responses.append(results)

    markdown_preview = generate_markdown_preview_for_search_results(all_results)
    documentation_preview = DocumentationPreview(
        md_preview=markdown_preview, search_logs=all_responses
    )
    return documentation_preview


def refine_documentation(
    ticket_text: str,
    documentation_preview: DocumentationPreview,
) -> UnstructuredGPTResponse:
    """
    Refines the relevant articles down to a smaller list so that 1) it fits within the token limit
    and 2) we don't overwhelm the user with too many links.
    """
    with open("prompts/refine.md") as file:
        prompt_template = file.read()
    prompt = prompt_template.format(
        documentation_preview=documentation_preview.md_preview,
        ticket_text=ticket_text,
    )
    response = get_gpt3_response(prompt)
    text_response = response["choices"][0]["text"]
    log = GPT3Log(prompt=prompt, response=response)
    return UnstructuredGPTResponse(response=text_response, log=log)


def generate_response(
    ticket_text: str,
    classification: TicketClassification,
    refined_documentation: UnstructuredGPTResponse,
    checklist_screening: UnstructuredGPTResponse,
) -> UnstructuredGPTResponse:
    """
    Given the ticket text, classification, results preview, and checklist screening, generate a
    response to the user.
    """
    with open("prompts/response.md") as file:
        prompt_template = file.read()
    checklist = get_team_checklist(classification.team)
    prompt = prompt_template.format(
        ticket_text=ticket_text,
        checklist=checklist,
        team=classification.team,
        refined_documentation=refined_documentation.response,
        screening=checklist_screening.response,
    )
    # Delete newlines to save space
    prompt = prompt.replace("\n", " ")
    response = get_gpt3_response(prompt)
    text_response = response["choices"][0]["text"]
    log = GPT3Log(prompt=prompt, response=response)
    return UnstructuredGPTResponse(response=text_response, log=log)


def triage_ticket(ticket_text: str) -> TicketTriage:
    """
    Triage the ticket end-to-end. This chains together all of the functions above.
    """
    classification = classify_ticket(ticket_text)
    search_queries = create_search_queries(ticket_text)
    checklist_screening = screen_checklist(ticket_text, classification)
    documentation_preview = get_documentation(search_queries.search_queries)
    refined_documentation = refine_documentation(ticket_text, documentation_preview)
    response = generate_response(
        ticket_text,
        classification,
        refined_documentation,
        checklist_screening,
    )
    return TicketTriage(
        classification=classification,
        search_queries=search_queries,
        checklist_screening=checklist_screening,
        documentation_preview=documentation_preview,
        refined_documentation=refined_documentation,
        response=response,
    )

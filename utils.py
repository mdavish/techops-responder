import re
import os
from typing import Dict, Union, List
import streamlit as st
import openai
from yext import YextClient
from rich.console import Console

console = Console()


def get_preview(text: str, n_char=250):
    """
    Generate a preview of a large text field that does the following:
    - Is no more than n_char characters long
    - Removes markdown headers and other formatting
    - Replaces newline characters with the | character
    """
    text = text.replace("#", "")
    # Replace any number of newlines with a single |
    text = re.sub(r"\n+", " | ", text)
    # Replace links and URLs
    text = re.sub(r"\[.*\]\(.*\)", "", text)
    if len(text) > n_char:
        text = text[:n_char].rsplit(" ", 1)[0] + "..."
    return text


@st.experimental_memo()
def get_gpt3_response(prompt: str, max_tokens=512, **kwargs):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.Completion.create(
        prompt=prompt,
        max_tokens=max_tokens,
        engine="text-davinci-003",
        top_p=1,
        temperature=0.7,
        **kwargs,
    )
    return response


@st.experimental_memo()
def get_yext_results(query: str) -> dict:
    client = YextClient("01db1d1e5ebbaa7ea2e6807ad2196ab3")
    # This is to fix a bug where the Yext client is accidentally hitting Answers universal
    # when you call search_answers_vertical()
    client.ANSWERS_ENDPOINTS["PRODUCTION"][
        "answers_universal"
    ] = "https://liveapi.yext.com/v2/accounts/me/answers/vertical/query"

    results = client.search_answers_vertical(
        query=query,
        vertical_key="everything",
        experience_key="yext-help-hh-react",
    )
    return results


def get_body_field(result: dict):
    data = result["data"]
    default_body_field = "body"
    get_body_field_by_type: Dict[Union[dict, callable]] = {
        "discourse_discourseTopic": lambda x: (
            x["discourse_answerAccepted"]["text"]
            if "discourse_answerAccepted" in x
            else x["discourse_firstDiscoursePost"]["text"]
        ),
        "ce_hHUnit": "body",
        "ce_hhGuide": "shortDescription",
        "ce_referenceDoc": "body",
        "ce_blog": "description",
        "helpArticle": "body",
    }
    assert "type" in data, "Result does not have a type field"
    if data["type"] in get_body_field_by_type:
        body_field = get_body_field_by_type[data["type"]]
        if callable(body_field):
            return body_field(data)
        else:
            return data[body_field]
    else:
        try:
            return data[default_body_field]
        except KeyError:
            console.log(
                f"Result type {data['type']} does not have a body field and no default body field was found",
                style="red",
            )
            return ""


def get_url_field(result: dict):
    data = result["data"]
    default_url_field = "url"
    url_fields_by_type: Dict[Union[dict, callable]] = {
        "ce_hHUnit": "website",
        "ce_hhGuide": "landingPageUrl",
        "discourse_discourseTopic": lambda result: f"https://hitchhikers.yext.com/community/t/{data['discourse_slug']}",
        "ce_referenceDoc": "landingPageUrl",
        "ce_blog": "landingPageUrl",
    }
    assert "type" in data, "Result does not have a type field"
    if data["type"] in url_fields_by_type:
        url_field = url_fields_by_type[data["type"]]
        if callable(url_field):
            return url_field(result)
        else:
            return data[url_field]
    else:
        try:
            return data[default_url_field]
        except KeyError:
            console.log(
                f"Result type {data['type']} does not have a url field and no default url field was found",
                style="red",
            )
            return ""


def generate_markdown_preview_for_search_results(all_results: List[dict]):
    """
    Generate a markdown preview of the search results for the user AND GPT-3 to look at.
    """
    markdown = ""
    for i, result in enumerate(all_results):
        data = result["data"]
        body = get_body_field(result)
        url = get_url_field(result)
        markdown += f"""
        ##### {i+1}. [{data['name']}]({url})
        {get_preview(body)}
        """
    return markdown


def get_team_checklist(team: str):
    """
    Load the relevant team's checklist from the team_checklists/ folder
    If the team is not found, return an appropriate error message
    """
    with open(f"team_checklists/{team.lower()}.md", "r") as f:
        return f.read()


def create_team_descriptions():
    """
    Reads individual files from the team_descriptions/ folder and creates a text blob of the form
    1. **Team Name:** Team Description
    etc.
    """
    team_descriptions = ""
    for i, team in enumerate(os.listdir("team_descriptions"), 1):
        with open(f"team_descriptions/{team}", "r") as f:
            team_descriptions += f"{i}. **{team[:-3].title()}:** {f.read()}\n"
    return team_descriptions

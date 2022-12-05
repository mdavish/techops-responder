import json
import streamlit as st
from utils import (
    get_gpt3_response,
    get_yext_results,
    generate_markdown_preview_for_search_results,
    get_team_checklist,
)


MAX_RESULTS = 3

default_ticket = """
Hi Team,

*Priority:* Normal, issue is not on production as this experience is not live yet

*KG*: https://www.yext.com/s/1410208

*Search Experience*: https://www.yext.com/s/1410208/search/experiences/configuration/answers-locator/testSearch (Not live yet)

*Incorrect Behavior:* Searching for "open now [[city]], [[state]]" yields different results than searching for "[[city]], [[state]] open now" for some sample searches. It seems like when the query leads with "Open Now" the NLP Location Filter does not trigger vs when it's at the end.

*Expected Behavior:* Same result set agnostic of query order

New York, NY (username = test, password = tupss6060!)

"open now new york, ny" has 10 results at time of query not specific

https://www.yext.com/s/1410208/search/experiences/answers-locator/searchQueryLogDetails/018463fd-a85d-ac51-b711-7e4005791b4b

"new york, ny open now" has  59 results at time of query (desired result set)

https://www.yext.com/s/1410208/search/experiences/answers-locator/searchQueryLogDetails/018463fe-17d9-2950-a198-015798a6d43b

Arlington, VA

"open now arlington, va" has 9 results at time of query

"arlington, va open now" has 23 results at time of query (desired result set)

**Troubleshooting Steps: **

Confirmed City wasn't a searchable field

Added "Open Now" as custom phrase which didn't help

Please let us know if you have any questions.
"""

classification_prompt_template = """
You are a program whose job is to determine which engineering to route a ticket to. There are three engineering teams:

1. Slapshot: Slapshot deals with problems related to our front-end developer SDKs. If people have questions about our Javascript library, they go to Slapshot.

2. Watson: Watson deals with the core search API. If people are confused about why certain search results are showing up, or the order of the results, they go to Watson. 

3. Fusion: Fusion deals with data and Analytics. If people have questions about how our reporting or analytics data, they go to fusion. 

Your job is to take a ticket and decide which team to send it to. Output a response in JSON of the following form:

{{
 "team": "WATSON",
 "rationale": "This question pertains to the search algorithm so it belongs to Watson."
}}

If it's not obvious which team it pertains to, you may say return this response:

{{
 "team": "Unknown"
"rationale": "It's not clear which team this belongs to."
}}

#####
Ticket:
{ticket_text}
#####

"""

search_prompt_template = """
You are a program whose job is to look at support tickets and search for documentation that might be relevant. You will read the support ticket and then compose a search query of our developer documentation to fetch relevant articles. 

A search query should be no more than 5-6 words and should focus on the most relevant keywords of the ticket.

You are allowed to enter multiple search queries if you want, but no more than 3. Usually 1 will suffice.

Return a JSON response of this form:

{{"searchQueries": ["example query"]}}

#### Ticket:
{ticket_text}
####
"""

docs_refinement_template = """
You are a program whose job it is to look at a support ticket and attempt to answer it based on relevant documentation.

In this exercise, you will be presented with a support ticket and a list of between 3 and 10 
relevant documentation articles. 

Your job is ONLY to tell us which article is most relevant to the ticket OR indicate if there is 
no relevant article. 

If there is a relevant article output the index of the most relevant article. 

If there is no relevant article, output -1.

Just output a number, nothing else.

#### Ticket:
{ticket_text}
####

#### Relevant Articles:
{relevant_articles}
####
"""

ticket_checklist_template = """
You are a program whose job it is to look at a support ticket and a checklist of requirements 
and determine whether the ticket meets the requirements. 

For example, a list of requirements might look like:

- The ticket must include a link to the web page in question
- The ticket must include a video recording of the behavior in question

(This is just an example, the real check list will be listed below.)

Your job is to provide an evaluation of whether the ticket meets the requirements. If the ticket
does meet the requirements, explain exactly how so and reference the ticket text. If the ticket does not,
explain exactly why it falls short.

#### Ticket:
{ticket_text}
####

#### Checklist:
{checklist}
####
"""

compose_final_response_template = """
You are a program whose job it is to answer support tickets for Yext. 

You will be presented with a few materials to compose your response:

1. The ticket itself
2. The engineering team that GPT-3 believes the ticket should be routed to
3. A list of potentially relevant documentation articles
4. A checklist of requirements that the ticket must meet for this particular engineering team
5. GPT-3's previous assessment of whether the ticket meets these requirements

Based on these materials, compose a response to the ticket. The response should include the following:

- Send a helpful, friendly greeting from the Yext team
- Provide them a list of the most relevant documentation articles. No more than 4 articles.
- If the ticket does not meet the requirements, inform the user what they need to do to meet the requirements
- If the ticket does meet the requirements, inform the user that the ticket will be routed to the engineering team

#### Ticket:
{ticket_text}
####

#### Engineering Team:
{team}
####

#### Relevant Articles:
{relevant_articles}
####

#### Checklist:
{checklist}
####

#### Previous Assessment:
{assessment}
####
"""

st.title("GPT-3 Techops Triage")
ticket_text = st.text_area(
    "Enter Your Techops Ticket Here", value=default_ticket, height=400
)
generate = st.button("Generate")

if generate:

    if ticket_text:
        with st.spinner("Step 1: Classifying Engineering Team"):
            classification_prompt = classification_prompt_template.format(
                ticket_text=ticket_text
            )
            c_response = get_gpt3_response(classification_prompt)
            try:
                c_text_dict = json.loads(c_response["choices"][0]["text"])
            except json.decoder.JSONDecodeError:
                st.exception("Error: GPT-3 returned invalid JSON")

            st.write("## 1. Classifying Engineering Team")
            st.write(f"**Engineering Team:** {c_text_dict['team']}")
            st.write(f"**Rationale:** {c_text_dict['rationale']}")

            with st.expander("View Classification Details"):
                st.write("### Open AI Response")
                st.write(c_response)
                st.write("### Prompt")
                st.code(classification_prompt)

        with st.spinner("Step 2: Generating Search Queries"):
            search_prompt = search_prompt_template.format(ticket_text=ticket_text)
            s_response = get_gpt3_response(search_prompt)
            try:
                s_text_dict = json.loads(s_response["choices"][0]["text"])
            except json.JSONDecodeError:
                st.exception("Error: GPT-3 returned invalid JSON")

            st.write("## 2. Generating Search Queries")
            st.write(f"**Search Queries:** \n\n")
            st.write(s_text_dict["searchQueries"])

        with st.spinner("Step 3: Searching Yext Docs"):

            st.write("## 3. Relevant Documentation")

            assert s_text_dict["searchQueries"], "No search queries were generated"
            all_results = []
            all_responses = []
            for query in s_text_dict["searchQueries"]:
                results = get_yext_results(query)
                all_results.extend(results["response"]["results"][:MAX_RESULTS])
                all_responses.append(results)

            markdown_preview = generate_markdown_preview_for_search_results(all_results)
            st.markdown(markdown_preview)

            with st.expander("View Search Details"):
                st.write("### Open AI Response")
                st.write(s_response)
                st.write("### Prompt")
                st.code(search_prompt)

            for query, response in zip(s_text_dict["searchQueries"], all_responses):
                with st.expander(f'Search Results: `"{query}"`'):
                    st.json(results)

        with st.spinner("Step 4: Refining Search Results"):
            docs_refinement_prompt = docs_refinement_template.format(
                ticket_text=ticket_text, relevant_articles=markdown_preview
            )
            d_response = get_gpt3_response(docs_refinement_prompt)

            st.write("## 4. Refining Search Results")
            best_choice_index = d_response["choices"][0]["text"]
            try:
                best_choice_index = int(best_choice_index)
            except ValueError:
                st.exception("Error: GPT-3 returned an invalid number.")
            if best_choice_index == -1:
                st.write("No relevant article")
            else:
                st.write("#### Most Relevant Article:")
                preview = generate_markdown_preview_for_search_results(
                    [all_results[best_choice_index]]
                )
                st.write(preview)

            with st.expander("View Refinement Details"):
                st.write("### Open AI Response")
                st.write(d_response)
                st.write("### Prompt")
                st.code(docs_refinement_prompt)

        with st.spinner("Step 5: Checking Ticket Against Checklist"):
            team_checklist = get_team_checklist(c_text_dict["team"])
            ticket_checklist_prompt = ticket_checklist_template.format(
                ticket_text=ticket_text, checklist=team_checklist
            )
            t_response = get_gpt3_response(ticket_checklist_prompt)

            st.write("## 5. Checking Ticket Against Checklist")
            checklist_results = t_response["choices"][0]["text"]
            st.write(checklist_results)

            with st.expander("View Checklist Details"):
                st.write("### Open AI Response")
                st.write(t_response)
                st.write("### Prompt")
                st.code(ticket_checklist_prompt)

        with st.spinner("Step 6: Composing Final Response"):
            final_response_prompt = compose_final_response_template.format(
                ticket_text=ticket_text,
                team=c_text_dict["team"],
                relevant_articles=markdown_preview,
                checklist=team_checklist,
                assessment=checklist_results,
            )
            f_response = get_gpt3_response(final_response_prompt, max_tokens=1000)

            st.write("## 6. Composing Final Response")
            final_response = f_response["choices"][0]["text"]
            st.write(final_response)

            with st.expander("View Final Response Details"):
                st.write("### Open AI Response")
                st.write(f_response)
                st.write("### Prompt")
                st.code(final_response_prompt)

import streamlit as st
from triage import (
    classify_ticket,
    create_search_queries,
    screen_checklist,
    get_documentation,
    refine_documentation,
    generate_response,
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

st.title("GPT-3 Techops Triage")
ticket_text = st.text_area(
    "Enter Your Techops Ticket Here", value=default_ticket, height=400
)
generate = st.button("Generate")

if generate:

    if ticket_text:
        with st.spinner("Step 1: Classifying Engineering Team"):
            ticket_classification = classify_ticket(ticket_text)
            st.write("## 1. Classifying Engineering Team")
            st.write(f"**Engineering Team:** {ticket_classification.team}")
            st.write(f"**Rationale:** {ticket_classification.rationale}")
            with st.expander("Debug This Step"):
                st.write(ticket_classification.dict())

        with st.spinner("Step 2: Generating Search Queries"):
            search_queries = create_search_queries(ticket_text)
            st.write("## 2. Generating Search Queries")
            st.write(f"**Search Queries:** \n\n")
            st.write(search_queries.search_queries)
            with st.expander("Debug This Step"):
                st.write(search_queries.dict())

        with st.spinner("Step 3: Searching Yext Docs"):
            documentation_preview = get_documentation(search_queries.search_queries)
            st.write("## 3. Relevant Documentation")
            st.markdown(documentation_preview.md_preview)
            with st.expander("Debug This Step"):
                st.write(documentation_preview.dict())

        with st.spinner("Step 3.5: Refining Documentation"):
            refined_docs = refine_documentation(ticket_text, documentation_preview)
            st.write("## 3.5. Refining Documentation")
            st.markdown(refined_docs.response)
            with st.expander("Debug This Step"):
                st.write(refined_docs.dict())

        with st.spinner("Step 4: Checking Ticket Against Checklist"):
            checklist_results = screen_checklist(ticket_text, ticket_classification)
            st.write("## 4. Checking Ticket Against Checklist")
            st.write(checklist_results.response)

            with st.expander("Debug This Step"):
                st.write(checklist_results.dict())

        with st.spinner("Step 5: Composing Final Response"):
            final_response = generate_response(
                ticket_text,
                ticket_classification,
                refined_docs,
                checklist_results,
            )
            st.write("## 5. Composing Final Response")
            st.write(final_response.response)

            with st.expander("View Final Prompt"):
                st.write("### Final Promppt")
                st.write(final_response.log.prompt)

            with st.expander("Debug This Step"):
                st.write(final_response.dict())

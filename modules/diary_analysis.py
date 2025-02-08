import statistics
from datetime import datetime

import fasthtml.common as fh
import fasthtml.components as fh_components
from openai import OpenAI
from pymongo.collection import Collection

import js_css_loader
import structured_output_schemas.diary_prompt as diary_prompt
import structured_output_schemas.diary_responses as diary_responses


def category_analysis(
    text: str,
    happiness_score: int,
    openai_client: OpenAI,
    session: dict,
    users_collection: Collection,
):
    """Displays the scores/info for various categories, given a submitted diary entry.

    Args:
        text (str): User submitted entry
        happiness_score (int): User submitted happiness

    Returns:
        fh.FT: HTML components in the form of a franken ui accordion: https://next.franken-ui.dev/docs/2.0/accordion
    """
    scores = []

    def _make_accordian_title(title: str) -> fh.FT:
        return (
            fh.A(cls="uk-accordion-title", href=True)(
                title,
                fh.Span(cls="uk-accordion-icon")(
                    fh_components.Uk_icon(icon="chevron-down"),
                ),
            ),
        )

    def _make_accordian_content(explaination: str, suggestions: list[str]) -> fh.FT:
        # uk-list-hyphen is a filled hyphen marker: https://next.franken-ui.dev/docs/2.0/list
        return (
            fh.Div(cls="uk-accordion-content")(
                fh.P(f"Explaination: {explaination}"),
                fh.P("Suggestions:"),
                fh.Ul(cls="uk-list uk-list-hyphen")(
                    *[fh.Li(suggestion) for suggestion in suggestions]
                ),
            ),
        )

    socialization_score_response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_responses.socialization_system_prompt,
            },
            {
                "role": "user",
                "content": f"This is my dairy, tell me how well I socialized today:\n<diary-entry>\n{text}\n</dairy-entry>",
            },
        ],
        response_format=diary_responses.SocializationScore,
    )
    socialization_accordion_element = fh.Li(cls="uk-open")(
        _make_accordian_title(
            f"Socialization Score: {socialization_score_response.choices[0].message.parsed.score}"
        ),
        _make_accordian_content(
            socialization_score_response.choices[0].message.parsed.reason,
            socialization_score_response.choices[
                0
            ].message.parsed.improvement_suggestions,
        ),
    )
    scores.append(socialization_score_response.choices[0].message.parsed.score)

    productivity_score_response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_responses.productivity_system_prompt,
            },
            {
                "role": "user",
                "content": f"This is my dairy, tell me how well productive I was today:\n<diary-entry>\n{text}\n</dairy-entry>",
            },
        ],
        response_format=diary_responses.ProductivityScore,
    )
    productivity_accordion_element = fh.Li(cls="uk-open")(
        _make_accordian_title(
            f"Productivity Score: {productivity_score_response.choices[0].message.parsed.score}"
        ),
        _make_accordian_content(
            productivity_score_response.choices[0].message.parsed.reason,
            productivity_score_response.choices[
                0
            ].message.parsed.improvement_suggestions,
        ),
    )

    scores.append(productivity_score_response.choices[0].message.parsed.score)

    fulfillment_score_response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_responses.fulfillment_system_prompt,
            },
            {
                "role": "user",
                "content": f"This is my dairy, tell me how well I achieved self fulfillment:\n<diary-entry>\n{text}\n</dairy-entry>",
            },
        ],
        response_format=diary_responses.FulfillmentScore,
    )
    fulfillment_accordion_element = fh.Li(cls="uk-open")(
        _make_accordian_title(
            f"Fulfillment Score: {fulfillment_score_response.choices[0].message.parsed.score}"
        ),
        _make_accordian_content(
            fulfillment_score_response.choices[0].message.parsed.reason,
            fulfillment_score_response.choices[
                0
            ].message.parsed.improvement_suggestions,
        ),
    )
    scores.append(fulfillment_score_response.choices[0].message.parsed.score)

    health_score_response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_responses.health_system_prompt,
            },
            {
                "role": "user",
                "content": f"This is my dairy, tell me how healthy I was today:\n<diary-entry>\n{text}\n</dairy-entry>",
            },
        ],
        response_format=diary_responses.HealthScore,
    )
    health_accordion_element = fh.Li(cls="uk-open")(
        _make_accordian_title(
            f"Health Score: {health_score_response.choices[0].message.parsed.score}"
        ),
        _make_accordian_content(
            health_score_response.choices[0].message.parsed.reason,
            health_score_response.choices[0].message.parsed.improvement_suggestions,
        ),
    )
    scores.append(health_score_response.choices[0].message.parsed.score)

    if "user_info" not in session or not session["user_info"].get("email"):
        return fh.P(
            "Error: You must be logged in to submit entries.", style="color: red;"
        )

    # Ensure the `google_id` uniquely identifies the user
    user_id = session["user_info"]["id"]
    user = users_collection.find_one({"google_id": user_id})

    if not user:
        return fh.P("Error: User not found. Please log in again.", style="color: red;")

    # Prepare diary entry for storage
    diary_entry = {
        "text": text,
        "happiness_score": happiness_score,
        "analysis": {
            "socialization": {
                "score": socialization_score_response.choices[0].message.parsed.score,
                "explanation": socialization_score_response.choices[
                    0
                ].message.parsed.reason,
                "suggestions": socialization_score_response.choices[
                    0
                ].message.parsed.improvement_suggestions,
            },
            "productivity": {
                "score": productivity_score_response.choices[0].message.parsed.score,
                "explanation": productivity_score_response.choices[
                    0
                ].message.parsed.reason,
                "suggestions": productivity_score_response.choices[
                    0
                ].message.parsed.improvement_suggestions,
            },
            "fulfillment": {
                "score": fulfillment_score_response.choices[0].message.parsed.score,
                "explanation": fulfillment_score_response.choices[
                    0
                ].message.parsed.reason,
                "suggestions": fulfillment_score_response.choices[
                    0
                ].message.parsed.improvement_suggestions,
            },
            "health": {
                "score": health_score_response.choices[0].message.parsed.score,
                "explanation": health_score_response.choices[0].message.parsed.reason,
                "suggestions": health_score_response.choices[
                    0
                ].message.parsed.improvement_suggestions,
            },
        },
        "created_at": datetime.utcnow(),
    }

    # Store diary entry in MongoDB
    try:
        users_collection.update_one(
            {"google_id": user_id},
            {
                "$push": {"diary_entries": diary_entry},
            },
            upsert=True,
        )
        print(f"✅ Diary entry saved for user {user_id}")
    except Exception as e:
        print(f"🔥 Failed to save diary entry: {e}")
        return fh.P("Error saving diary entry", style="color: red;")

    return fh.Ul(cls="uk-accordion", data_uk_accordion="multiple: true")(
        socialization_accordion_element,
        productivity_accordion_element,
        fulfillment_accordion_element,
        health_accordion_element,
    ), fh.P(f"Average Score: {(statistics.mean(scores))}")


def prompt_user(text: str, openai_client: OpenAI) -> fh.FT:
    diary_prompt_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_prompt.diary_prompt_system_prompt,
            },
            {
                "role": "user",
                "content": f"This is my dairy that is still in progress. Tell me what to improve:\n<diary-entry>\n{text}\n</dairy-entry>",
            },
        ],
    )
    return fh.H2(
        fh.Style(
            js_css_loader.styles["span_inherit_h2.css"]
        ),  # make the spans inherit the h2 style
        fh.Span(
            fh.Span(diary_prompt_response.choices[0].message.content),
            fh.Style(  # css only typewriter effect: https://dev.to/afif/a-scalable-css-only-typewriter-effect-2opn
                # gnat css-scope-inline: https://github.com/gnat/css-scope-inline
                js_css_loader.styles["prompt_user_typewriter.css"]
            ),
        ),
    )

import os
import statistics
from datetime import datetime
from typing import Callable

import fasthtml.common as fh
import fasthtml.components as fh_components
from dotenv import load_dotenv
from openai import OpenAI

import modules.auth as auth
import structured_output_schemas.diary_prompt as diary_prompt
import structured_output_schemas.diary_responses as diary_responses
from modules.auth import Auth
from modules.db import init_db

print("Link: http://localhost:5001")
load_dotenv()

openai_client: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app: fh.FastHTML | fh.FastHTMLWithLiveReload
rt: Callable
app, rt = fh.fast_app(
    live=True,
    pico=False,
    hdrs=(
        # franken ui: https://franken-ui.dev/docs/installation
        fh.Link(
            rel="stylesheet",
            href="https://unpkg.com/franken-ui@2.0.0-internal.38/dist/css/core.min.css",
        ),
        fh.Link(
            rel="stylesheet",
            href="https://unpkg.com/franken-ui@2.0.0-internal.38/dist/css/utilities.min.css",
        ),
        fh.Script(
            src="https://unpkg.com/franken-ui@2.0.0-internal.38/dist/js/core.iife.js",
            type="module",
        ),
        fh.Script(
            src="https://unpkg.com/franken-ui@2.0.0-internal.38/dist/js/icon.iife.js",
            type="module",
        ),
        # notion style: https://github.com/miloxeon/potion/tree/master
        fh.Link(rel="stylesheet", href="styles/notion.css", type="text/css"),
    ),
)

db, users_collection = init_db()
oauth = Auth(app, auth.google_auth_client)
oauth.users_collection = users_collection


@rt("/")
def get(auth, session) -> fh.FT:
    """Default Home Page"""
    is_authenticated = bool(auth and session.get("user_info"))

    diary_entries: list[dict[str, str | datetime | dict[str, str]] | None]
    if is_authenticated:
        user_id = session["user_info"]["id"]
        user = users_collection.find_one(
            {"google_id": user_id}, {"diary_entries": 1, "_id": 0}
        )

        if user and "diary_entries" in user:
            diary_entries = sorted(
                user["diary_entries"],
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )
        else:
            diary_entries = []

    history_items = []
    for entry in diary_entries:
        history_items.append(
            fh.Div(cls="uk-card uk-card-default uk-card-body")(
                fh.H2(f"{entry['created_at'].strftime('%Y-%m-%d %H:%M')}"),
                fh.P(f"User Input: {entry.get('user_input', 'No input stored')}"),
                fh.P(
                    f"Mood Score: {entry.get('happiness_score', 'Pending Analysis')}/10"
                ),
                fh.Details()(
                    fh.Summary("View Analysis Details"),
                    fh.Ul(cls="uk-list uk-list-hyphen")(
                        fh.Li(
                            f"Social Score: {entry['analysis'].get('socialization_score', 'Pending Analysis')}"
                        ),
                        fh.Li(
                            f"Productivity Score: {entry['analysis'].get('productivity_score', 'Pending Analysis')}"
                        ),
                        fh.Li(
                            f"Fulfillment Score: {entry['analysis'].get('fulfillment_score', 'Pending Analysis')}"
                        ),
                        fh.Li(
                            f"Health Score: {entry['analysis'].get('health_score', 'Pending Analysis')}"
                        ),
                    ),
                ),
            )
        )

    return (
        fh.Header()(
            fh.Div(
                style="background-image: url(https://images.unsplash.com/photo-1505533321630-975218a5f66f?fm=jpg&q=60&w=3000&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D)",
                cls="background",
            ),
            fh.Div("✍️", cls="icon"),
            fh.H1(),
            fh.Script(
                "me('h1').textContent = `Today is ${new Date().toLocaleDateString()}`;"
            ),
        ),
        fh.Div(
            fh.A(
                "Login" if not is_authenticated else "Logout",
                href="/login" if not is_authenticated else "/auth/logout",
            ),
        ),
        fh.Main()(
            fh.Div(id="diary-prompt")(fh.H2("Tell me about your day....")),
            fh.Form(hx_post="/submit", hx_target="#data", hx_indicator="#spinner")(
                fh.Style("""
me textarea{width: 100%; height: 70vh; resize: none;}
me textarea:focus {outline: none;}
                        """),
                fh.Script("""
onloadAdd(() => {
    let keystrokeCount = 0;
    me("textarea").on("keydown", ev => {
        let textarea = me(ev); // Get the textarea element
        keystrokeCount++; // Increment the keystroke count
        if (keystrokeCount % 100 === 0 && keystrokeCount >= 200) {
            htmx.ajax("POST", "/diary_prompt", {
                target: "#diary-prompt",
                swap: "innerHTML",
                values: { text: textarea.value }
            }).catch(err => console.warn("Request failed:", err));
        }
    });
});
                        """),
                fh.Textarea(
                    name="text",
                    placeholder="Talk to me.....",
                    hx_post="/diary-prompt",
                    hx_target="dairy-prompt",
                    hx_swap="innerHTML",
                ),
                fh.Div(
                    fh.Label(
                        "Rate Your Happiness:",
                        fh.Input(
                            type="number",
                            name="happiness_score",
                            min="1",
                            max="10",
                            cls="uk-input",
                        ),
                    )
                ),
                fh.Button(cls="uk-btn uk-btn-default")("Submit"),
            ),
            fh.Div(id="spinner", data_uk_spinner=True, cls="htmx-indicator"),
            fh.Div(id="data"),
        ),
        fh.Div(cls="uk-margin-top")(fh.H2("History"), *history_items),
    )


@rt("/submit")
def post(text: str, happiness_score: int, session) -> fh.FT:
    """Displays the scores/info for various categories, given a submitted diary entry.

    Args:
        dairy (DairyEntry): User submitted entry

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
        # uk-list-disc is a filled circle marker: https://next.franken-ui.dev/docs/2.0/list
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
    ), fh.P(f"Average Score: {statistics.mean(scores)}")


@rt("/diary_prompt")
def post(text: str = "") -> fh.FT:
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
            "me h2 span {font: inherit; color: inherit; text-decoration: inherit; }"
        ),  # make the spans inherit the h2 style
        fh.Span(
            fh.Span(diary_prompt_response.choices[0].message.content),
            fh.Style(  # css only typewriter effect: https://dev.to/afif/a-scalable-css-only-typewriter-effect-2opn
                # gnat css-scope-inline: https://github.com/gnat/css-scope-inline
                """
me {
    display:inline-flex;
}
me span {
    word-break: break-all;
    height: 1.5em;
    width:0%;
    overflow: hidden;
    animation:
        c 0.5s infinite steps(1),
        t 1s linear forwards,
        c-hide 0.5s steps(1) 1s forwards; /* hide caret after 2s aka when the typewriter is done */
}
me span:before {
    content:" ";
    display:inline-block;
}
@keyframes t{
    90%,100% {width:100%}
}
@keyframes c{ /* Caret Animation */
    0%,100%{box-shadow:5px 0 0 #0000}
    50%    {box-shadow:5px 0 0 black  }
}

@keyframes c-hide {
    0%, 100% {
        box-shadow: none; /* Caret disappears */
    }
}
"""
            ),
        ),
    )


@rt("/login")
def login(req):
    return auth.login(req, oauth)


@rt("/auth/logout")
def logout(session: dict):
    return auth.logout(session)


fh.serve(host="localhost", port=5001)

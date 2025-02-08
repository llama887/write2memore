from datetime import datetime

import fasthtml.common as fh
from pymongo.collection import Collection

import js_css_loader
from modules.auth import Auth


def homepage(auth: Auth, session, users_collection: Collection):
    is_authenticated = bool(auth and session.get("user_info"))
    if not is_authenticated:
        return (
            fh.H1("Welcome to the Text Editor"),
            fh.A(href="/login")("Login to start"),
    )
        
    user_id = session["user_info"]["id"]

    diary_entries: list[dict[str, str | datetime | dict[str, str]] | None]
    if is_authenticated:
        user_id = session["user_info"]["id"]
        user = users_collection.find_one(
            {"google_id": user_id}, {"diary_entries": 1, "_id": 0}
        )

        if user and "diary_entries" in user:
            diary_entries: list[dict[str, str | datetime | dict[str, str]] | None]  = sorted(
                user["diary_entries"],
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )
        else:
            diary_entries = []
            
    history_entries = sorted(
        diary_entries,  # Do not exclude today's entry
        key=lambda x: x.get("created_at", datetime.min),
        reverse=True
    )

    history_items = []
    for entry in history_entries:
            history_items.append(
                fh.Div(cls="uk-card uk-card-default uk-card-body")(
                    fh.H2(f"{entry['created_at'].strftime('%Y-%m-%d %H:%M')}"),
                    fh.P(f"User Input: {entry.get('text', 'No input stored')}"),
                    fh.P(
                        f"Mood Score: {entry.get('happiness_score', 'Pending Analysis')}/5"
                    ),
                    fh.Details()(
                        fh.Summary("View Analysis Details"),
                        fh.Ul(cls="uk-list uk-list-hyphen")(
                            fh.Li(
                                f"Social Score: {entry['analysis'].get('socialization', {}).get('score', 'Pending Analysis')}"
                            ),
                            fh.Li(
                                f"Social Explanation: {entry['analysis'].get('socialization', {}).get('explanation', 'N/A')}"
                            ),
                            fh.Li(
                                f"Productivity Score: {entry['analysis'].get('productivity', {}).get('score', 'Pending Analysis')}"
                            ),
                            fh.Li(
                                f"Productivity Explanation: {entry['analysis'].get('productivity', {}).get('explanation', 'N/A')}"
                            ),
                            fh.Li(
                                f"Fulfillment Score: {entry['analysis'].get('fulfillment', {}).get('score', 'Pending Analysis')}"
                            ),
                            fh.Li(
                                f"Fulfillment Explanation: {entry['analysis'].get('fulfillment', {}).get('explanation', 'N/A')}"
                            ),
                            fh.Li(
                                f"Health Score: {entry['analysis'].get('health', {}).get('score', 'Pending Analysis')}"
                            ),
                            fh.Li(
                                f"Health Explanation: {entry['analysis'].get('health', {}).get('explanation', 'N/A')}"
                            ),
                        ),
                    ),
                    fh.Details()(
                        fh.Summary("Suggestions"),
                        fh.Ul(cls="uk-list uk-list-hyphen")(
                            *[
                                fh.Li(f"Social: {suggestion}")
                                for suggestion in entry['analysis'].get('socialization', {}).get('suggestions', [])
                            ],
                            *[
                                fh.Li(f"Productivity: {suggestion}")
                                for suggestion in entry['analysis'].get('productivity', {}).get('suggestions', [])
                            ],
                            *[
                                fh.Li(f"Fulfillment: {suggestion}")
                                for suggestion in entry['analysis'].get('fulfillment', {}).get('suggestions', [])
                            ],
                            *[
                                fh.Li(f"Health: {suggestion}")
                                for suggestion in entry['analysis'].get('health', {}).get('suggestions', [])
                            ],
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
            fh.Script(js_css_loader.js["client_date.js"]),
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
                fh.Script(js_css_loader.js["count_keystrokes_for_user_prompts.js"]),
                fh.Textarea(
                    diary_entries[0].get('text') if diary_entries else 'No input stored',
                    name="text",
                    placeholder="Talk to me.....",
                    hx_post="/diary_prompt",
                    hx_target="diary_prompt",
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
                fh.Button(
                    cls="uk-btn uk-btn-default",
                    hx_disable=True,
                    hx_post="/submit",
                    hx_target="#data",
                    hx_on="htmx:afterRequest => this.removeAttribute('disabled')",
                )("Submit"),
            ),
            fh.Div(id="spinner", data_uk_spinner=True, cls="htmx-indicator"),
            fh.Div(id="data"),
        ),
        fh.Div(cls="uk-margin-top")(fh.H2("History"), *history_items),
    )

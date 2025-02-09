from datetime import datetime
from typing import Any

import fasthtml.common as fh
import numpy as np
from numpy.linalg import norm
from openai import OpenAI
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
            diary_entries: list[dict[str, str | datetime | dict[str, str]] | None] = (
                sorted(
                    user["diary_entries"],
                    key=lambda x: x.get("created_at", ""),
                    reverse=True,
                )
            )
        else:
            diary_entries = []

    history_entries = sorted(
        diary_entries,  # Do not exclude today's entry
        key=lambda x: x.get("created_at", datetime.min),
        reverse=True,
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
                            for suggestion in entry["analysis"]
                            .get("socialization", {})
                            .get("suggestions", [])
                        ],
                        *[
                            fh.Li(f"Productivity: {suggestion}")
                            for suggestion in entry["analysis"]
                            .get("productivity", {})
                            .get("suggestions", [])
                        ],
                        *[
                            fh.Li(f"Fulfillment: {suggestion}")
                            for suggestion in entry["analysis"]
                            .get("fulfillment", {})
                            .get("suggestions", [])
                        ],
                        *[
                            fh.Li(f"Health: {suggestion}")
                            for suggestion in entry["analysis"]
                            .get("health", {})
                            .get("suggestions", [])
                        ],
                    ),
                ),
            )
        )
    return fh.Body(
        fh.Div(cls="intro-screen")(fh.Div(cls="intro-text")("write2me")),
        fh.A("Dashboard", href="/dashboard"),
        fh.Div(cls="container")(
            fh.Div(cls="left-sidebar")(
                fh.Div(id="response"),
            ),
            fh.Div(cls="main-content")(
                fh.Div(cls="header")(
                    fh.Div(cls="date-display")(
                        fh.Div("2025", id="currentYear", cls="year"),
                        fh.P(
                            f"Today is {datetime.now().strftime('%Y-%m-%d')}",
                            cls="today-text",
                        ),
                        cls="date-display",
                    ),
                ),
                fh.Div(cls="date-info")(
                    fh.Hr(cls="separator"),
                    fh.Div(id="diary-prompt")("Tell me about your day...."),
                ),
                fh.Form(hx_post="/submit", hx_target="#data", hx_indicator="#spinner")(
                    fh.Script(js_css_loader.js["count_keystrokes_for_user_prompts.js"]),
                    fh.Div(
                        fh.Label(
                            "How are you feeling from 1-10?",
                            fh.Input(
                                type="number",
                                name="happiness_score",
                                min="1",
                                max="10",
                                cls="uk-input",
                            ),
                        )
                    ),
                    fh.Div(style="height: 30px;"),
                    fh.Div(id="diary-prompt")(fh.H2("Tell me about your day....")),
                    fh.Textarea(
                        diary_entries[0].get("text")
                        if diary_entries
                        else "No input stored",
                        name="text",
                        placeholder="What's on your mind?",
                        hx_post="/diary_prompt",
                        hx_target="diary_prompt",
                        hx_swap="innerHTML",
                        rows=6,
                        cols=50,
                        cls="uk-textarea",
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
            fh.Div(cls="right-sidebar")(
                *[
                    fh.A(fh.Span(month), href=f"/{month.lower()}", cls="tab")
                    for month in [
                        "January",
                        "February",
                        "March",
                        "April",
                        "May",
                        "June",
                        "July",
                        "August",
                        "September",
                        "October",
                        "November",
                        "December",
                    ]
                ],
                fh.A(fh.Span("Login"), href="#", id="loginTab", cls="tab"),
                fh.Div(cls="search-container", style="display: flex;")(
                    fh.Form(hx_post="/search", hx_target="#response")(
                        fh.Input(
                            type="text",
                            name="search_query",
                            placeholder="Search past diaries...",
                            required=True,
                            style="flex-grow:1",
                        )
                    ),
                ),
            ),
            fh.Div(id="loginModal", cls="modal")(
                fh.Div(cls="modal-content")(
                    fh.Span("×", cls="close-button"),
                    fh.Div(cls="login-container")(
                        fh.H2("Login"),
                        fh.Form(
                            action="/login",
                            method="post",
                        )(
                            fh.Input(
                                type="text",
                                name="username",
                                placeholder="Username or Email",
                                required=True,
                            ),
                            fh.Input(
                                type="password",
                                name="password",
                                placeholder="Password",
                                required=True,
                            ),
                            fh.Button("Login", type="submit"),
                        ),
                        fh.Div(
                            fh.A("Forgot your password?", href="#"),
                            cls="forgot-password",
                        ),
                    ),
                ),
            ),
            fh.Div(id="calendarModal", cls="modal")(
                fh.Div(cls="modal-content calendar-modal-content")(
                    fh.Span("×", cls="close-calendar-button"),
                    fh.Div(id="calendarContent"),
                ),
            ),
        ),
    )


def search(
    search_query: str,
    session: dict,
    users_collection: Collection,
    openai_client: OpenAI,
):
    search_query_embedding = np.array(
        openai_client.embeddings.create(
            input=search_query, model="text-embedding-3-large"
        )
        .data[0]
        .embedding
    )
    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    diary_entries: list[dict[str, int | list[dict[str, int]] | Any]] = sorted(
        user.get("diary_entries"),
        key=lambda x: np.dot(
            search_query_embedding,
            np.array(x.get("vector", [0] * len(search_query_embedding))),
        )
        / (
            norm(search_query_embedding)
            * norm(x.get("vector", [0] * len(search_query_embedding)))
        ),
    )

    return fh.Div(
        *[
            fh.A(
                href=f"/diary?date={entry.get('date', datetime.min.strftime('%Y-%m-%d'))}"
            )(
                fh.Span(entry.get("text", "")[:100] + "...", style="color: white;"),
                fh.Br(),
                fh.Br(),
                fh.Br(),
            )
            for entry in diary_entries[:5]
        ]
    )


def diary(date: datetime, session: dict, users_collection: Collection):
    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    diary_entries: list[dict[str, int | list[dict[str, int]] | Any]] = sorted(
        user.get("diary_entries"),
        key=lambda x: int(x.get("date", datetime.min.strftime("%Y-%m-%d")) == date),
        reverse=True,
    )
    if (
        len(diary_entries) > 0
        and diary_entries[0].get("date", datetime.min.strftime("%Y-%m-%d")) == date
    ):
        return fh.Header(fh.A("Main", href="/")), fh.Div(cls="uk-card uk-card-body")(
            fh.H3(cls="uk-card-title")(date),
            fh.P(diary_entries[0].get("text", "")),
        )
    return fh.P(f"Could not find a diary entry created at {date}")

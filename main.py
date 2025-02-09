import os
from typing import Callable

import fasthtml.common as fh
from dotenv import load_dotenv
from openai import OpenAI

import modules.auth as auth
import modules.dashboard as dashboard
import modules.diary_analysis as diary_analysis
import modules.homepage as homepage
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
        # plotly
        fh.Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
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
        fh.Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Gamja+Flower&display=swap",
        ),
    ),
)

db, users_collection = init_db()
oauth = Auth(app, auth.google_auth_client)
oauth.users_collection = users_collection


@rt("/")
def get(auth, session) -> fh.FT:
    return homepage.homepage(auth, session, users_collection)


@rt("/submit")
def post(text: str, happiness_score: int, session) -> fh.FT:
    return diary_analysis.category_analysis(
        text, happiness_score, openai_client, session, users_collection
    )


@rt("/search")
def post(search_query: str, session) -> fh.FT:
    return homepage.search(search_query, session, users_collection, openai_client)


@rt("/login")
def login(req):
    return auth.login(req, oauth)


@rt("/auth/logout")
def logout(session):
    return auth.logout(session)


@rt("/prompt_user")
def post(text: str = "") -> fh.FT:
    return diary_analysis.prompt_user(text, openai_client)


@rt("/dashboard")
def get(session):
    return dashboard.plot_diary_data(session, users_collection)


@rt("/improvement_suggestions")
def get(session, feature: str):
    return dashboard.improvement_suggestions(
        feature, openai_client, session, users_collection
    )


fh.serve(host="localhost", port=5001)

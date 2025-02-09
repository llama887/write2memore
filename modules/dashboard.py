import json
from datetime import datetime, timedelta
from typing import Any

import fasthtml.common as fh
import numpy as np
import pandas as pd
from openai import OpenAI
from pymongo.collection import Collection
from sklearn.linear_model import LinearRegression

import prompts_and_schemas.diary_feature_analysis as diary_feature_analysis
import prompts_and_schemas.diary_prompt as diary_prompt


def plot_diary_data(session: dict, users_collection: Collection):
    def _make_plot(plot_data, div_id: str) -> fh.FT:
        div_id = div_id.replace(" ", "-")
        json_data = json.dumps(plot_data)
        return fh.Div(id=div_id), fh.Script(f"Plotly.newPlot('{div_id}', {json_data});")

    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    diary_entries: list[dict[str, int | list[dict[str, int]] | Any]] = sorted(
        user.get("diary_entries"), key=lambda x: x.get("created_at", "")
    )

    dates: list[int] = []
    analysis_scores: list[dict[str, int]] = [{} for _ in diary_entries]
    happiness_scores: list[int] = []
    types_of_analysis: set[str] = set()
    for i, diary in enumerate(diary_entries):
        happiness_scores.append(diary.get("happiness_score", 0))
        dates.append(str(diary.get("created_at")))
        analysis_types = diary.get("analysis", {})
        for analysis_type in analysis_types.keys():
            analysis_scores[i][analysis_type] = analysis_types[analysis_type].get(
                "score", 0
            )
            types_of_analysis.add(analysis_type)

    data = []
    data.append(
        {"x": dates, "y": happiness_scores, "type": "scatter", "name": "happiness"}
    )

    scores_per_analysis_type: dict[str, int] = {}
    for analysis_type in types_of_analysis:
        current_analysis_type_scores: list[int] = []
        for analysis_score in analysis_scores:
            current_analysis_type_scores.append(analysis_score.get(analysis_type, 0))
        data.append(
            {
                "x": dates,
                "y": current_analysis_type_scores,
                "type": "scatter",
                "name": analysis_type,
            }
        )
        scores_per_analysis_type[analysis_type] = current_analysis_type_scores
    plot_data = {
        "data": data,
        "layout": {"title": data},
        "config": {
            "modeBarButtonsToRemove": [
                "zoom2d",
                "pan2d",
                "select2d",
                "zoom",
                "resetScale2d",
                "zoomIn2d",
                "zoomOut2d",
            ]
        },
    }

    # finding the most important feature
    X: pd.DataFrame = pd.DataFrame(scores_per_analysis_type)
    y: pd.DataFrame = pd.DataFrame(
        np.array(happiness_scores), columns=["happiness_score"]
    )
    model = LinearRegression()
    model.fit(X, y)
    coefficients = pd.DataFrame(
        {"Feature": X.columns, "Coefficient": model.coef_.ravel()}
    ).sort_values(by="Coefficient", ascending=False)
    return (
        fh.A("Main", href="/"),
        fh.H1(
            f"The most important thing to optimize is {coefficients.iloc[0]['Feature']}"
        ),
        fh.Div(
            hx_indicator="#improvement-suggestions-spinner",
            hx_trigger="load",
            hx_swap="innerHTML",
            hx_get=f"/improvement_suggestions?feature={coefficients.iloc[0]['Feature']}",
        ),
        fh.Div(
            id="improvement-suggestions-spinner",
            data_uk_spinner=True,
            cls="htmx-indicator",
        ),
        fh.H1("Weekly Summary"),
        fh.Div(
            hx_indicator="#weekly-goals-spinner",
            hx_trigger="load",
            hx_swap="innerHTML",
            hx_get="/weekly_summary",
        ),
        fh.Div(
            id="weekly-goals-spinner",
            data_uk_spinner=True,
            cls="htmx-indicator",
        ),
        fh.H1("All Time Performance"),
        _make_plot(plot_data, "plot"),
    )


def improvement_suggestions(
    feature: str,
    openai_client: OpenAI,
    session: dict,
    users_collection: Collection,
):
    def get_entries(
        diary_entries: list[dict[str, int | list[dict[str, int]] | Any]],
        feature: str,
        context_length: int,
        min_length: int,
        best: bool,
    ) -> list[dict[str, list | str]]:
        entries = []
        slice = (
            diary_entries[: context_length + 1]
            if best
            else diary_entries[context_length:]
        )
        for entry in slice:
            if len(entry.get("text", "")) > min_length:
                entries.append(
                    {
                        "text": entry.get("text", ""),
                        "feature": feature,
                        "suggestions": entry.get(feature, {}).get("suggestions", []),
                        "explanation": entry.get(feature, {}).get("explanation", ""),
                    }
                )
        return entries

    def _make_prompt(
        best: list[dict[str, list | str]],
        worst: list[dict[str, list | str]],
        feature: str,
    ) -> str:
        prompt = f"<feature>{feature}</feature>"
        prompt += "<best-entries>"
        for entry in best:
            prompt += f"""
    <entry>
        <text>
            {entry["text"]}
        </text>
        <explaination>
            {entry["explanation"]}
        </explaination>
        <suggestions>
            {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry["suggestions"]]}
        </suggestions>
    </entry>"""
        prompt += "</best-entries>\n<worst-entries>"
        for entry in worst:
            prompt += f"""
    <entry>
        <text>
            {entry["text"]}
        </text>
        <explaination>
            {entry["explanation"]}
        </explaination>
        <suggestions>
            {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry["suggestions"]]}
        </suggestions>
    </entry>
            """
        prompt += "<worst-entries>"

    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    diary_entries: list[dict[str, int | list[dict[str, int]] | Any]] = sorted(
        user.get("diary_entries"),
        key=lambda x: x.get("analysis", {}).get(feature, {}).get("score", 0),
        reverse=True,
    )
    CONTEXT_LENGTH = 5
    MIN_LENGTH = 100
    # TODO: length check
    best: list[dict[str, list | str]] = get_entries(
        diary_entries, feature, CONTEXT_LENGTH, MIN_LENGTH, best=True
    )
    worst: list[dict[str, list | str]] = get_entries(
        diary_entries, feature, CONTEXT_LENGTH, MIN_LENGTH, best=False
    )
    prompt = _make_prompt(best, worst, feature)
    improvement_suggestions_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": diary_feature_analysis.diary_feature_analysis_system_prompt,
            },
            {
                "role": "user",
                "content": f"""These are some of my past diary entries which demonstrate my best and worst days relative to this metric: {feature}\nPlease give me some suggestions on how to improve\n{prompt}""",
            },
        ],
    )
    return fh.P(improvement_suggestions_response.choices[0].message.content)


def weekly_summary(
    openai_client: OpenAI,
    session: dict,
    users_collection: Collection,
):
    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    diary_entries: list[dict[str, int | list[dict[str, int]] | Any]] = sorted(
        user.get("diary_entries"), key=lambda x: x.get("created_at", ""), reverse=True
    )
    week_entries = []
    one_week_ago = datetime.now() - timedelta(weeks=1)
    for entry in diary_entries:
        if entry.get("created_at", datetime.min) <= one_week_ago:
            break
        week_entries.append(entry)

    prompt = "<entries>\n"
    for entry in week_entries:
        prompt += f"""
    <entry>
        <text>\n{entry.get("text", "")}\n</text>
        <happiness_score>{entry.get("happiness_score", 0)}</happiness_score>
        <analysis>
            <socialization>
                {entry.get("analysis", {}).get("socialization", {}).get("explanation")}
                <suggestions>
                    {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry.get("analysis", {}).get("socialization", {}).get("suggestions", [])]}
                </suggestions>
            </socialization>
            <productivity>
                {entry.get("analysis", {}).get("productivity", {}).get("explanation")}
                <suggestions>
                    {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry.get("analysis", {}).get("productivity", {}).get("suggestions", [])]}
                </suggestions>
            </productivity>
            <fulfillment>
                {entry.get("analysis", {}).get("fulfillment", {}).get("explanation")}
                <suggestions>
                    {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry.get("analysis", {}).get("fulfillment", {}).get("suggestions", [])]}
                </suggestions>
            </fulillment>
            <health>
                {entry.get("analysis", {}).get("health", {}).get("explanation")}
                <suggestions>
                    {[f"<suggestion>{suggestion}</suggestion>" for suggestion in entry.get("analysis", {}).get("health", {}).get("suggestions", [])]}
                </suggestions>
            </health>
        </analysis>
    </entry>
        """
    prompt += "</entries>"
    print(prompt)
    weekly_summary_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": diary_prompt.weekly_summary_system_prompt},
            {
                "role": "user",
                "content": f"""These are some of my past diary entries from this week. Give me a goal to pursue\n{prompt}""",
            },
        ],
    )
    return fh.P(weekly_summary_response.choices[0].message.content)

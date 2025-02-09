import json
from typing import Any

import fasthtml.common as fh
import numpy as np
import pandas as pd
from pymongo.collection import Collection
from sklearn.linear_model import LinearRegression


def plot_diary_data(session: dict, users_collection: Collection):
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

    analysis_plots: list[fh.FT] = {}
    happiness_data = {
        "data": [
            {
                "y": happiness_scores,
                "x": dates,
                "type": "scatter",
            }
        ],
        "title": "happiness",
        "type": "scatter",
    }
    analysis_plots["happiness plot"] = make_plot(happiness_data, "happiness plot")
    scores_per_analysis_type: dict[str, int] = {}
    for analysis_type in types_of_analysis:
        current_analysis_type_scores: list[int] = []
        for analysis_score in analysis_scores:
            current_analysis_type_scores.append(analysis_score.get(analysis_type, 0))
        plot_data = {
            "data": [
                {
                    "y": current_analysis_type_scores,
                    "x": dates,
                    "type": "scatter",
                }
            ],
            "title": analysis_type,
            "type": "scatter",
        }
        analysis_plots[analysis_type] = make_plot(plot_data, f"{analysis_type} plot")
        scores_per_analysis_type[analysis_type] = current_analysis_type_scores
    X: pd.DataFrame = pd.DataFrame(scores_per_analysis_type)
    y: pd.DataFrame = pd.DataFrame(
        np.array(happiness_scores), columns=["happiness_score"]
    )
    model = LinearRegression()
    model.fit(X, y)
    coefficients = pd.DataFrame(
        {"Feature": X.columns, "Coefficient": model.coef_.ravel()}
    ).sort_values(by="Coefficient", ascending=False)
    print(coefficients)
    return (
        fh.A("Main", href="/"),
        fh.H1(
            f"The most important thing to optimize is {coefficients.iloc[0]['Feature']}"
        ),
        fh.Div(
            *[
                (fh.H2(analysis_type), analysis_plots[analysis_type])
                for analysis_type in list(analysis_plots.keys())
            ]
        ),
    )


def make_plot(plot_data, div_id: str) -> fh.FT:
    div_id = div_id.replace(" ", "-")
    json_data = json.dumps(plot_data)
    return fh.Div(id=div_id), fh.Script(f"Plotly.newPlot('{div_id}', {json_data});")

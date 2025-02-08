from fh_plotly import plotly2fasthtml
from pymongo.collection import Collection


def plot_diary_data(session: dict, users_collection: Collection):
    user_id = session["user_info"]["id"]
    user: dict = users_collection.find_one({"google_id": user_id})
    name = user.get("name", "no name stored")
    diary_entries: list[dict] = sorted(
        user.get("diary_entries"), key=lambda x: x.get("created_at", "")
    )

    dates: list[int] = []
    analysis_scores: dict[str, list[int]] = {}
    happiness_scores: list[int] = []
    for diary in diary_entries:
        happiness_scores.append(diary.get("happiness_score", 0))
        dates.append(diary.get("created_at"))
    return plotly2fasthtml()

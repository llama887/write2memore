import os
from datetime import datetime
from typing import Any

import fasthtml.common as fh
from fastcore.basics import AttrDictDefault
from fasthtml.oauth import GoogleAppClient, OAuth
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

google_auth_client: GoogleAppClient = GoogleAppClient(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    redirect_uri="http://localhost:5001/auth/callback",
)


class Auth(OAuth):
    users_collection: Collection

    def get_auth(
        self,
        info: AttrDictDefault,
        ident: str,
        session: dict,
        state: Any,
    ):
        user_data = {
            "google_id": info["sub"],
            "email": info["email"],
            "name": info.get("name", ""),
            "picture": info.get("picture", ""),
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
        }

        try:
            result = self.users_collection.update_one(
                {"google_id": user_data["google_id"]},
                {
                    "$setOnInsert": {
                        "created_at": user_data["created_at"],
                        "name": user_data["name"],
                        "picture": user_data["picture"],
                        "email": user_data["email"],
                    },
                    "$set": {"last_login": user_data["last_login"]},
                },
                upsert=True,
            )
            print(
                f"✅ User stored: {result.matched_count} updated, {result.upserted_id} inserted."
            )
        except DuplicateKeyError:
            print(f"⚠️ Duplicate user: {user_data['email']}")
        except Exception as e:
            print(f"❌ Error saving user: {e}")

        session["user_info"] = {
            "id": str(user_data["google_id"]),
            "email": user_data["email"],
            "name": user_data["name"],
        }

        return fh.RedirectResponse("/", status_code=303)


def login(req, oauth: Auth):
    return fh.Div(
        fh.P("Login Page"),
        fh.A("Start OAuth", href=oauth.login_link(req)),
    )


def logout(session: dict):
    """Logout route that clears user session and redirects to home."""
    session.pop("user_info", None)
    response = fh.RedirectResponse("/", status_code=303)
    response.delete_cookie("auth")
    return response

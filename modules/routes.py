from typing import Callable

import fasthtml.common as fh
from pymongo.collection import Collection

from modules.auth import Auth, google_auth_client


def init_routes(
    app: fh.FastHTML | fh.FastHTMLWithLiveReload,
    rt: Callable,
    users_collection: Collection,
):
    oauth = Auth(app, google_auth_client)
    oauth.users_collection = users_collection

    @rt("/login")
    def login(req):
        """Login route that redirects to Google OAuth."""
        return fh.Div(
            fh.P("Login Page"),
            fh.A("Start OAuth", href=oauth.login_link(req)),
        )

    @rt("/auth/logout")
    def logout(session: dict):
        """Logout route that clears user session and redirects to home."""
        session.pop("user_info", None)
        response = fh.RedirectResponse("/", status_code=303)
        response.delete_cookie("auth")
        return response

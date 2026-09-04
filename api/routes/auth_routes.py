from flask import (
    Blueprint,
    jsonify,
)

from config import get_headers


# ============================================================
# AUTH BLUEPRINT
# ============================================================

auth_bp = Blueprint(
    "auth",
    __name__,
)


# ============================================================
# AUTH STATUS
# ============================================================

@auth_bp.route(
    "/auth/status",
    methods=["GET"],
)
def auth_status():

    try:

        headers = get_headers()

        cookie_ok = bool(
            headers.get(
                "Cookie"
            )
        )

        csrf_ok = bool(
            headers.get(
                "X-Csrftoken"
            )
        )

        return jsonify({
            "success": True,
            "authenticated": (
                cookie_ok
                and csrf_ok
            ),
            "cookie": cookie_ok,
            "csrf": csrf_ok,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "authenticated": False,
            "cookie": False,
            "csrf": False,
            "error": str(e),
        }), 401

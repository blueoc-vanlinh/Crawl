# ============================================================
# app_1.py
# HY SOC
#
# Nhiệm vụ:
#   - Chạy Flask
#   - Serve Frontend React/Vite
#   - Register API Blueprints
#   - Kiểm tra SPX authentication lúc startup
#
# Không đặt logic crawl ở đây.
# ============================================================

import os

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
)

from config import (
    BASE_URL,
    get_headers,
)

# ============================================================
# API ROUTES
# ============================================================

from api.routes import (
    auth_bp,
    cage_bp,
    order_bp,
    orders_bp,
    station_bp,
    to_bp,
    trip_bp,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend",
)

DIST_DIR = os.path.join(
    FRONTEND_DIR,
    "dist",
)

INDEX_FILE = os.path.join(
    DIST_DIR,
    "index.html",
)


# ============================================================
# SERVER CONFIG
# ============================================================

HOST = os.getenv(
    "HOST",
    "0.0.0.0",
)

PORT = int(
    os.getenv(
        "PORT",
        "5000",
    )
)


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__,
    static_folder=DIST_DIR,
    static_url_path="",
)


# ============================================================
# REGISTER API BLUEPRINTS
# ============================================================

app.register_blueprint(
    auth_bp
)

app.register_blueprint(
    cage_bp
)

app.register_blueprint(
    order_bp
)

app.register_blueprint(
    orders_bp
)

app.register_blueprint(
    station_bp
)

app.register_blueprint(
    to_bp
)

app.register_blueprint(
    trip_bp
)


# ============================================================
# SPX AUTH
# ============================================================

def check_spx_auth():
    """
    Chỉ kiểm tra authentication hiện tại.

    Không crawl dữ liệu.
    """

    headers = get_headers()

    return {
        "success": True,

        "cookie": bool(
            headers.get(
                "Cookie"
            )
        ),

        "csrf": bool(
            headers.get(
                "X-Csrftoken"
            )
        ),
    }


# ============================================================
# STARTUP AUTH CHECK
# ============================================================

def startup_auth_check():

    print(
        "=" * 60
    )

    print(
        "Checking SPX authentication..."
    )

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

        if not cookie_ok:

            raise RuntimeError(
                "Không tìm thấy Cookie"
            )

        if not csrf_ok:

            raise RuntimeError(
                "Không tìm thấy CSRF"
            )

        print(
            "SPX AUTH: OK"
        )

        print(
            "Cookie: OK"
        )

        print(
            "CSRF:   OK"
        )

        print(
            "=" * 60
        )

        return True

    except Exception as e:

        print(
            "SPX AUTH: FAILED"
        )

        print(
            f"ERROR: {e}"
        )

        print(
            "=" * 60
        )

        return False


# ============================================================
# FRONTEND ROOT
# ============================================================

@app.route(
    "/",
    methods=["GET"],
)
def frontend_home():

    if not os.path.isfile(
        INDEX_FILE
    ):

        return jsonify({
            "success": False,

            "error":
                "Frontend build not found",

            "message":
                "Hãy chạy npm run build "
                "trong thư mục frontend.",
        }), 500

    return send_from_directory(
        DIST_DIR,
        "index.html",
    )


# ============================================================
# FRONTEND STATIC
# ============================================================

@app.route(
    "/assets/<path:filename>",
    methods=["GET"],
)
def frontend_assets(
    filename,
):

    assets_dir = os.path.join(
        DIST_DIR,
        "assets",
    )

    return send_from_directory(
        assets_dir,
        filename,
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():

    return jsonify({
        "success": True,
        "service": "HY SOC",
        "status": "running",
    })


# ============================================================
# FRONTEND SPA FALLBACK
# ============================================================

@app.errorhandler(
    404
)
def not_found(error):

    path = request.path

    # --------------------------------------------------------
    # Những path này là API
    #
    # Nếu API không tồn tại thì trả JSON 404,
    # KHÔNG trả index.html.
    # --------------------------------------------------------

    api_prefixes = (
        "/api/",
        "/auth/",
        "/health",
        "/trip/",
        "/order/",
        "/orders/",
        "/cage/",
        "/station/",
        "/stations/",
        "/to/",
        "/tracking/",
    )

    if path.startswith(
        api_prefixes
    ):

        return jsonify({
            "success": False,

            "error":
                "API endpoint not found",

            "path":
                path,
        }), 404

    # --------------------------------------------------------
    # FRONTEND
    #
    # React Router:
    #
    # /dashboard
    # /trip
    # /orders
    # /cage
    # /jobs
    #
    # Nếu không phải file thật thì trả index.html
    # để React tự xử lý route.
    # --------------------------------------------------------

    if os.path.isfile(
        INDEX_FILE
    ):

        return send_from_directory(
            DIST_DIR,
            "index.html",
        )

    return jsonify({
        "success": False,

        "error":
            "Frontend build not found",

        "message":
            "Hãy chạy npm run build "
            "trong thư mục frontend.",
    }), 500


# ============================================================
# INTERNAL SERVER ERROR
# ============================================================

@app.errorhandler(
    500
)
def internal_error(error):

    return jsonify({
        "success": False,

        "error":
            "Internal server error",
    }), 500


# ============================================================
# PRINT REGISTERED ROUTES
# ============================================================

def print_routes():

    print()
    print(
        "=" * 90
    )

    print(
        "REGISTERED ROUTES"
    )

    print(
        "=" * 90
    )

    for rule in sorted(
        app.url_map.iter_rules(),
        key=lambda x: str(x),
    ):

        methods = sorted(
            rule.methods
            - {
                "HEAD",
                "OPTIONS",
            }
        )

        print(
            f"{methods!s:<35} {rule}"
        )

    print(
        "=" * 90
    )


# ============================================================
# FRONTEND CHECK
# ============================================================

def check_frontend():

    print(
        "FRONTEND:",
        DIST_DIR,
    )

    if os.path.isfile(
        INDEX_FILE
    ):

        print(
            "FRONTEND: OK"
        )

        print(
            "INDEX:",
            INDEX_FILE,
        )

        return True

    print(
        "FRONTEND: NOT FOUND"
    )

    print(
        "Run:"
    )

    print(
        "cd frontend"
    )

    print(
        "npm run build"
    )

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 60
    )

    print(
        "HY SOC"
    )

    print(
        "=" * 60
    )

    print(
        "BASE URL:",
        BASE_URL,
    )

    print(
        "HOST:",
        HOST,
    )

    print(
        "PORT:",
        PORT,
    )

    print(
        "FRONTEND:",
        DIST_DIR,
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # SPX AUTH
    # --------------------------------------------------------

    startup_auth_check()

    print()

    # --------------------------------------------------------
    # FRONTEND
    # --------------------------------------------------------

    check_frontend()

    print()

    # --------------------------------------------------------
    # ROUTES
    # --------------------------------------------------------

    print_routes()

    print()

    print(
        "Starting Flask..."
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
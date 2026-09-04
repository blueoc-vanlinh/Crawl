import os
import json
import time
import subprocess

import requests
import websocket


CHROME_EXE = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)

CHROME_PROFILE = os.path.join(
    os.environ["LOCALAPPDATA"],
    "ChromeDebug_SOC"
)

PORT_FILE = os.path.join(
    CHROME_PROFILE,
    "DevToolsActivePort"
)

AUTH_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            __file__
        )
    ),
    "spx_auth_cache.json"
)

AUTH_TTL_SECONDS = (
    2
    * 60
    * 60
)

LOGIN_TIMEOUT_SECONDS = (
    10
    * 60
)

LOGIN_CHECK_INTERVAL = 2

CLOSE_DELAY_SECONDS = 5


def read_debug_port():
    if not os.path.exists(
        PORT_FILE
    ):
        return None

    try:
        with open(
            PORT_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            lines = (
                f.read()
                .splitlines()
            )

        if not lines:
            return None

        return int(
            lines[0].strip()
        )

    except Exception:
        return None


def is_debug_port_alive(
    port
):
    if not port:
        return False

    try:
        response = requests.get(
            (
                f"http://127.0.0.1:"
                f"{port}/json/version"
            ),
            timeout=1
        )

        return (
            response.status_code
            == 200
        )

    except requests.RequestException:
        return False


def start_chrome_debug():
    os.makedirs(
        CHROME_PROFILE,
        exist_ok=True
    )

    try:
        if os.path.exists(
            PORT_FILE
        ):
            os.remove(
                PORT_FILE
            )
    except OSError:
        pass

    args = [
        CHROME_EXE,
        "--remote-debugging-port=0",
        "--remote-allow-origins=*",
        (
            f"--user-data-dir="
            f"{CHROME_PROFILE}"
        ),
        "--no-first-run",
        "--no-default-browser-check",
        "https://spx.shopee.vn/",
    ]

    subprocess.Popen(
        args,
        stdout=
            subprocess.DEVNULL,
        stderr=
            subprocess.DEVNULL
    )

    for _ in range(60):
        time.sleep(
            0.5
        )

        port = (
            read_debug_port()
        )

        if (
            port
            and
            is_debug_port_alive(
                port
            )
        ):
            print(
                "ChromeDebug_SOC "
                f"started on port {port}"
            )

            return port

    raise RuntimeError(
        "Không thể khởi động "
        "ChromeDebug_SOC."
    )


def get_debug_port():
    port = (
        read_debug_port()
    )

    if (
        port
        and
        is_debug_port_alive(
            port
        )
    ):
        return port

    print(
        "ChromeDebug_SOC chưa chạy "
        "hoặc port cũ đã chết."
    )

    print(
        "Starting ChromeDebug_SOC..."
    )

    return (
        start_chrome_debug()
    )


def get_debug_url(
    port=None
):
    if port is None:
        port = (
            get_debug_port()
        )

    return (
        f"http://127.0.0.1:"
        f"{port}"
    )


def close_chrome_debug(
    port
):
    if not port:
        return

    if not is_debug_port_alive(
        port
    ):
        return

    try:
        response = requests.get(
            (
                f"http://127.0.0.1:"
                f"{port}/json/version"
            ),
            timeout=3
        )

        response.raise_for_status()

        data = (
            response.json()
        )

        ws_url = data.get(
            "webSocketDebuggerUrl"
        )

        if not ws_url:
            return

        ws = (
            websocket
            .create_connection(
                ws_url,
                timeout=5
            )
        )

        try:
            ws.send(
                json.dumps({
                    "id": 1,
                    "method":
                        "Browser.close"
                })
            )

            try:
                ws.recv()
            except Exception:
                pass

        finally:
            try:
                ws.close()
            except Exception:
                pass

        print(
            "ChromeDebug_SOC closed."
        )

    except Exception as e:
        print(
            "Không đóng được "
            "ChromeDebug_SOC: "
            f"{e}"
        )


def load_cached_auth():
    if not os.path.exists(
        AUTH_FILE
    ):
        return None

    try:
        with open(
            AUTH_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = (
                json.load(f)
            )

        saved_at = float(
            data.get(
                "saved_at",
                0
            )
            or 0
        )

        if not saved_at:
            return None

        age = (
            time.time()
            - saved_at
        )

        if (
            age
            >= AUTH_TTL_SECONDS
        ):
            print(
                "SPX auth cache "
                "đã hết hạn."
            )

            try:
                os.remove(
                    AUTH_FILE
                )
            except OSError:
                pass

            return None

        cookie = data.get(
            "cookie"
        )

        csrf = data.get(
            "csrf"
        )

        if (
            not cookie
            or
            not csrf
        ):
            return None

        remaining = int(
            AUTH_TTL_SECONDS
            - age
        )

        remaining_minutes = (
            remaining // 60
        )

        print(
            "SPX auth cache: OK "
            f"({remaining_minutes} "
            "phút còn lại)"
        )

        return {
            "cookie":
                cookie,
            "csrf":
                csrf,
            "cookies":
                data.get(
                    "cookies",
                    {}
                ),
            "saved_at":
                saved_at,
        }

    except Exception as e:
        print(
            "Không đọc được "
            "SPX auth cache: "
            f"{e}"
        )

        return None


def save_auth_cache(
    auth
):
    saved_at = (
        time.time()
    )

    data = {
        "saved_at":
            saved_at,

        "expires_at":
            saved_at
            + AUTH_TTL_SECONDS,

        "cookie":
            auth["cookie"],

        "csrf":
            auth["csrf"],

        "cookies":
            auth.get(
                "cookies",
                {}
            ),
    }

    temp_file = (
        AUTH_FILE
        + ".tmp"
    )

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        AUTH_FILE
    )

    print(
        "SPX auth saved."
    )

    print(
        "Auth expires in 2 hours."
    )


def get_spx_tabs(
    port
):
    debug_url = (
        get_debug_url(
            port
        )
    )

    response = requests.get(
        f"{debug_url}/json",
        timeout=5
    )

    response.raise_for_status()

    return (
        response.json()
    )


def find_spx_tab(
    port
):
    try:
        tabs = (
            get_spx_tabs(
                port
            )
        )

    except Exception:
        return None

    for tab in tabs:
        url = str(
            tab.get(
                "url",
                ""
            )
        )

        if (
            "spx.shopee.vn"
            in url
        ):
            return tab

    return None


def read_spx_auth_from_browser(
    port
):
    spx_tab = (
        find_spx_tab(
            port
        )
    )

    if not spx_tab:
        return None

    ws_url = (
        spx_tab.get(
            "webSocketDebuggerUrl"
        )
    )

    if not ws_url:
        return None

    ws = (
        websocket
        .create_connection(
            ws_url,
            timeout=5
        )
    )

    try:
        request_id = 1

        ws.send(
            json.dumps({
                "id":
                    request_id,

                "method":
                    "Network.getAllCookies"
            })
        )

        cookie_list = []

        while True:
            raw = (
                ws.recv()
            )

            response = (
                json.loads(
                    raw
                )
            )

            if (
                response.get(
                    "id"
                )
                != request_id
            ):
                continue

            cookie_list = (
                response
                .get(
                    "result",
                    {}
                )
                .get(
                    "cookies",
                    []
                )
            )

            break

    finally:
        try:
            ws.close()
        except Exception:
            pass

    cookies = {}

    for cookie in cookie_list:
        domain = str(
            cookie.get(
                "domain",
                ""
            )
        )

        if (
            "spx.shopee.vn"
            not in domain
        ):
            continue

        name = (
            cookie.get(
                "name"
            )
        )

        value = (
            cookie.get(
                "value"
            )
        )

        if (
            name
            and
            value is not None
        ):
            cookies[
                name
            ] = value

    if not cookies:
        return None

    csrf = (
        cookies.get(
            "csrftoken"
        )
    )

    if not csrf:
        return None

    cookie_string = (
        "; ".join(
            (
                f"{name}="
                f"{value}"
            )
            for (
                name,
                value
            )
            in cookies.items()
        )
    )

    if not cookie_string:
        return None

    return {
        "cookie":
            cookie_string,

        "csrf":
            csrf,

        "cookies":
            cookies,
    }


def wait_for_spx_login(
    port
):
    print(
        "=" * 60
    )

    print(
        "Hãy đăng nhập SPX "
        "trong ChromeDebug_SOC."
    )

    print(
        "Đang chờ Cookie + CSRF..."
    )

    print(
        "=" * 60
    )

    start_time = (
        time.time()
    )

    while True:
        if (
            time.time()
            - start_time
            > LOGIN_TIMEOUT_SECONDS
        ):
            raise RuntimeError(
                "Hết thời gian chờ "
                "đăng nhập SPX."
            )

        if not is_debug_port_alive(
            port
        ):
            raise RuntimeError(
                "ChromeDebug_SOC "
                "đã bị đóng."
            )

        try:
            auth = (
                read_spx_auth_from_browser(
                    port
                )
            )

            if (
                auth
                and
                auth.get(
                    "cookie"
                )
                and
                auth.get(
                    "csrf"
                )
            ):
                print(
                    "SPX login detected."
                )

                return auth

        except Exception:
            pass

        time.sleep(
            LOGIN_CHECK_INTERVAL
        )


def create_new_spx_auth():
    port = (
        get_debug_port()
    )

    try:
        auth = (
            wait_for_spx_login(
                port
            )
        )

        save_auth_cache(
            auth
        )

        print(
            "Đã lấy token SPX."
        )

        print(
            "Chrome sẽ đóng sau "
            f"{CLOSE_DELAY_SECONDS} giây..."
        )

        time.sleep(
            CLOSE_DELAY_SECONDS
        )

        return auth

    finally:
        close_chrome_debug(
            port
        )


def get_spx_auth(
    force_refresh=False
):
    if not force_refresh:
        cached = (
            load_cached_auth()
        )

        if cached:
            return cached

    return (
        create_new_spx_auth()
    )


def clear_spx_auth_cache():
    if os.path.exists(
        AUTH_FILE
    ):
        try:
            os.remove(
                AUTH_FILE
            )

            print(
                "SPX auth cache cleared."
            )

        except OSError as e:
            raise RuntimeError(
                "Không xóa được "
                "SPX auth cache."
            ) from e


def get_spx_headers(
    force_refresh=False
):
    auth = get_spx_auth(
        force_refresh=
            force_refresh
    )

    return {
        "Cookie":
            auth["cookie"],

        "X-Csrftoken":
            auth["csrf"],

        "X-CSRFToken":
            auth["csrf"],

        "Referer":
            "https://spx.shopee.vn/",

        "Origin":
            "https://spx.shopee.vn",

        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 "
                "Safari/537.36"
            ),

        "Accept":
            "application/json, text/plain, */*",

        "Accept-Language":
            "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
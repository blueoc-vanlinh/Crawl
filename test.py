from core.auth import get_spx_auth
from core.sheet_auth_push import push_spx_auth_to_sheet


def main():
    auth = get_spx_auth()

    push_spx_auth_to_sheet(
        auth
    )

    print(
        "TEST OK"
    )


if __name__ == "__main__":
    main()
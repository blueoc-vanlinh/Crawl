import requests
from config import BASE_URL, HEADERS


class SPXClient:

    def post(self, endpoint, payload):
        url = BASE_URL + endpoint

        r = requests.post(
            url,
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        r.raise_for_status()

        return r.json()
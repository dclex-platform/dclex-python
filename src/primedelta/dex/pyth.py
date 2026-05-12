import requests

from primedelta.settings import PYTH_HERMES_BASE_URL


def fetch_price_update_data(feed_ids: list[str]) -> list[bytes]:
    if not feed_ids:
        return []

    response = requests.get(
        f"{PYTH_HERMES_BASE_URL}/v2/updates/price/latest",
        params=[("ids[]", fid) for fid in feed_ids] + [("encoding", "hex")],
    )
    response.raise_for_status()
    payload = response.json()
    return [bytes.fromhex(entry) for entry in payload["binary"]["data"]]

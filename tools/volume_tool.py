import requests


def get_most_active(count: int = 20) -> list[str]:
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {"scrIds": "most_actives", "count": count}
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, params=params, headers=headers, timeout=10)
    res.raise_for_status()

    quotes = res.json()["finance"]["result"][0]["quotes"]
    return [q["symbol"] for q in quotes]

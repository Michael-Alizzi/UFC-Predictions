"""Fighter nationality lookup via the Wikidata API.

ufcstats.com fighter pages carry no nationality or hometown, so fighter
country is enriched from Wikidata instead: search the fighter's name,
keep the first hit whose description looks like a combat-sports athlete
(guards against namesakes), then read the country-of-citizenship claim
(property P27). Any failure or ambiguity returns "" (NaN in the output
CSV) rather than raising, so one bad lookup never kills a scrape.
"""
import re
import threading

import requests

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
# Wikidata API etiquette: send a descriptive User-Agent
HEADERS = {
    "User-Agent": "UFC-Predictions scraper (https://github.com/Michael-Alizzi/UFC-Predictions)"
}
TIMEOUT = 15

# Two-tier disambiguation: strongly prefer entities described as MMA
# fighters; only fall back to the broader combat-sports match when no MMA
# hit exists. The broad pattern alone once matched a 19th-century British
# boxer namesake ahead of the UFC's Robert Whittaker.
MMA_DESC = re.compile(r"mixed martial|MMA|UFC", re.IGNORECASE)
FIGHTER_DESC = re.compile(
    r"fighter|martial artist|kickboxer|boxer|wrestler|judoka|grappler",
    re.IGNORECASE,
)

# Country labels are shared across fighters; cache them across the
# thread pool so ~200 countries aren't re-fetched thousands of times.
_country_label_cache = {}
_cache_lock = threading.Lock()


def _api_get(params: dict) -> dict:
    params = dict(params, format="json")
    resp = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _find_fighter_entity(name: str):
    data = _api_get(
        {
            "action": "wbsearchentities",
            "search": name,
            "language": "en",
            "type": "item",
            # 20, not 5: common names bury the MMA fighter below namesakes
            # (ecologists, cricketers, Victorian boxers) in search ranking --
            # the MMA-preferred tier can only pick from hits it can see.
            "limit": 20,
        }
    )
    hits = data.get("search", [])
    for pattern in (MMA_DESC, FIGHTER_DESC):
        for hit in hits:
            if pattern.search(hit.get("description") or ""):
                return hit["id"]
    return None


def _country_ids(entity_id: str) -> list:
    data = _api_get(
        {"action": "wbgetclaims", "entity": entity_id, "property": "P27"}
    )
    ids = []
    for claim in data.get("claims", {}).get("P27", []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and "id" in value:
            ids.append(value["id"])
    return ids


def _country_labels(ids: list) -> list:
    with _cache_lock:
        missing = [i for i in ids if i not in _country_label_cache]
    if missing:
        data = _api_get(
            {
                "action": "wbgetentities",
                "ids": "|".join(missing),
                "props": "labels",
                "languages": "en",
            }
        )
        with _cache_lock:
            for qid, entity in data.get("entities", {}).items():
                _country_label_cache[qid] = (
                    entity.get("labels", {}).get("en", {}).get("value", "")
                )
    with _cache_lock:
        return [_country_label_cache.get(i, "") for i in ids]


# Names whose Wikidata search never surfaces the UFC fighter, verified by
# the CI smoke test: even 20 candidates deep with MMA-preferred matching,
# "Robert Whittaker" only yields famous namesakes (a Victorian-era British
# boxer wins the fallback tier). Checked before any API call.
MANUAL_COUNTRIES = {
    "robert whittaker": "New Zealand; Australia",
}


def get_fighter_country(name: str) -> str:
    """Country of citizenship for a fighter name (";"-joined when Wikidata
    records more than one), or "" when the fighter can't be found, has no
    recorded citizenship, or the API is unreachable."""
    manual = MANUAL_COUNTRIES.get(name.strip().lower())
    if manual:
        return manual
    try:
        entity_id = _find_fighter_entity(name)
        if not entity_id:
            return ""
        labels = _country_labels(_country_ids(entity_id))
        return "; ".join(label for label in labels if label)
    except Exception:
        return ""

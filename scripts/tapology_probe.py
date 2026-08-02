"""Exploratory CI probe: can Tapology be scraped for fighter birthplace?

Tapology fighter pages carry richer location data than Wikidata (a
"Born:" field with city/state/country plus "Fighting out of:"), which
would improve the home-crowd feature and add locality columns. But the
site is known for aggressive anti-bot protection, so before writing any
real scraper this probe answers, from a CI runner:

  1. Does Tapology serve real pages or a Cloudflare challenge?
  2. Can a fighter be found by name via the search page?
  3. What exactly does the fighter page's details box contain?

Always exits 0 -- it is a fact-finding mission, not a test.
"""
import re
import sys

import requests
from bs4 import BeautifulSoup

BASE = "https://www.tapology.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PANEL = [
    "Ilia Topuria",
    "Robert Whittaker",
    "Conor McGregor",
    "Zhang Weili",
    "Jiri Prochazka",
    "Belal Muhammad",
]


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    blocked = (
        r.status_code in (403, 503)
        or "Just a moment" in r.text
        or "Checking your browser" in r.text
        or "challenge-platform" in r.text
    )
    body = " ".join(r.text.split())
    print(f"GET {url}\n  -> {r.status_code} bytes={len(r.text)} "
          f"{'BLOCKED (bot challenge)' if blocked else 'ok'}")
    if blocked or len(r.text) < 5000:
        print(f"  body[:400]: {body[:400]!r}")
    return r, blocked


def probe_fighter(name):
    q = name.replace(" ", "+")
    r, blocked = fetch(f"{BASE}/search?term={q}&mainSearchFilter=fighters")
    if blocked:
        return False
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a for a in soup.find_all("a", href=True)
             if "/fightcenter/fighters/" in a["href"]]
    print(f"  fighter links found for {name!r}: {len(links)}"
          + (f"; first: {links[0]['href']} ({links[0].get_text(strip=True)!r})"
             if links else ""))
    if not links:
        return False

    url = links[0]["href"]
    if url.startswith("/"):
        url = BASE + url
    r, blocked = fetch(url)
    if blocked:
        return False
    soup = BeautifulSoup(r.text, "html.parser")

    # Dump every "label: value" line in the page's details area so the CI
    # log shows the exact fields and formats available for parsing.
    text = soup.get_text("\n", strip=True)
    interesting = re.compile(
        r"^(Given Name|Nickname|Born|Fighting out of|Nationality|Age|"
        r"Date of Birth|Height|Reach|Weight Class|Affiliation)\b", re.I)
    lines, seen = [], set()
    it = iter(text.split("\n"))
    for line in it:
        if interesting.match(line) and line not in seen:
            value = line if ":" in line else f"{line}: {next(it, '')}"
            lines.append(value)
            seen.add(line)
    print(f"  details for {name}:")
    for line in lines[:14]:
        print(f"    {line}")
    return True


def main():
    print("=== Tapology probe ===")
    _, blocked = fetch(BASE + "/")
    if blocked:
        print("\nVERDICT: Tapology serves a bot challenge to this network -- "
              "not scrapeable from CI with plain requests.")
        return
    ok = 0
    for name in PANEL:
        print()
        ok += bool(probe_fighter(name))
    print(f"\nVERDICT: fighter pages parsed for {ok}/{len(PANEL)} panel names")


if __name__ == "__main__":
    main()
    sys.exit(0)

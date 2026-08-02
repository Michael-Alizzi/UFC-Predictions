"""Live smoke test for the fighter scraper and Wikidata nationality lookup.

Meant for CI (GitHub Actions), where outbound network is unrestricted:

    python scripts/scrape_smoke_test.py          # quick live checks (~1 min)
    python scripts/scrape_smoke_test.py --full   # full fighter scrape (slow)

Quick mode hits one real ufcstats listing page, a few real fighter pages,
and Wikidata for a panel of well-known fighters across nationalities,
then reports lookup coverage. Full mode runs create_fighter_data_csv()
for real; the workflow uploads the resulting CSV as an artifact.
"""
import argparse
import sys

sys.path.insert(0, ".")  # run from the repo root

from src.createdata.scrape_fighter_details import FighterDetailsScraper
from src.createdata.scrape_fighter_nationality import get_fighter_country

# Expected country substrings (lowercased) -- any match counts, so both
# "United States" and "United States of America" satisfy "united states".
KNOWN_FIGHTERS = {
    "Conor McGregor": ("ireland",),
    "Ilia Topuria": ("georgia", "spain"),
    "Zhang Weili": ("china",),
    "Islam Makhachev": ("russia",),
    "Alexander Volkanovski": ("australia",),
    "Tom Aspinall": ("united kingdom",),
    "Charles Oliveira": ("brazil",),
    "Sean O'Malley": ("united states",),
    "Dricus du Plessis": ("south africa",),
    "Jan Blachowicz": ("poland",),
    "Kamaru Usman": ("nigeria", "united states"),
    "Amanda Nunes": ("brazil",),
    "Georges St-Pierre": ("canada",),
    "Khabib Nurmagomedov": ("russia",),
    "Jose Aldo": ("brazil",),
    "Valentina Shevchenko": ("kyrgyzstan", "peru"),
    "Israel Adesanya": ("nigeria", "new zealand"),
    "Jiri Prochazka": ("czech",),
    "Robert Whittaker": ("australia", "new zealand"),
    "Belal Muhammad": ("united states",),
}


def smoke_ufcstats():
    print("=== ufcstats.com: listing page + fighter pages ===")
    scraper = FighterDetailsScraper()
    scraper.fighter_group_urls = [
        "http://ufcstats.com/statistics/fighters?char=t&page=all"
    ]
    links = scraper._get_fighter_name_and_link()
    print(f"fighters found on char=t listing: {len(links)}")
    assert len(links) > 50, "listing page parse came back near-empty"

    checked = 0
    for name, url in list(links.items())[:3]:
        _, data = scraper._get_fighter_data_task(name, url)
        print(f"  {name}: {len(data)} fields -> {data}")
        assert len(data) == len(scraper.HEADER), (
            f"fighter page parse broke for {name}: {len(data)} fields, "
            f"expected {len(scraper.HEADER)}"
        )
        checked += 1
    print(f"OK: listing + {checked} fighter pages parse\n")


def smoke_wikidata():
    print("=== Wikidata: nationality panel ===")
    resolved, matched = 0, 0
    for name, expected in KNOWN_FIGHTERS.items():
        country = get_fighter_country(name)
        ok = country and any(e in country.lower() for e in expected)
        resolved += bool(country)
        matched += bool(ok)
        print(f"  {name:>24}: {country or '(not found)':<40} "
              f"{'OK' if ok else 'MISMATCH' if country else ''}")
    n = len(KNOWN_FIGHTERS)
    print(f"\nresolved {resolved}/{n}, expected-country matches {matched}/{n}")
    assert resolved >= 0.7 * n, "too many well-known fighters failed to resolve"
    assert matched >= 0.8 * resolved, "too many resolved fighters got the wrong country"
    print("OK: Wikidata lookups\n")


def full_scrape():
    print("=== FULL fighter scrape (ufcstats + Wikidata) ===")
    FighterDetailsScraper().create_fighter_data_csv()

    import pandas as pd
    df = pd.read_csv("data/raw_fighter_details.csv", index_col="fighter_name")
    coverage = df["Country"].notna().mean()
    print(f"\n{len(df)} fighters scraped; Country coverage {coverage:.1%}")
    print("Top countries:")
    print(df["Country"].value_counts().head(15).to_string())
    assert "Country" in df.columns and len(df) > 2000


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="run the full fighter scrape (slow)")
    args = parser.parse_args()

    if args.full:
        full_scrape()
    else:
        smoke_ufcstats()
        smoke_wikidata()
    print("SMOKE TEST PASSED")

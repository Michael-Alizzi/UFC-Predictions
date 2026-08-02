import sys

import requests
from bs4 import BeautifulSoup


# Some hosts serve bot-default user agents an empty/blocked page
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def make_soup(url: str) -> BeautifulSoup:
    # Follow redirects: ufcstats redirects http:// to https:// (and bare to
    # www.), and the old allow_redirects=False returned the empty redirect
    # body, silently scraping nothing.
    source_code = requests.get(url, headers=_HEADERS, timeout=30)
    plain_text = source_code.text.encode("ascii", "replace")
    return BeautifulSoup(plain_text, "html.parser")


def print_progress(
    iteration: int,
    total: int,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 1,
    bar_length: int = 50,
) -> None:
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    percents = f"{100 * (iteration / float(total)):.2f}"
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = f'{"█" * filled_length}{"-" * (bar_length - filled_length)}'

    sys.stdout.write(f"\r{prefix} |{bar}| {percents}% {suffix}")

    if iteration == total:
        sys.stdout.write("\n")
    sys.stdout.flush()

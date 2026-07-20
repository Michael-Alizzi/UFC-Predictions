import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def make_soup(url: str) -> BeautifulSoup:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/138 Safari/537.36"
            )
        )

        page.goto(url, wait_until="networkidle", timeout=120000)

        html = page.content()

        browser.close()

    return BeautifulSoup(html, "html.parser")

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

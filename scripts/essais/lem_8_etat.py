# /// script
# requires-python = ">=3.13"
# dependencies = ["truststore"]
# ///
"""LEM-8: polite sample of the French State property sales site.

Run with `uv run scripts/essais/lem_8_etat.py`. cessions.immobilier-etat.gouv.fr
publishes its content under Licence Ouverte 2.0 and its robots.txt allows
`/biens/`. The script reads a few list pages and at most `MAX_DETAILS` listing
pages, one request every `DELAY_SECONDS`, with a project user agent. Only
parsed fields are cached in `.cache/lem-8/etat/`: contact names, phone numbers
and emails are never kept. Prints Markdown tables to stdout.
"""

import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import truststore

# The site omits its intermediate certificate: the OS verifier fetches it.
truststore.inject_into_ssl()

SITE = "https://cessions.immobilier-etat.gouv.fr"
GEO = "https://geo.api.gouv.fr"
USER_AGENT = "homepedia-lem-8"
DELAY_SECONDS = 3
LIST_PAGES = {"active": ["/?page=0", "/?page=1"], "sold": ["/biens-vendus?page=0"]}
MAX_DETAILS = 30
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "lem-8" / "etat"
# Coordinates closer than this to the commune centre are read as a centroid.
CENTROID_METRES = 300
ARRONDISSEMENT = re.compile(r"^(751(0[1-9]|1\d|20)|132(0[1-9]|1[0-6])|6938[1-9])$")


def fetch(url: str) -> str:
    time.sleep(DELAY_SECONDS)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8", "replace")


def cached_json(name: str, build: Callable[[], Any]) -> Any:  # noqa: ANN401
    path = CACHE / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    value = build()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1))
    return value


def text_lines(page: str) -> list[str]:
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", page))
    return [line.strip() for line in text.splitlines() if line.strip()]


def after(lines: list[str], label: str) -> str | None:
    """Value on the line following an exact label, or after `label :` on the same line."""
    for index, line in enumerate(lines):
        if line.rstrip(" :") == label and index + 1 < len(lines):
            return lines[index + 1]
        if line.startswith(f"{label} :") and line != f"{label} :":
            return line.split(":", 1)[1].strip()
    return None


def list_page(path: str) -> dict:
    page = fetch(SITE + path)
    links = sorted(set(re.findall(r'href="(/biens/[^"?#]+)"', page)))
    pages = [int(n) for n in re.findall(r'href="\?page=(\d+)"', page)]
    return {"links": links, "last_page": max(pages, default=0)}


CONTACT = re.compile(r"@|\d{2}[ .]?\d{2}[ .]?\d{2}[ .]?\d{2}[ .]?\d{2}")
PLACE = re.compile(r".+ - \d[\dAB]{1,2}$")
STATUS = re.compile(r"^(Expiré|Vendu|Nouveau|Sous offre|Fini dans .+)$")
PRICE = re.compile(r"(première offre|mise à prix|prix).*€", re.I)


def sanitize(lines: list[str]) -> list[str]:
    """Keep the listing body without the manager contact block or any email or phone."""
    if "Ajouter aux favoris" in lines:
        lines = lines[lines.index("Ajouter aux favoris") + 1 :]
    if "Pièces jointes" in lines:
        lines = lines[: lines.index("Pièces jointes")]
    if "Gestionnaire de l\u2019annonce" in lines:
        head = lines.index("Gestionnaire de l\u2019annonce")
        place = next((i for i in range(head, len(lines)) if PLACE.match(lines[i])), head)
        lines = lines[:head] + lines[place:]
    return [line for line in lines if not CONTACT.search(line) or "€" in line or "m²" in line]


def listing(path: str) -> dict:
    try:
        page = fetch(SITE + path)
    except urllib.error.HTTPError as error:
        return {"path": path, "http_status": error.code}
    lat = re.search(r'data-lat="([-0-9.]+)"', page)
    lon = re.search(r'data-lon="([-0-9.]+)"', page)
    return {
        "path": path,
        "lat": float(lat.group(1)) if lat else None,
        "lon": float(lon.group(1)) if lon else None,
        "lines": sanitize(text_lines(page)),
    }


def parse_listing(record: dict) -> dict:
    lines = record["lines"]
    prices = [line for line in lines if PRICE.search(line)]
    return {
        "path": record["path"],
        "status": next((line for line in lines[:3] if STATUS.match(line)), None),
        "place": next((line for line in lines if PLACE.match(line)), None),
        "reference": after(lines, "Référence"),
        "published": after(lines, "Publié le"),
        "modified": after(lines, "Modifié le"),
        "insee": after(lines, "Code INSEE"),
        "cadastre": after(lines, "Référence cadastrale"),
        "sale_type": after(lines, "Type de vente"),
        "auction_date": after(lines, "Date d'adjudication"),
        "first_listed_year": after(lines, "Année première inscription"),
        "surface_m2": after(lines, "Surface en m²"),
        "rooms": after(lines, "Nombre de pièces"),
        "price": prices[0] if prices else None,
        "lat": record["lat"],
        "lon": record["lon"],
    }


def centre(code: str) -> tuple[float, float] | None:
    for kind in ("commune-actuelle", "arrondissement-municipal"):
        url = f"{GEO}/communes?code={code}&type={kind}&fields=centre"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            found = json.loads(response.read())
        if found:
            lon, lat = found[0]["centre"]["coordinates"]
            return lat, lon
    return None


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat = math.radians((a[0] + b[0]) / 2)
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(lat)
    return math.hypot(dx, dy)


def table(title: str, columns: list[str], rows: list[list[object]]) -> None:
    lines = [f"\n### {title}\n", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join("-" if v is None else str(v) for v in row) + " |" for row in rows]
    sys.stdout.write("\n".join(lines) + "\n")


def expect(actual: object, wanted: object) -> None:
    if actual != wanted:
        raise AssertionError(f"self-check: {actual!r} != {wanted!r}")


def self_check() -> None:
    lines = ["Référence :", "240640007", "Code INSEE", "64445", "Date d'adjudication : 18/11/2026"]
    expect(after(lines, "Référence"), "240640007")
    expect(after(lines, "Code INSEE"), "64445")
    expect(after(lines, "Date d'adjudication"), "18/11/2026")
    expect(round(metres((45.0, 4.0), (45.0, 4.01))), 787)
    block = [
        "Expiré",
        "Gestionnaire de l\u2019annonce",
        "Contact 1",
        "01.23.45.67.89",
        "contact@example.org",
        "Pau - 64",
    ]
    expect(sanitize(["Ajouter aux favoris", *block]), ["Expiré", "Pau - 64"])


def main() -> None:
    self_check()
    lists = {
        kind: [cached_json(f"list-{kind}-{i}", lambda p=p: list_page(p)) for i, p in enumerate(ps)]
        for kind, ps in LIST_PAGES.items()
    }
    paths = {
        kind: sorted({link for page in pages for link in page["links"]})
        for kind, pages in lists.items()
    }
    # Most of the budget on active listings, the rest on sold ones.
    chosen = paths["active"][: MAX_DETAILS * 2 // 3] + paths["sold"][: MAX_DETAILS // 3]
    raw = [
        cached_json("listing-" + p.removeprefix("/biens/")[:80], lambda p=p: listing(p))
        for p in chosen
    ]
    records = [parse_listing(r) for r in raw if "lines" in r]
    sold_paths = set(paths["sold"])

    table(
        "Volume visible",
        ["list", "pages read", "distinct listing links", "last page number"],
        [
            [kind, len(pages), len(paths[kind]), pages[0]["last_page"]]
            for kind, pages in lists.items()
        ],
    )

    fields = [k for k in records[0] if k != "path"] if records else []
    table(
        f"Complétude sur {len(records)} fiches",
        ["field", "filled", "examples"],
        [
            [
                field,
                f"{sum(r.get(field) not in (None, '') for r in records)}/{len(records)}",
                ", ".join(sorted({str(r[field]) for r in records if r.get(field)})[:3]),
            ]
            for field in fields
        ],
    )

    statuses = Counter((r["path"] in sold_paths, r.get("status")) for r in records)
    table(
        "Statut affiché",
        ["from list", "status", "listings"],
        [
            ["sold" if sold else "active", s, n]
            for (sold, s), n in sorted(statuses.items(), key=str)
        ],
    )

    references = Counter(r.get("reference") for r in records if r.get("reference"))
    parcels = Counter((r.get("insee"), r.get("cadastre")) for r in records if r.get("cadastre"))
    coordinates = Counter((r.get("lat"), r.get("lon")) for r in records if r.get("lat"))
    overlap = set(paths["active"]) & sold_paths
    centroid = 0
    located = 0
    for r in records:
        if r.get("lat") and r.get("insee"):
            point = centre(r["insee"])
            if point:
                located += 1
                centroid += metres(point, (r["lat"], r["lon"])) < CENTROID_METRES
    table(
        "Doublons et localisation",
        ["measure", "value"],
        [
            ["duplicate references", sum(n - 1 for n in references.values() if n > 1)],
            ["same INSEE code and parcel, several listings", sum(n > 1 for n in parcels.values())],
            [
                "identical coordinates shared by several listings",
                sum(n > 1 for n in coordinates.values()),
            ],
            ["links present in both active and sold lists", len(overlap)],
            ["listings with coordinates and INSEE code", located],
            [f"coordinates within {CENTROID_METRES} m of the commune centre", centroid],
            [
                "INSEE codes that are municipal arrondissements",
                sum(bool(ARRONDISSEMENT.match(r.get("insee") or "")) for r in records),
            ],
        ],
    )


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.13"
# dependencies = ["truststore"]
# ///
"""LEM-8: check access rules of listing portals and measure open listing datasets.

Run with `uv run scripts/essais/lem_8.py`. Prints Markdown tables to stdout.
For each portal it fetches robots.txt and the terms-of-use page once (no retry,
no browser, no bypass of anti-bot pages) and evaluates representative URLs
against robots.txt. It then measures two open datasets from data.gouv.fr.
Downloads are cached in `.cache/lem-8/`.
"""

import csv
import io
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import truststore

# cessions.immobilier-etat.gouv.fr omits its intermediate certificate: the OS
# verifier fetches it, OpenSSL alone fails. Verification stays on.
truststore.inject_into_ssl()

USER_AGENT = "homepedia-lem-8"
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "lem-8"
DELAY_SECONDS = 2

# Portal, robots host, terms-of-use URL, representative search and listing URLs.
# URL shapes come from the portals' public sitemaps and search results pages.
PORTALS = [
    (
        "Leboncoin",
        "https://www.leboncoin.fr",
        "https://www.leboncoin.fr/dc/cgu",
        ["/recherche?category=9", "/ad/ventes_immobilieres/1234567890"],
    ),
    (
        "SeLoger",
        "https://www.seloger.com",
        "https://www.seloger.com/cgu",
        [
            "/classified-search?distributionTypes=Buy",
            "/annonces/achat/appartement/lyon-1er-69/1.htm",
        ],
    ),
    (
        "PAP",
        "https://www.pap.fr",
        "https://www.pap.fr/groupe/cgu",
        ["/annonce/vente-appartements-lyon-1er-g43590", "/annonces/appartement-lyon-1er-r123"],
    ),
    (
        "Bien'ici",
        "https://www.bienici.com",
        "https://www.bienici.com/cgu",
        ["/recherche/achat/lyon-1er-69001", "/annonce/vente/lyon-1er/appartement/3pieces/ag1"],
    ),
    (
        "Logic-Immo",
        "https://www.logic-immo.com",
        "https://www.logic-immo.com/cgu",
        ["/classified-search?distributionTypes=Buy", "/detail-vente-1.htm"],
    ),
    (
        "Figaro Immobilier",
        "https://immobilier.lefigaro.fr",
        "https://immobilier.lefigaro.fr/annonces/cgu",
        ["/annonces/immobilier-vente-bien-lyon+69001.html", "/annonces/annonce-1.html"],
    ),
    (
        "ParuVendu",
        "https://www.paruvendu.fr",
        "https://www.paruvendu.fr",
        ["/immobilier/vente/lyon-69001/", "/immobilier/vente/appartement/1A1"],
    ),
    (
        "Ouest-France Immo",
        "https://www.ouestfrance-immo.com",
        "https://www.ouestfrance-immo.com",
        [
            "/acheter/appartement/lyon-69-69001/",
            "/immobilier/vente/appartement/lyon-69-69001/1.htm",
        ],
    ),
    (
        "Superimmo",
        "https://www.superimmo.com",
        "https://www.superimmo.com",
        ["/achat/rhone-alpes/rhone/lyon-1er", "/annonces/1"],
    ),
    (
        "EtreProprio",
        "https://www.etreproprio.com",
        "https://www.etreproprio.com/conditions-generales-utilisation",
        ["/annonces/lyon-1er", "/annonce-1"],
    ),
    (
        "Green-Acres",
        "https://www.green-acres.fr",
        "https://www.green-acres.fr",
        ["/fr/prog_show_properties.html?searchQuery=lyon", "/fr/properties/1.htm"],
    ),
    (
        "Immobilier des notaires",
        "https://www.immobilier.notaires.fr",
        "https://www.immobilier.notaires.fr/fr/mentions-legales",
        ["/fr/annonces-immobilieres-liste?commune=69381", "/fr/annonce-immo-vente-1"],
    ),
    (
        "Licitor (enchères judiciaires)",
        "https://www.licitor.com",
        "https://www.licitor.com/droits-auteur.html",
        ["/ventes-aux-encheres-immobilieres/paris-et-ile-de-france.html", "/annonce/1.html"],
    ),
    (
        "Cessions immobilières de l'État",
        "https://cessions.immobilier-etat.gouv.fr",
        "https://cessions.immobilier-etat.gouv.fr/mentions-legales",
        ["/?page=1", "/biens/immeuble-bourgeois-pau-centre-ville"],
    ),
]

BAILLEURVERIF = (
    "https://static.data.gouv.fr/resources/annonces-de-location-francaises-non-conformes-"
    "observatoire-bailleurverif/20260701-063316/observatoire-annonces-loyer-cumulative.csv"
)
YANPORT = (
    "https://static.data.gouv.fr/resources/t2-2019-volume-dannonces-mensuelles-par-region-et-"
    "par-portail-a-la-vente-et-a-la-location/20190731-104953/"
    "vente-loc-t2-2019-stock-dannonces-par-portail.csv"
)


def fetch(url: str) -> tuple[int, bytes]:
    """GET once with the project user agent. Returns the status even on HTTP errors."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    time.sleep(DELAY_SECONDS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def cached(url: str, name: str) -> tuple[int, bytes]:
    """Fetch a URL once and keep `status` and body in the cache."""
    path = CACHE / name
    if path.exists():
        status, _, body = path.read_bytes().partition(b"\n")
        return int(status), body
    status, body = fetch(url)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f"{status}\n".encode() + body)
    return status, body


def robots_groups(text: str) -> list[tuple[list[str], list[tuple[bool, str]]]]:
    """Parse robots.txt into (user agents, [(allow, pattern)]) groups."""
    groups: list[tuple[list[str], list[tuple[bool, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[bool, str]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif key in ("allow", "disallow") and agents:
            if value:
                rules.append((key == "allow", value))
            elif not rules:
                rules.append((True, "/"))  # Empty Disallow: everything allowed.
    if agents:
        groups.append((agents, rules))
    return groups


def pattern_regex(pattern: str) -> re.Pattern[str]:
    body = re.escape(pattern.removesuffix("$")).replace(r"\*", ".*")
    return re.compile(body + ("$" if pattern.endswith("$") else ""))


def allowed(text: str, path: str, agent: str = USER_AGENT) -> tuple[bool, str]:
    """Google-style evaluation: specific group else `*`, longest match, Allow wins ties."""
    groups = robots_groups(text)
    chosen = [rules for agents, rules in groups if any(a != "*" and a in agent for a in agents)]
    if not chosen:
        chosen = [rules for agents, rules in groups if "*" in agents]
    if not chosen:
        return True, "no group for this agent"
    best: tuple[int, bool, str] = (-1, True, "")
    for rules in chosen:
        for allow, pattern in rules:
            if pattern_regex(pattern).match(path):
                candidate = (len(pattern), allow, pattern)
                if candidate[:2] > best[:2]:
                    best = candidate
    return (True, "no matching rule") if best[0] < 0 else (best[1], best[2])


def self_check() -> None:
    sample = "User-agent: *\nDisallow: /*?*\nAllow: /annonces$\nDisallow : /annonces/\n"
    expect(allowed(sample, "/annonces"), (True, "/annonces$"))
    expect(allowed(sample, "/annonces/x")[0], False)
    expect(allowed(sample, "/recherche?q=1")[0], False)
    expect(allowed(sample, "/biens/x"), (True, "no matching rule"))
    only_google = "User-agent: Googlebot\nDisallow: /\n"
    expect(allowed(only_google, "/x"), (True, "no group for this agent"))


def page_kind(status: int, body: bytes) -> str:
    text = body[:20000].decode("utf-8", "replace").lower()
    if status in (403, 429) and ("captcha-delivery" in text or "datadome" in text):
        return f"{status} DataDome"
    if "just a moment" in text or "attention required" in text or "cf-chl" in text:
        return f"{status} Cloudflare"
    if "challenge validation" in text or "vérification" in text[:2000]:
        return f"{status} anti-bot challenge"
    return str(status)


def table(title: str, columns: list[str], rows: list[list[object]]) -> None:
    lines = [f"\n### {title}\n", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join("-" if v is None else str(v) for v in row) + " |" for row in rows]
    sys.stdout.write("\n".join(lines) + "\n")


def expect(actual: object, wanted: object) -> None:
    if actual != wanted:
        raise AssertionError(f"self-check: {actual!r} != {wanted!r}")


def portals() -> None:
    rows = []
    for name, host, terms, paths in PORTALS:
        slug = re.sub(r"\W+", "-", host.split("//")[1])
        status, body = cached(f"{host}/robots.txt", f"robots-{slug}.txt")
        text = body.decode("utf-8", "replace") if status == 200 else ""
        has_star = any("*" in agents for agents, _ in robots_groups(text))
        # Some portals state their policy in comments only (Leboncoin).
        notice = re.search(r"^#+\s*(.*(?:forbidden|interdit).*)$", text, re.I | re.M)
        verdicts = []
        for path in paths:
            ok, rule = allowed(text, path) if text else (False, "robots.txt unavailable")
            verdicts.append(f"`{path}` {'allowed' if ok else 'disallowed'} ({rule})")
        terms_status, terms_body = cached(terms, f"terms-{slug}.html")
        rows.append(
            [
                name,
                page_kind(status, body),
                "yes" if has_star else "no",
                "<br>".join(verdicts),
                notice.group(1).strip() if notice else "-",
                page_kind(terms_status, terms_body),
            ]
        )
    table(
        f"Portails : robots.txt et page de conditions (agent `{USER_AGENT}`)",
        ["portal", "robots.txt", "`*` group", "representative URLs", "comment", "terms page"],
        rows,
    )


def blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def bailleurverif() -> None:
    _, body = cached(BAILLEURVERIF, "bailleurverif-cumulative.csv")
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8"))))
    snapshots = Counter(row["ts_score"][:10] for row in rows)
    by_listing = Counter((row["source"], row["accommodation_id"]) for row in rows)
    # Same flat published under several ids: same source, postcode, surface and rent.
    signature = Counter(
        (row["source"], row["code_postal"], row["surface_m2"], row["loyer_eur_total"])
        for row in rows
    )
    fields = ["surface_m2", "loyer_eur_total", "dpe_letter", "ges_letter", "meuble", "code_postal"]
    table(
        "BailleurVérif, fichier cumulatif",
        ["measure", "value"],
        [
            ["rows", len(rows)],
            [
                "snapshots (observation dates)",
                f"{len(snapshots)}: {min(snapshots)} to {max(snapshots)}",
            ],
            ["sources", dict(Counter(row["source"] for row in rows).most_common())],
            ["distinct (source, accommodation_id)", len(by_listing)],
            ["listings seen in more than one snapshot", sum(n > 1 for n in by_listing.values())],
            ["distinct url_hash", len({row["url_hash"] for row in rows})],
            [
                "rows sharing source, postcode, surface and rent with another id",
                sum(n for n in signature.values() if n > 1),
            ],
            [
                "missing rate",
                ", ".join(
                    f"{f} {sum(blank(row.get(f)) for row in rows) / len(rows):.0%}" for f in fields
                ),
            ],
            ["finest location", "postcode and city label, no INSEE code, no coordinates"],
        ],
    )


def yanport() -> None:
    _, body = cached(YANPORT, "yanport-t2-2019.csv")
    rows = [r for r in csv.DictReader(io.StringIO(body.decode("utf-8"))) if r["Date"] == "2019-06"]
    # Sales have a FRANCE row; rentals only exist per region, so sum the regions.
    totals: Counter[tuple[str, str]] = Counter()
    for row in rows:
        national = row["Région"] == "FRANCE"
        if national == (row["Type"] == "VENTE"):
            totals[(row["Portail"], row["Type"])] += int(row["Nombre d'annonces"])
    portals_seen = sorted({portal for portal, _ in totals}, key=lambda p: -totals[(p, "VENTE")])
    table(
        "Yanport, stock d'annonces par portail, juin 2019 (métropole)",
        ["portal", "sale listings", "rental listings"],
        [[p, f"{totals[(p, 'VENTE')]:,}", f"{totals[(p, 'LOCATION')]:,}"] for p in portals_seen]
        + [
            [
                "sum over portals",
                f"{sum(v for (_, t), v in totals.items() if t == 'VENTE'):,}",
                f"{sum(v for (_, t), v in totals.items() if t == 'LOCATION'):,}",
            ]
        ],
    )


def main() -> None:
    self_check()
    portals()
    bailleurverif()
    yanport()


if __name__ == "__main__":
    main()

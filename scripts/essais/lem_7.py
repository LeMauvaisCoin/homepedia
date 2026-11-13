# /// script
# requires-python = ">=3.13"
# ///
"""LEM-7: measure candidate enrichment sources on one territorial sample.

Run with `uv run scripts/essais/lem_7.py`. Queries public APIs only and prints
Markdown tables to stdout. No API key needed.
"""

import http.client
import json
import sys
import time
import urllib.parse
from collections import Counter
from http.client import HTTPMessage
from pathlib import Path
from typing import Any

# Shared sample. Kind: COM = current commune, ARM = municipal arrondissement,
# OLD = code absorbed by a commune nouvelle on 2025-01-01 (now 25390).
SAMPLE = [
    ("69123", "Lyon", "COM"),
    ("69381", "Lyon 1er", "ARM"),
    ("75056", "Paris", "COM"),
    ("75111", "Paris 11e", "ARM"),
    ("67482", "Strasbourg", "COM"),
    ("15219", "Salers", "COM"),
    ("25390", "Pays-de-Montbenoît", "COM"),
    ("25303", "Hauterive-la-Fresse (absorbed)", "OLD"),
    ("97411", "Saint-Denis (La Réunion)", "COM"),
]

DPE = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant"
ORE = "https://opendata.agenceore.fr/data-fair/api/v1/datasets/consommation-annuelle-d-electricite-et-gaz-par-commune"
BDNB = "https://api.bdnb.io/v1/bdnb/donnees/batiment_groupe_complet"
MELODI = "https://api.insee.fr/melodi/data"
GEORISQUES = "https://georisques.gouv.fr/api/v1"
COG_COMMUNES = "https://www.insee.fr/fr/statistiques/fichier/8377162/v_commune_2025.csv"
SAMPLE_ROWS = 500
# Downloaded files, ignored by Git. Delete the folder to fetch fresh copies.
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "lem-7"


def open_url(
    url: str, headers: dict[str, str] | None = None
) -> tuple[http.client.HTTPSConnection, http.client.HTTPResponse]:
    """Open an HTTPS GET, following redirects. The caller closes the connection."""
    for _ in range(5):
        parts = urllib.parse.urlsplit(url)
        connection = http.client.HTTPSConnection(parts.netloc, timeout=120)
        target = f"{parts.path}?{parts.query}" if parts.query else parts.path
        connection.request(
            "GET", target, headers={"User-Agent": "homepedia-lem-7", **(headers or {})}
        )
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            url = urllib.parse.urljoin(url, response.headers["Location"])
            connection.close()
            continue
        return connection, response
    raise OSError(f"Too many redirects for {url}")


def fetch(url: str, headers: dict[str, str] | None = None) -> tuple[bytes, HTTPMessage]:
    """GET an HTTPS URL, retrying transient failures. Raises OSError on HTTP errors."""
    for attempt in range(3):
        connection = None
        try:
            connection, response = open_url(url, headers)
            body = response.read()
            if response.status < 400:
                return body, response.headers
            if response.status < 500 or attempt == 2:
                raise OSError(f"HTTP {response.status} for {url}")
        except TimeoutError:
            if attempt == 2:
                raise
        finally:
            if connection:
                connection.close()
        time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def download(url: str, name: str) -> Path:
    """Stream a file into the local cache once; later runs reuse it."""
    path = CACHE / name
    if path.exists():
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    connection, response = open_url(url)
    try:
        if response.status >= 400:
            raise OSError(f"HTTP {response.status} for {url}")
        partial = path.with_suffix(path.suffix + ".part")
        with partial.open("wb") as file:
            while chunk := response.read(1 << 20):
                file.write(chunk)
        partial.rename(path)
    finally:
        connection.close()
    return path


def get(
    url: str, params: dict[str, str | int] | None = None, headers: dict[str, str] | None = None
) -> tuple[Any, HTTPMessage]:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body, response_headers = fetch(url, headers)
    return json.loads(body), response_headers


def blank(value: object) -> bool:
    return value is None or value == "" or value == {}


def missing_rates(rows: list[dict], fields: list[str]) -> str:
    if not rows:
        return "-"
    return ", ".join(
        f"{field} {sum(blank(row.get(field)) for row in rows) / len(rows):.0%}" for field in fields
    )


def dpe(code: str) -> dict:
    fields = [
        "etiquette_dpe",
        "conso_5_usages_par_m2_ep",
        "surface_habitable_logement",
        "annee_construction",
        "_geopoint",
    ]
    query = f'code_insee_ban:"{code}"'
    page, _ = get(f"{DPE}/lines", {"size": SAMPLE_ROWS, "qs": query, "select": ",".join(fields)})
    rows = page["results"]
    return {
        "rows": page["total"],
        "missing": missing_rates(rows, fields),
        "zero": sum(row.get("conso_5_usages_par_m2_ep") == 0 for row in rows),
        "labels": dict(sorted(Counter(row.get("etiquette_dpe") for row in rows).items(), key=str)),
    }


def bdnb(code: str) -> dict:
    fields = [
        "classe_bilan_dpe",
        "conso_5_usages_ep_m2",
        "annee_construction",
        "nb_log",
        "usage_niveau_1_txt",
    ]
    params = {"code_commune_insee": f"eq.{code}", "select": ",".join(fields), "limit": SAMPLE_ROWS}
    rows, _ = get(BDNB, params)
    # Counting in the same request as the sample times out on large communes (Strasbourg).
    count_params = {"code_commune_insee": f"eq.{code}", "select": "batiment_groupe_id", "limit": 1}
    _, headers = get(BDNB, count_params, {"Prefer": "count=exact"})
    total = int(headers["Content-Range"].split("/")[1].replace("*", "0"))
    return {
        "rows": total,
        "missing": missing_rates(rows, fields),
        "zero": sum(row.get("nb_log") == 0 for row in rows),
    }


def melodi(dataset: str, code: str, kind: str) -> list[dict]:
    geo = f"{'ARM' if kind == 'ARM' else 'COM'}-{code}"
    try:
        page, _ = get(f"{MELODI}/{dataset}", {"GEO": geo, "maxResult": 10000})
    except OSError:
        return []
    return page.get("observations", [])


def filosofi(code: str, kind: str) -> dict:
    observations = melodi("DS_FILOSOFI_CC", code, kind)
    values = {
        o["dimensions"]["FILOSOFI_MEASURE"]: o["measures"]["OBS_VALUE_NIVEAU"] for o in observations
    }
    filled = [
        m
        for m, v in values.items()
        if not blank(v) and not blank(v.get("value") if isinstance(v, dict) else v)
    ]
    median = values.get("MED_SL")
    return {
        "rows": len(observations),
        "filled": len(filled),
        "status": dict(Counter(o["attributes"].get("OBS_STATUS") for o in observations)),
        "median": median.get("value") if isinstance(median, dict) else median,
        "year": observations[0]["dimensions"]["TIME_PERIOD"] if observations else "-",
    }


def bpe(code: str, kind: str) -> dict:
    observations = melodi("DS_BPE", code, kind)
    counts = [
        o["measures"]["OBS_VALUE_NIVEAU"].get("value")
        for o in observations
        if o["dimensions"].get("BPE_MEASURE") == "FACILITIES"
        and o["dimensions"].get("FACILITY_TYPE", "").startswith(("A", "B", "C", "D", "E", "F", "G"))
        and len(o["dimensions"].get("FACILITY_TYPE", "")) == 4
    ]
    return {
        "rows": len(observations),
        "types": len(counts),
        "facilities": sum(c or 0 for c in counts),
        "zero": sum(c == 0 for c in counts),
        "missing": sum(c is None for c in counts),
        "year": observations[0]["dimensions"]["TIME_PERIOD"] if observations else "-",
    }


def georisques(code: str) -> dict:
    risks, _ = get(f"{GEORISQUES}/gaspar/risques", {"code_insee": code})
    catnat, _ = get(f"{GEORISQUES}/gaspar/catnat", {"code_insee": code, "page_size": 1})
    radon, _ = get(f"{GEORISQUES}/radon", {"code_insee": code})
    details = risks["data"][0]["risques_detail"] if risks["data"] else []
    return {
        "risks": len(details),
        "catnat": catnat["results"] if catnat["data"] else 0,
        "radon": radon["data"][0]["classe_potentiel"] if radon["data"] else None,
        "name": (catnat["data"] or radon["data"] or [{}])[0].get("libelle_commune"),
    }


def ore(code: str) -> dict:
    page, _ = get(f"{ORE}/lines", {"size": 10000, "qs": f'code_commune:"{code}"'})
    rows = page["results"]
    years = sorted({row["annee"] for row in rows})
    last = [row for row in rows if years and row["annee"] == years[-1]]
    return {
        "rows": page["total"],
        "years": f"{years[0]}-{years[-1]}" if years else "-",
        "last_rows": len(last),
        "secret": sum(row.get("nombre_de_mailles_secretisees") or 0 for row in last),
        "zero": sum(row.get("conso_totale_mwh") == 0 for row in last),
        "null": sum(row.get("conso_totale_mwh") is None for row in last),
        "sectors": ",".join(sorted({row["code_categorie_consommation"] for row in last})),
    }


def table(title: str, columns: list[str], rows: list[list[object]]) -> None:
    lines = [f"\n### {title}\n", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join("-" if v is None else str(v) for v in row) + " |" for row in rows]
    sys.stdout.write("\n".join(lines) + "\n")


def national() -> None:
    dpe_meta, _ = get(DPE)
    ore_meta, _ = get(ORE)
    no_code, _ = get(f"{DPE}/lines", {"size": 0, "qs": "NOT _exists_:code_insee_ban"})
    cog, _ = fetch(COG_COMMUNES)
    communes = [line for line in cog.decode().splitlines() if line.startswith('"COM"')]
    table(
        "National volumes",
        ["source", "value"],
        [
            ["communes on 2025-01-01 (INSEE COG)", len(communes)],
            ["DPE rows", dpe_meta["count"]],
            [
                "DPE rows without code_insee_ban",
                f"{no_code['total']} ({no_code['total'] / dpe_meta['count']:.1%})",
            ],
            ["DPE updated", dpe_meta["dataUpdatedAt"]],
            ["ORE rows", ore_meta["count"]],
            ["ORE updated", ore_meta["dataUpdatedAt"]],
        ],
    )


def main() -> None:
    results = {code: {} for code, _, _ in SAMPLE}
    for code, _, kind in SAMPLE:
        results[code] = {
            "dpe": dpe(code),
            "bdnb": bdnb(code),
            "filosofi": filosofi(code, kind),
            "bpe": bpe(code, kind),
            "georisques": georisques(code),
            "ore": ore(code),
        }

    labels = {code: f"{name} `{code}`" for code, name, _ in SAMPLE}
    r = results
    table(
        "DPE logements existants (ADEME, dpe03existant)",
        ["territory", "rows", "missing in sample", "conso = 0", "labels in sample"],
        [
            [
                labels[c],
                r[c]["dpe"]["rows"],
                r[c]["dpe"]["missing"],
                r[c]["dpe"]["zero"],
                r[c]["dpe"]["labels"],
            ]
            for c in r
        ],
    )
    table(
        "BDNB batiment_groupe_complet",
        ["territory", "building groups", "missing in sample", "nb_log = 0"],
        [
            [labels[c], r[c]["bdnb"]["rows"], r[c]["bdnb"]["missing"], r[c]["bdnb"]["zero"]]
            for c in r
        ],
    )
    table(
        "Filosofi (INSEE Melodi, DS_FILOSOFI_CC)",
        ["territory", "year", "measures", "with value", "OBS_STATUS", "median standard of living"],
        [
            [labels[c], f["year"], f["rows"], f["filled"], f["status"], f["median"]]
            for c in r
            for f in [r[c]["filosofi"]]
        ],
    )
    table(
        "BPE (INSEE Melodi, DS_BPE)",
        [
            "territory",
            "year",
            "observations",
            "facility types",
            "facilities",
            "value = 0",
            "value missing",
        ],
        [
            [labels[c], b["year"], b["rows"], b["types"], b["facilities"], b["zero"], b["missing"]]
            for c in r
            for b in [r[c]["bpe"]]
        ],
    )
    table(
        "Géorisques (GASPAR, CatNat, radon)",
        ["territory", "listed risks", "CatNat decrees", "radon class", "name returned"],
        [
            [labels[c], g["risks"], g["catnat"], g["radon"], g["name"]]
            for c in r
            for g in [r[c]["georisques"]]
        ],
    )
    table(
        "Consommation électricité et gaz par commune (Agence ORE)",
        [
            "territory",
            "rows",
            "years",
            "rows last year",
            "secret meshes",
            "conso = 0",
            "conso null",
            "sectors",
        ],
        [
            [
                labels[c],
                o["rows"],
                o["years"],
                o["last_rows"],
                o["secret"],
                o["zero"],
                o["null"],
                o["sectors"],
            ]
            for c in r
            for o in [r[c]["ore"]]
        ],
    )
    national()


if __name__ == "__main__":
    main()

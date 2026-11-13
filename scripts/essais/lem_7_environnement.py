# /// script
# requires-python = ">=3.13"
# dependencies = ["defusedxml>=0.7"]
# ///
"""LEM-7: measure environment and spatial risk sources on the shared sample.

Run with `uv run scripts/essais/lem_7_environnement.py`. Uses public endpoints
only, no API key. Files under 500 MB are cached in `.cache/lem-7`; larger
layers are only measured from their HTTP headers.
"""

import csv
import io
import re
import zipfile
from collections import Counter

from defusedxml import ElementTree
from lem_7 import COG_COMMUNES, GEORISQUES, SAMPLE, download, fetch, get, open_url, table

GASPAR = "https://files.georisques.fr/GASPAR/gaspar.zip"
COAST_DECREE = (
    "https://static.data.gouv.fr/resources/liste-des-communes-volontaires-pour-sadapter-au-recul"
    "-du-trait-de-cote/20260218-105039/trait-de-cote-commune-2026-95.csv"
)
INEC = "https://geolittoral.din.developpement-durable.gouv.fr/telechargement/couches_sig/"
CLC_MEDIA = "https://www.statistiques.developpement-durable.gouv.fr/media/"
AIR_STATIONS = (
    "https://static.data.gouv.fr/resources/donnees-temps-reel-de-mesure-des-concentrations-de"
    "-polluants-atmospheriques-reglementes-1/20260825-130000/fr-2026-d-07082026-1.xml"
)
AIR_HOURLY = (
    "https://files.data.gouv.fr/ineris/lcsqa/concentrations-de-polluants-atmospheriques"
    "-reglementes/temps-reel/2026/FR_E2_2026-11-12.csv"
)
# Station municipality names as written in the LCSQA file, per sample code.
AIR_NAMES = {
    "69123": r"^LYON",
    "69381": r"^LYON ?(1|1ER)\b",
    "75056": r"^PARIS",
    "75111": r"^PARIS ?11",
    "67482": r"^STRASBOURG",
    "15219": r"^SALERS",
    "25390": r"MONTBENO",
    "25303": r"HAUTERIVE",
    "97411": r"^SAINT[- ]DENIS",
}


def head(url: str) -> str:
    """Size and date of a large file, without downloading its body."""
    connection, response = open_url(url)
    try:
        size = int(response.headers.get("Content-Length") or 0)
        return f"{size / 1e6:.0f} MB, {response.headers.get('Last-Modified', '-')}"
    finally:
        connection.close()


def valid_codes() -> set[str]:
    cog, _ = fetch(COG_COMMUNES)
    rows = csv.DictReader(io.StringIO(cog.decode()))
    return {row["COM"] for row in rows if row["TYPECOM"] in ("COM", "ARM")}


def risk_report(code: str) -> dict:
    """Commune-level statuses of the Géorisques risk report (12 natural hazards)."""
    try:
        report, _ = get(f"{GEORISQUES}/resultats_rapport_risque", {"code_insee": code})
    except OSError as error:
        return {"error": str(error)}
    natural = report.get("risquesNaturels") or {}

    def status(key: str) -> str:
        item = natural.get(key) or {}
        return (item.get("libelleStatutCommune") or "present") if item.get("present") else "no"

    return {
        "name": (report.get("commune") or {}).get("libelle", "-"),
        "present": sum(bool((v or {}).get("present")) for v in natural.values()),
        "rga": status("retraitGonflementArgile"),
        "flood": status("inondation"),
        "groundwater": status("remonteeNappe"),
        "coast": status("reculTraitCote"),
        "radon": status("radon"),
    }


def rga_at_centre(code: str) -> str:
    """RGA exposure at the commune centre: a point, not the commune share."""
    try:
        commune, _ = get(f"https://geo.api.gouv.fr/communes/{code}", {"fields": "centre"})
        lon, lat = commune["centre"]["coordinates"]
        rga, _ = get(f"{GEORISQUES}/rga", {"latlon": f"{lon},{lat}"})
    except (OSError, KeyError) as error:
        return f"error: {error}"
    except ValueError:
        # Empty body: the layer has no polygon there (Paris, overseas).
        return "empty response"
    return rga.get("exposition") or "no value"


def flood_api(code: str) -> dict:
    def count(path: str, params: dict[str, str | int]) -> int | str:
        try:
            page, _ = get(f"{GEORISQUES}/{path}", params)
        except OSError as error:
            return f"error {error}"
        return page.get("results", page.get("totalElements", 0))

    return {
        "tri": count("gaspar/tri", {"code_insee": code}),
        "azi": count("gaspar/azi", {"code_insee": code}),
        "pprn": count("gaspar/pprn", {"codeInsee": code}),
    }


def gaspar_files(valid: set[str]) -> tuple[list[list[object]], dict[str, dict[str, int]]]:
    """National GASPAR extract: rows, communes and codes unknown to the 2025 COG."""
    archive = zipfile.ZipFile(download(GASPAR, "gaspar.zip"))
    summary, per_code = [], {code: {} for code, _, _ in SAMPLE}
    for name in archive.namelist():
        kind = name.split("_gaspar")[0]
        with archive.open(name) as file:
            rows = list(csv.DictReader(io.TextIOWrapper(file, "utf-8"), delimiter=";"))
        column = next(
            c for c in ("cod_commune", "code_commune", "CODE INSEE COMMUNE") if c in rows[0]
        )
        codes = Counter(row[column] for row in rows)
        unknown = [c for c in codes if c not in valid]
        summary.append([name, len(rows), len(codes), len(unknown), sum(codes[c] for c in unknown)])
        for code in per_code:
            per_code[code][kind] = codes.get(code, 0)
    return summary, per_code


def coast_decree() -> tuple[int, int, set[str]]:
    body, _ = fetch(COAST_DECREE)
    rows = list(csv.DictReader(io.StringIO(body.decode())))
    active = {row["code_commune"] for row in rows if row["is_currently_active"] == "True"}
    return len(rows), len(active), active


def clc(valid: set[str]) -> tuple[list[list[object]], dict[str, str]]:
    """CORINE Land Cover statistics by commune (5 classes), metropole and overseas."""
    metro = download(f"{CLC_MEDIA}2546/download?inline", "clc_communes_metropole_5.csv")
    drom_zip = zipfile.ZipFile(
        download(f"{CLC_MEDIA}2549/download?inline", "clc_communes_drom_5.zip")
    )
    drom_text = drom_zip.read(drom_zip.namelist()[0]).decode("utf-8", "replace")
    # Both files have 3 header lines (label, type, unit) before the technical names.
    rows = list(csv.DictReader(metro.read_text("utf-8", "replace").splitlines()[3:], delimiter=";"))
    drom = list(csv.DictReader(drom_text.splitlines()[3:], delimiter=";"))
    years = Counter(row["ANNEE"] for row in rows)
    latest = max(years)
    latest_rows = [row for row in rows if row["ANNEE"] == latest]
    codes = {row["NUM_COM"] for row in latest_rows}
    classes = [f"CLC_{i}" for i in range(1, 6)]
    cells = [row[c] for row in latest_rows for c in classes]
    summary = [
        ["metropole rows", len(rows)],
        ["years", dict(sorted(years.items()))],
        [f"communes in {latest}", len(codes)],
        [f"codes unknown to COG 2025 in {latest}", len(codes - valid)],
        [
            f"current communes missing in {latest} (metropole)",
            len({c for c in valid if not c.startswith("97")} - codes),
        ],
        ["empty class cells", sum(v == "" for v in cells)],
        ["zero class cells", sum(v in ("0", "0.0") for v in cells)],
        ["overseas rows (all years, incl. revised)", len(drom)],
        ["overseas extra class CLC_9 (no data)", "CLC_9" in drom[0]],
    ]
    per_code = {}
    for code, _, _ in SAMPLE:
        row = next((r for r in latest_rows if r["NUM_COM"] == code), None)
        if row is None and code.startswith("97"):
            row = next((r for r in drom if r["NUM_COM"] == code and r["ANNEE"] == latest), None)
        per_code[code] = (
            "absent" if row is None else "; ".join(f"{c}={row.get(c) or 'empty'}" for c in classes)
        )
    return summary, per_code


def air() -> tuple[list[list[object]], dict[str, str]]:
    """LCSQA station metadata: stations carry a municipality name and a point, no INSEE code."""
    tree = ElementTree.parse(download(AIR_STATIONS, "lcsqa_stations_d.xml"))
    ns = {
        "aqd": "http://dd.eionet.europa.eu/schemaset/id2011850eu-1.0",
        "ef": "http://inspire.ec.europa.eu/schemas/ef/3.0",
        "gml": "http://www.opengis.net/gml/3.2",
    }
    stations = []
    for station in tree.getroot().iter(f"{{{ns['aqd']}}}AQD_Station"):
        end = station.find(".//gml:endPosition", ns)
        position = station.find(".//gml:pos", ns)
        stations.append(
            {
                "town": (station.findtext("aqd:municipality", "", ns) or "").upper(),
                "active": end is None or not (end.text or "").strip(),
                "lat": float(position.text.split()[0])
                if position is not None and position.text
                else None,
            }
        )
    active = [s for s in stations if s["active"]]
    hourly, _ = fetch(AIR_HOURLY)
    hourly_rows = list(csv.DictReader(io.StringIO(hourly.decode("utf-8-sig")), delimiter=";"))
    summary = [
        ["stations in metadata", len(stations)],
        ["active stations (no end date)", len(active)],
        ["active stations without municipality", sum(not s["town"] for s in active)],
        ["hourly file 2026-11-12: rows", len(hourly_rows)],
        ["hourly file: sites", len({r["code site"] for r in hourly_rows})],
        ["hourly file: commune column", any("commune" in k.lower() for k in hourly_rows[0])],
    ]
    per_code = {}
    for code, pattern in AIR_NAMES.items():
        matches = [s for s in active if re.search(pattern, s["town"])]
        if code == "97411":
            matches = [s for s in matches if s["lat"] is not None and s["lat"] < 0]
        per_code[code] = str(len(matches))
    return summary, per_code


def climate() -> list[list[object]]:
    drias, _ = get(
        "https://www.data.gouv.fr/api/1/datasets/drias-projections-climatiques-pour-ladaptation-de-nos-societes/"
    )
    portal, _ = fetch("https://www.drias-climat.fr/commande")
    tracc, _ = get(
        "https://www.data.gouv.fr/api/1/datasets/indicateurs-de-debits-futurs-explore2-tracc-agreges-par-territoire/"
    )
    return [
        ["DRIAS on data.gouv: resource formats", sorted({r["format"] for r in drias["resources"]})],
        ["DRIAS order page asks for a login", b"login" in portal.lower()],
        ["Explore2 TRACC river flows: formats", sorted({r["format"] for r in tracc["resources"]})],
        ["Explore2 TRACC river flows: updated", tracc["last_update"][:10]],
    ]


def main() -> None:
    valid = valid_codes()
    labels = {code: f"{name} `{code}`" for code, name, _ in SAMPLE}
    gaspar_summary, gaspar_codes = gaspar_files(valid)
    decree_rows, decree_active, decree_codes = coast_decree()
    clc_summary, clc_codes = clc(valid)
    air_summary, air_codes = air()

    rows = []
    for code, _, _ in SAMPLE:
        report = risk_report(code)
        flood = flood_api(code)
        rows.append(
            [
                labels[code],
                report.get("name", report.get("error")),
                report.get("present"),
                report.get("rga"),
                rga_at_centre(code),
                report.get("flood"),
                flood["tri"],
                flood["azi"],
                flood["pprn"],
                report.get("groundwater"),
                report.get("coast"),
                "yes" if code in decree_codes else "no",
            ]
        )
    table(
        "Géorisques risk report by commune, RGA, flood and coast",
        [
            "territory",
            "name returned",
            "natural risks present",
            "RGA (report)",
            "RGA at centre",
            "flood (report)",
            "TRI",
            "AZI",
            "PPRN",
            "groundwater",
            "coast retreat",
            "in 2026 decree",
        ],
        rows,
    )
    table(
        "GASPAR national extract (gaspar.zip, rows per sample code)",
        ["territory", *gaspar_codes[SAMPLE[0][0]].keys()],
        [[labels[c], *gaspar_codes[c].values()] for c, _, _ in SAMPLE],
    )
    table(
        "GASPAR national files",
        ["file", "rows", "distinct communes", "codes unknown to COG 2025", "rows on those codes"],
        gaspar_summary,
    )
    table(
        "Coast retreat: decree list and INEC 2026 layers",
        ["item", "value"],
        [
            ["communes listed (all decrees)", decree_rows],
            ["communes in the active decree", decree_active],
            [
                "INEC metropole layer",
                head(f"{INEC}N_evol-INEC-2026_8periodes_metropole_espg2154_S.zip"),
            ],
            [
                "INEC Réunion layer",
                head(f"{INEC}N_evol-INEC-2026_8periodes_reunion_espg2975_S.zip"),
            ],
        ],
    )
    table("CORINE Land Cover statistics by commune (5 classes)", ["item", "value"], clc_summary)
    table(
        "CORINE Land Cover, latest year, hectares per class",
        ["territory", "classes"],
        [[labels[c], clc_codes[c]] for c, _, _ in SAMPLE],
    )
    table(
        "Large spatial layers (headers only)",
        ["layer", "size and date"],
        [
            ["CLC 2018 metropole shapefile", head(f"{CLC_MEDIA}9687/download?inline")],
            [
                "RGA 2026 risk map (pmtiles)",
                head(
                    "https://static.data.gouv.fr/resources/carte-des-risques-retrait-gonflement-des-argiles"
                    "-2026/20260401-081931/argile-2026.pmtiles"
                ),
            ],
        ],
    )
    table("Air quality: LCSQA stations and hourly file", ["item", "value"], air_summary)
    table(
        "Air quality: active stations matched by municipality name",
        ["territory", "active stations"],
        [[labels[c], air_codes[c]] for c, _, _ in SAMPLE],
    )
    table("Climate projections access", ["item", "value"], climate())


if __name__ == "__main__":
    main()

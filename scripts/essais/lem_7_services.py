# /// script
# requires-python = ">=3.13"
# dependencies = ["openpyxl"]
# ///
"""LEM-7, services and infrastructure: measure group B sources on the shared sample.

Run with `uv run scripts/essais/lem_7_services.py`. Large files are cached in
`.cache/lem-7/`. Prints Markdown tables to stdout.
"""

import csv
import gzip
import struct
import zipfile
from collections import Counter

import openpyxl
from lem_7 import SAMPLE, download, get, table

CODES = [code for code, _, _ in SAMPLE]
LABELS = {code: f"{name} `{code}`" for code, name, _ in SAMPLE}
EDUCATION = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets"
STATIC = "https://static.data.gouv.fr/resources"
APL = (
    "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
    "530_l-accessibilite-potentielle-localisee-apl/attachments/"
    "indicateur_d_apl_aux_medecins_generalistes_xlsx"
)
FINESS = (
    f"{STATIC}/finess-extraction-du-fichier-des-etablissements/20260512-091152/"
    "etalab-cs1100507-stock-20260512-0339.csv"
)
DELINQUANCE = (
    f"{STATIC}/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-"
    "enregistree-par-la-police-et-la-gendarmerie-nationales/20260709-115942/"
    "donnee-data.gouv-2025-geographie2026-produit-le2026-06-25.csv.gz"
)
ARCEP = (
    f"{STATIC}/le-marche-du-haut-et-tres-haut-debit-fixe-deploiements/20260910-162103/"
    "2026t2-commune.zip"
)
IRVE = (
    f"{STATIC}/base-nationale-des-irve-data-gouv-infrastructures-de-recharge-pour-vehicules-"
    "electriques-donnees-statiques/20261112-053200/"
    "consolidation-etalab-schema-irve-statique-v-2.3.1-20261112.csv"
)
STOPS = (
    f"{STATIC}/arrets-de-transport-en-france/20260113-104155/"
    "gtfs-stops-france-export-2026-01-13.csv"
)
HUBEAU = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/resultats_dis"


def number(value: object) -> float | None:
    """Parse French and English decimals; None for empty or non-numeric markers."""
    if value is None:
        return None
    text = str(value).replace("%", "").replace(",", ".").strip()
    try:
        return float(text)
    except ValueError:
        return None


def education(dataset: str, code_field: str, year_field: str, value_field: str) -> dict:
    """Rows of the latest year for each sample code, from the Opendatasoft API."""
    url = f"{EDUCATION}/{dataset}/records"
    latest = get(url, {"order_by": f"{year_field} desc", "limit": 1})[0]["results"][0][year_field]
    meta = get(url, {"limit": 0})[0]["total_count"]
    result = {"dataset": dataset, "total": meta, "latest": latest, "codes": {}}
    for code in CODES:
        # IVAL stores the year as a date: compare years, not strings.
        year = (
            f"year({year_field})={latest}" if year_field == "annee" else f'{year_field}="{latest}"'
        )
        where = f'{code_field}="{code}" and {year}'
        page = get(url, {"where": where, "limit": 100})[0]
        values = [number(row.get(value_field)) for row in page["results"]]
        result["codes"][code] = {
            "rows": page["total_count"],
            "missing": sum(v is None for v in values),
            "zero": sum(v == 0 for v in values),
        }
    return result


def finess() -> dict:
    """Health and social facilities; the INSEE code is rebuilt from department + commune."""
    path = download(FINESS, "finess.csv")
    counts: Counter[str] = Counter()
    categories: dict[str, Counter[str]] = {code: Counter() for code in CODES}
    total = 0
    with path.open(encoding="utf-8", errors="replace") as file:
        for row in csv.reader(file, delimiter=";"):
            if row[0] != "structureet":
                continue
            total += 1
            department, commune = row[13], row[12]
            # Overseas departments are coded 9A..9F: the INSEE code starts with 97.
            code = (
                "97" if department[0] == "9" and department[1].isalpha() else department
            ) + commune
            counts[code] += 1
            if code in categories:
                categories[code][row[21]] += 1
    return {"total": total, "counts": counts, "categories": categories}


def apl() -> dict:
    """APL to general practitioners, latest sheet (one row per commune)."""
    path = download(APL, "apl-mg.xlsx")
    workbook = openpyxl.load_workbook(path, read_only=True)
    sheet = workbook.worksheets[-1]
    rows = [row for row in sheet.iter_rows(min_row=11, values_only=True) if row[0]]
    by_code = {str(row[0]): row for row in rows}
    values = [number(row[2]) for row in rows]
    return {
        "sheet": sheet.title,
        "total": len(rows),
        "missing": sum(v is None for v in values),
        "zero": sum(v == 0 for v in values),
        "leading_zero_lost": sum(len(str(row[0])) != 5 for row in rows),
        "codes": {
            code: [by_code[code][2], round(by_code[code][7])] if code in by_code else None
            for code in CODES
        },
    }


def delinquance() -> dict:
    """Crime base: count indicators of the latest year and their diffusion flag."""
    path = download(DELINQUANCE, "delinquance-com.csv.gz")
    years: Counter[str] = Counter()
    national: Counter[str] = Counter()
    sample: dict[str, Counter[str]] = {code: Counter() for code in CODES}
    with gzip.open(path, "rt", encoding="utf-8") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    latest = max(row["annee"] for row in rows)
    communes = set()
    for row in rows:
        years[row["annee"]] += 1
        if row["annee"] != latest:
            continue
        communes.add(row["CODGEO_2026"])
        national[row["est_diffuse"]] += 1
        national["nombre NA"] += row["nombre"] == "NA"
        national["nombre 0"] += row["nombre"] == "0"
        if row["CODGEO_2026"] in sample:
            sample[row["CODGEO_2026"]][row["est_diffuse"]] += 1
            sample[row["CODGEO_2026"]]["zero"] += row["nombre"] == "0"
    return {
        "rows": len(rows),
        "latest": latest,
        "years": f"{min(years)}-{max(years)}",
        "communes": len(communes),
        "national": national,
        "sample": sample,
    }


def dbf_rows(raw: bytes) -> list[dict[str, str]]:
    """Minimal dBase III reader for the shapefile attribute table."""
    count, header, length = struct.unpack("<IHH", raw[4:12])
    fields, offset = [], 32
    while raw[offset] != 0x0D:
        fields.append(
            (raw[offset : offset + 11].split(b"\0")[0].decode("latin-1"), raw[offset + 16])
        )
        offset += 32
    rows = []
    for index in range(count):
        record, position, row = raw[header + index * length : header + (index + 1) * length], 1, {}
        for name, size in fields:
            row[name] = record[position : position + size].decode("latin-1").strip()
            position += size
        rows.append(row)
    return rows


def arcep() -> dict:
    archive = zipfile.ZipFile(download(ARCEP, "arcep-commune-2026t2.zip"))
    rows = dbf_rows(archive.read("communes_2026T2.dbf"))
    by_code = {row["INSEE_COM"]: row for row in rows}
    return {
        "total": len(rows),
        "arrondissements": sum(row["ID"].startswith("ARR_MUNI") for row in rows),
        "no_premises": sum(number(row["Locaux"]) in (None, 0) for row in rows),
        "couv": Counter(row["couv"].split(".")[0] for row in rows),
        "codes": {
            code: [int(float(by_code[code][key])) for key in ("Locaux", "ftth", "couv")]
            if code in by_code
            else None
            for code in CODES
        },
    }


def irve() -> dict:
    path = download(IRVE, "irve.csv")
    counts: Counter[str] = Counter()
    stations: dict[str, set[str]] = {code: set() for code in CODES}
    quality: Counter[str] = Counter()
    with path.open(encoding="utf-8") as file:
        for row in csv.DictReader(file):
            code = row["code_insee_commune"]
            quality["rows"] += 1
            quality["code empty"] += not code
            quality["code not 5 chars"] += bool(code) and len(code) != 5
            quality["code verified false"] += row["consolidated_is_code_insee_verified"] == "False"
            quality["code modified true"] += row["consolidated_is_code_insee_modified"] == "True"
            quality["power empty"] += not row["puissance_nominale"]
            counts[code] += 1
            if code in stations:
                stations[code].add(row["id_station_itinerance"])
    return {"quality": quality, "counts": counts, "stations": stations}


def stops() -> dict:
    path = download(STOPS, "stops.csv")
    with path.open(encoding="utf-8") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        quality: Counter[str] = Counter()
        datasets = set()
        for row in reader:
            quality["rows"] += 1
            quality["no coordinates"] += not (row["stop_lat"] and row["stop_lon"])
            quality["location_type 0 (stop)"] += row["location_type"] in ("", "0")
            datasets.add(row["dataset_id"])
    return {
        "size_mb": round(path.stat().st_size / 1e6),
        "commune_column": any("insee" in c or "commune" in c for c in columns),
        "datasets": len(datasets),
        "quality": quality,
    }


def water(code: str) -> dict:
    params = {
        "code_commune": code,
        "date_min_prelevement": "2025-01-01",
        "date_max_prelevement": "2025-12-31",
        "size": 1000,
    }
    page = get(HUBEAU, params)[0]
    rows = page["data"]
    below = [r for r in rows if str(r["resultat_alphanumerique"] or "").startswith("<")]
    return {
        "results 2025": page["count"],
        "below limit in sample": len(below),
        "below limit coded 0": sum(r["resultat_numerique"] == 0 for r in below),
        "numeric missing": sum(r["resultat_numerique"] is None for r in rows),
    }


def main() -> None:
    schools = [
        (
            "IPS écoles",
            education(
                "fr-en-ips-ecoles-ap2022", "code_insee_de_la_commune", "rentree_scolaire", "ips"
            ),
        ),
        (
            "IPS collèges",
            education(
                "fr-en-ips-colleges-ap2023", "code_insee_de_la_commune", "rentree_scolaire", "ips"
            ),
        ),
        ("DNB", education("fr-en-dnb-par-etablissement", "commune", "session", "taux_de_reussite")),
        (
            "IVAL lycées GT",
            education(
                "fr-en-indicateurs-de-resultat-des-lycees-gt_v2",
                "code_commune",
                "annee",
                "va_reu_total",
            ),
        ),
    ]
    table(
        "Education (data.education.gouv.fr): establishments in the latest year",
        ["dataset", "national rows", "latest year", *[LABELS[c] for c in CODES]],
        [
            [
                name,
                s["total"],
                s["latest"],
                *["{rows} (missing {missing}, 0: {zero})".format(**s["codes"][c]) for c in CODES],
            ]
            for name, s in schools
        ],
    )

    health = apl()
    table(
        f"APL to general practitioners (DREES, sheet {health['sheet']})",
        ["territory", "APL", "population"],
        [
            [
                LABELS[c],
                *(health["codes"][c] or ["absent", "-"]),
            ]
            for c in CODES
        ],
    )
    table(
        "APL national",
        ["communes", "APL missing", "APL = 0", "code not 5 chars"],
        [[health["total"], health["missing"], health["zero"], health["leading_zero_lost"]]],
    )

    facilities = finess()
    table(
        "FINESS establishments (geolocated extract)",
        ["territory", "establishments", "top categories"],
        [
            [LABELS[c], facilities["counts"][c], dict(facilities["categories"][c].most_common(3))]
            for c in CODES
        ],
    )
    table("FINESS national", ["establishments"], [[facilities["total"]]])

    crime = delinquance()
    table(
        f"Crime statistics (Ministère de l'Intérieur), year {crime['latest']}",
        ["territory", "indicators diffused", "not diffused", "count = 0"],
        [
            [
                LABELS[c],
                crime["sample"][c]["diff"],
                crime["sample"][c]["ndiff"],
                crime["sample"][c]["zero"],
            ]
            for c in CODES
        ],
    )
    table(
        "Crime statistics national",
        ["rows", "years", "communes latest year", "flags latest year"],
        [[crime["rows"], crime["years"], crime["communes"], dict(crime["national"])]],
    )

    fibre = arcep()
    table(
        "Arcep FttH deployment by commune (2026 Q2)",
        ["territory", "premises", "FttH connectable", "couv class"],
        [
            [
                LABELS[c],
                *(fibre["codes"][c] or ["absent", "-", "-"]),
            ]
            for c in CODES
        ],
    )
    table(
        "Arcep national",
        ["rows", "arrondissement rows", "premises 0 or empty", "couv classes"],
        [[fibre["total"], fibre["arrondissements"], fibre["no_premises"], dict(fibre["couv"])]],
    )

    charging = irve()
    table(
        "IRVE charging points (national consolidated base)",
        ["territory", "charging points", "stations"],
        [[LABELS[c], charging["counts"][c], len(charging["stations"][c])] for c in CODES],
    )
    table(
        "IRVE national quality",
        ["metric", "rows"],
        [[k, v] for k, v in charging["quality"].items()],
    )

    transit = stops()
    table(
        "Transit stops (national GTFS export, 2026-01-13)",
        ["file MB", "commune column", "GTFS datasets", *transit["quality"].keys()],
        [
            [
                transit["size_mb"],
                transit["commune_column"],
                transit["datasets"],
                *transit["quality"].values(),
            ]
        ],
    )

    table(
        "Drinking water results (Hub'Eau qualite_eau_potable, 2025)",
        [
            "territory",
            "results 2025",
            "below limit in sample",
            "below limit coded 0",
            "numeric missing",
        ],
        [[LABELS[c], *water(c).values()] for c in CODES],
    )


if __name__ == "__main__":
    main()

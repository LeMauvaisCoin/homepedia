# /// script
# requires-python = ">=3.13"
# ///
"""LEM-7, group A: population, economy and housing sources on the shared sample.

Run with `uv run scripts/essais/lem_7_population.py`. Downloads go to the
`.cache/lem-7/` cache (about 470 MB, mostly RNIC). Prints Markdown tables.
"""

import csv
import json
from collections import Counter
from pathlib import Path

from lem_7 import SAMPLE, blank, download, fetch, get, missing_rates, table

MELODI = "https://api.insee.fr/melodi/data"
DIDO = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datafiles"
SITADEL_HOUSING = "8b35affb-55fc-4c1f-915b-7750f974446a"
RPLS = "f3c2f2cb-8fb1-40fd-8733-964247744c9a"
STATIC = "https://static.data.gouv.fr/resources"
DATAGOUV = "https://www.data.gouv.fr/api/1/datasets"
LOVAC = (
    f"{STATIC}/logements-vacants-du-parc-prive-par-commune-departement-region-france"
    "/20260625-163627/lovac-opendata-communes26.csv"
)
RENTS = (
    f"{STATIC}/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025"
    "/20251211-145010/pred-app-mef-dhup.csv"
)
RNIC = (
    f"{STATIC}/registre-national-dimmatriculation-des-coproprietes"
    "/20260105-104918/fichier-t3-2025.csv"
)
# Statistical secrecy marker in LOVAC values.
MASKED = "s"


def melodi(dataset: str, code: str, kind: str) -> list[dict] | None:
    """Observations for one territory, or None when the API rejects the code."""
    geo = f"{'ARM' if kind == 'ARM' else 'COM'}-{code}"
    try:
        page, _ = get(f"{MELODI}/{dataset}", {"GEO": geo, "maxResult": 10000})
    except OSError:
        return None
    return page.get("observations", [])


def total(observations: list[dict], year: str, **wanted: str) -> float | None:
    """Value of the observation whose listed dimensions match and all others are `_T`."""
    for o in observations:
        dims = o["dimensions"]
        if dims["TIME_PERIOD"] != year:
            continue
        others = {k: v for k, v in dims.items() if k not in ("GEO", "FREQ", "TIME_PERIOD")}
        if all(others.get(k) == v for k, v in wanted.items()) and all(
            v == "_T" for k, v in others.items() if k not in wanted
        ):
            return o["measures"]["OBS_VALUE_NIVEAU"].get("value")
    return None


def census(code: str, kind: str) -> dict:
    housing = melodi("DS_RP_LOGEMENT_PRINC", code, kind)
    people = melodi("DS_RP_POPULATION_PRINC", code, kind)
    jobs = melodi("DS_RP_EMPLOI_LR_PRINC", code, kind)
    if housing is None or people is None or jobs is None:
        return {"status": "HTTP 400"}
    year = max(o["dimensions"]["TIME_PERIOD"] for o in housing)
    dwellings = total(housing, year, RP_MEASURE="DWELLINGS")
    vacant = total(housing, year, RP_MEASURE="DWELLINGS", OCS="DW_VAC")
    active = total(jobs, year, RP_MEASURE="POP", EMPSTA_ENQ="1T2", AGE="Y15T64")
    unemployed = total(jobs, year, RP_MEASURE="POP", EMPSTA_ENQ="2", AGE="Y15T64")
    statuses = Counter(o["attributes"].get("OBS_STATUS") for o in housing + people + jobs)
    return {
        "status": "ok",
        "years": ",".join(sorted({o["dimensions"]["TIME_PERIOD"] for o in housing})),
        "observations": len(housing) + len(people) + len(jobs),
        "population": total(people, year, RP_MEASURE="POP"),
        "dwellings": round(dwellings) if dwellings else dwellings,
        "vacancy": f"{vacant / dwellings:.1%}" if vacant is not None and dwellings else None,
        "unemployment": f"{unemployed / active:.1%}" if unemployed is not None and active else None,
        "obs_status": dict(statuses),
        "fractional": sum(
            not float(o["measures"]["OBS_VALUE_NIVEAU"].get("value", 0)).is_integer()
            for o in housing
        ),
    }


def companies(code: str, kind: str) -> dict:
    stocks = melodi("DS_SIDE_STOCKS_COM", code, kind)
    creations = melodi("DS_SIDE_CREA_COM", code, kind)
    if stocks is None or creations is None:
        return {"status": "HTTP 400"}
    stock_year = max(o["dimensions"]["TIME_PERIOD"] for o in stocks)
    creation_year = max(o["dimensions"]["TIME_PERIOD"] for o in creations)
    values = [o["measures"]["OBS_VALUE_NIVEAU"].get("value") for o in creations]
    return {
        "status": "ok",
        "establishments": total(stocks, stock_year, SIDE_MEASURE="UNIT_LOC"),
        "stock_year": stock_year,
        "creations": total(creations, creation_year, SIDE_MEASURE="BURE"),
        "creation_year": creation_year,
        "zero": sum(v == 0 for v in values),
        "missing": sum(v is None for v in values),
    }


def read_csv(path: Path, key: str) -> dict[str, dict]:
    """Rows of a semicolon CSV in Windows-1252, keyed by geographic code."""
    with path.open(encoding="cp1252", newline="") as file:
        return {row[key]: row for row in csv.DictReader(file, delimiter=";")}


def dido(datafile: str, millesime: str, code: str, columns: list[str]) -> list[dict]:
    """Rows of a SDES DiDo datafile for one commune; DiDo answers 400 on an empty result."""
    url = (
        f"{DIDO}/{datafile}/json?millesime={millesime}&{columns[0]}=eq:{code}"
        f"&columns={','.join(columns)}"
    )
    try:
        body, _ = fetch(url)
    except OSError:
        return []
    return json.loads(body)


def sitadel(code: str) -> dict:
    columns = ["COMM", "ETAT_DAU", "DATE_REELLE_AUTORISATION", "NB_LGT_TOT_CREES", "SURF_HAB_CREEE"]
    rows = dido(SITADEL_HOUSING, "2026-10", code, columns)
    years = sorted(r["DATE_REELLE_AUTORISATION"][:4] for r in rows if r["DATE_REELLE_AUTORISATION"])
    return {
        "rows": len(rows),
        "years": f"{years[0]}-{years[-1]}" if years else "-",
        "dwellings": sum(r["NB_LGT_TOT_CREES"] or 0 for r in rows),
        "surface_zero": sum(
            r["SURF_HAB_CREEE"] == 0 and (r["NB_LGT_TOT_CREES"] or 0) > 0 for r in rows
        ),
        "states": dict(sorted(Counter(r["ETAT_DAU"] for r in rows).items())),
    }


def rpls(code: str) -> dict:
    columns = ["DEPCOM", "NBPIECE", "SURFHAB", "CONSTRUCT", "DPEENERGIE", "QUALITE_XY"]
    rows = dido(RPLS, "2025-01", code, columns)
    return {"rows": len(rows), "missing": missing_rates(rows, columns[1:])}


def rnic(path: Path) -> dict[str, dict]:
    """One streaming pass over RNIC: copropriétés by `commune` and by official code."""
    codes = {code for code, _, _ in SAMPLE}
    result = {code: {"by_commune": 0, "by_official": 0, "rows": []} for code in codes}
    national = {"rows": 0, "bad_code": 0}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            national["rows"] += 1
            national["bad_code"] += len(row["commune"]) != 5
            if row["commune"] in codes:
                result[row["commune"]]["by_commune"] += 1
                result[row["commune"]]["rows"].append(row)
            if row["code_officiel_commune"] in codes:
                result[row["code_officiel_commune"]]["by_official"] += 1
    result["national"] = national
    return result


def main() -> None:
    labels = {code: f"{name} `{code}`" for code, name, _ in SAMPLE}
    lovac_path = download(LOVAC, "lovac-communes-2026.csv")
    rents_path = download(RENTS, "loyers-appartements-2025.csv")
    rnic_path = download(RNIC, "rnic-t3-2025.csv")
    lovac = read_csv(lovac_path, "CODGEO_26")
    rents = read_csv(rents_path, "INSEE_C")
    copro = rnic(rnic_path)

    rows = {code: (census(code, kind), companies(code, kind)) for code, _, kind in SAMPLE}
    table(
        "Recensement (INSEE Melodi: DS_RP_LOGEMENT_PRINC, DS_RP_POPULATION_PRINC, "
        "DS_RP_EMPLOI_LR_PRINC)",
        [
            "territory",
            "API",
            "years",
            "observations",
            "population",
            "dwellings",
            "vacant share",
            "unemployment 15-64",
            "OBS_STATUS",
            "fractional values",
        ],
        [
            [
                labels[c],
                r["status"],
                r.get("years"),
                r.get("observations"),
                r.get("population"),
                r.get("dwellings"),
                r.get("vacancy"),
                r.get("unemployment"),
                r.get("obs_status"),
                r.get("fractional"),
            ]
            for c, (r, _) in rows.items()
        ],
    )
    table(
        "Entreprises (INSEE Melodi: DS_SIDE_STOCKS_COM, DS_SIDE_CREA_COM)",
        [
            "territory",
            "API",
            "establishments",
            "stock year",
            "creations",
            "creation year",
            "value = 0",
            "value missing",
        ],
        [
            [
                labels[c],
                s["status"],
                s.get("establishments"),
                s.get("stock_year"),
                s.get("creations"),
                s.get("creation_year"),
                s.get("zero"),
                s.get("missing"),
            ]
            for c, (_, s) in rows.items()
        ],
    )

    fields = ["pp_vacant_26", "pp_vacant_plus_2ans_26", "ff_pp_total_25", "pp_vacant_25"]
    table(
        "LOVAC 2026 (logements vacants du parc privé, communes)",
        ["territory", "found", *fields],
        [[labels[c], c in lovac, *[lovac.get(c, {}).get(f) for f in fields]] for c in labels],
    )
    secret = Counter(
        f for row in lovac.values() for f in row if f.startswith("pp_") and row[f] == MASKED
    )
    table(
        "LOVAC national: rows and secrecy",
        ["field", "value"],
        [
            ["communes", len(lovac)],
            ["empty values", sum(blank(v) for r in lovac.values() for v in r.values())],
            *[[f"`{MASKED}` in {f}", n] for f, n in sorted(secret.items())[:6]],
        ],
    )

    rent_fields = [
        "loypredm2",
        "lwr.IPm2",
        "upr.IPm2",
        "TYPPRED",
        "nbobs_com",
        "nbobs_mail",
        "R2_adj",
    ]
    table(
        "Carte des loyers 2025, appartements (rent per m² incl. charges)",
        ["territory", "found", *rent_fields],
        [[labels[c], c in rents, *[rents.get(c, {}).get(f) for f in rent_fields]] for c in labels],
    )
    kinds = Counter(r["TYPPRED"] for r in rents.values())
    table(
        "Carte des loyers national: prediction level",
        ["TYPPRED", "communes"],
        [[k, n] for k, n in kinds.most_common()],
    )

    table(
        "Sitadel, autorisations créant des logements (SDES DiDo, millésime 2026-10)",
        [
            "territory",
            "authorisations",
            "years",
            "dwellings authorised",
            "surface = 0 with dwellings",
            "ETAT_DAU",
        ],
        [
            [labels[c], s["rows"], s["years"], s["dwellings"], s["surface_zero"], s["states"]]
            for c in labels
            for s in [sitadel(c)]
        ],
    )
    table(
        "RPLS, logements sociaux au 1er janvier 2025 (SDES DiDo)",
        ["territory", "dwellings", "missing"],
        [[labels[c], r["rows"], r["missing"]] for c in labels for r in [rpls(c)]],
    )
    copro_fields = ["nombre_de_lots_a_usage_d_habitation", "periode_de_construction", "lat"]
    table(
        "RNIC T3 2025 (copropriétés)",
        [
            "territory",
            "rows by `commune`",
            "rows by `code_officiel_commune`",
            "missing",
            "construction period unknown",
        ],
        [
            [
                labels[c],
                copro[c]["by_commune"],
                copro[c]["by_official"],
                missing_rates(copro[c]["rows"], copro_fields),
                sum(r["periode_de_construction"] == "NON_CONNUE" for r in copro[c]["rows"]),
            ]
            for c in labels
        ],
    )

    sirene, _ = get(
        f"{DATAGOUV}/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/"
    )
    meta = {
        name: get(f"{DIDO}/{rid}")[0]
        for name, rid in [("Sitadel housing", SITADEL_HOUSING), ("RPLS", RPLS)]
    }
    table(
        "National volumes",
        ["source", "value"],
        [
            ["LOVAC communes file (MB)", round(lovac_path.stat().st_size / 1e6, 1)],
            ["Carte des loyers communes", len(rents)],
            ["RNIC rows", copro["national"]["rows"]],
            ["RNIC rows with `commune` not 5 characters", copro["national"]["bad_code"]],
            ["RNIC file (MB)", round(rnic_path.stat().st_size / 1e6)],
            *[[f"{n} rows", m["rows"]] for n, m in meta.items()],
            *[[f"{n} last modified", m["last_modified"][:10]] for n, m in meta.items()],
            *[
                [f"SIRENE {r['title'][:60]} (MB)", round(r["filesize"] / 1e6)]
                for r in sirene["resources"]
                if r["format"] == "parquet"
                and ("Etablissement -" in r["title"] or "UniteLegale -" in r["title"])
            ],
            ["SIRENE last update", sirene["last_update"][:10]],
        ],
    )


if __name__ == "__main__":
    main()

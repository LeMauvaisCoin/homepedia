# /// script
# requires-python = ">=3.13"
# ///
"""LEM-6, geography: inspect INSEE COG 2025, commune movements, and boundary sources.

Run with `uv run scripts/essais/lem_6_geo.py`. Downloads INSEE COG 2025 tables, Etalab
administrative GeoJSON contours, and sample features from the IGN Géoplateforme WFS
and API Géo. Files are cached in `.cache/lem-6/geo/` (ignored by Git). Prints Markdown
tables to stdout.
"""

import csv
import gzip
import json
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

from lem_7 import open_url, table

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "lem-6" / "geo"

COG_BASE = "https://www.insee.fr/fr/statistiques/fichier/8377162"
COG_FILES = {
    "communes": f"{COG_BASE}/v_commune_2025.csv",
    "movements": f"{COG_BASE}/v_mvt_commune_2025.csv",
    "departements": f"{COG_BASE}/v_departement_2025.csv",
    "regions": f"{COG_BASE}/v_region_2025.csv",
    "ctcd": f"{COG_BASE}/v_ctcd_2025.csv",
}

ETALAB_BASE = "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/latest/geojson"
ETALAB_CONTOURS = {
    "communes-100m": f"{ETALAB_BASE}/communes-100m.geojson.gz",
    "departements-100m": f"{ETALAB_BASE}/departements-100m.geojson.gz",
    "regions-100m": f"{ETALAB_BASE}/regions-100m.geojson.gz",
}
ETALAB_SIZES = [
    "communes-1000m.geojson.gz",
    "communes-100m.geojson.gz",
    "communes-50m.geojson.gz",
    "communes-5m.geojson.gz",
    "departements-100m.geojson.gz",
    "regions-100m.geojson.gz",
    "epci-100m.geojson.gz",
]

WFS = "https://data.geopf.fr/wfs/ows"
WFS_PAGE_SIZE = 500

# Shared LEM-7 sample plus Marseille, Marseille 5e, and Mayotte (uncovered by DVF).
GEO_SAMPLE = [
    ("69123", "Lyon", "COM"),
    ("69381", "Lyon 1er", "ARM"),
    ("75056", "Paris", "COM"),
    ("75111", "Paris 11e", "ARM"),
    ("13055", "Marseille", "COM"),
    ("13205", "Marseille 5e", "ARM"),
    ("67482", "Strasbourg", "COM"),
    ("15219", "Salers", "COM"),
    ("25390", "Pays-de-Montbenoît", "COM"),
    ("25303", "Hauterive-la-Fresse (absorbed 2025)", "OLD"),
    ("97411", "Saint-Denis (La Réunion)", "COM"),
    ("97611", "Mamoudzou (Mayotte)", "COM"),
]


def download(url: str, path: Path) -> Path:
    """Download a file into the local cache once; later runs reuse it."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection, response = open_url(url, headers={"User-Agent": "homepedia-lem-6"})
    try:
        if response.status >= 400:
            raise OSError(f"HTTP {response.status} for {url}")
        partial = path.with_suffix(path.suffix + ".part")
        with partial.open("wb") as handle:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
        partial.rename(path)
    finally:
        connection.close()
    return path


def head_size(url: str) -> int | None:
    """Fetch Content-Length via GET range request without downloading the full payload."""
    connection, response = open_url(
        url,
        headers={"User-Agent": "homepedia-lem-6", "Range": "bytes=0-0"},
    )
    try:
        content_range = response.headers.get("Content-Range")
        if content_range and "/" in content_range:
            total = content_range.rsplit("/", 1)[1]
            return int(total) if total.isdigit() else None
        length = response.headers.get("Content-Length")
        return int(length) if length and length.isdigit() else None
    finally:
        connection.close()


def read_csv_rows(name: str) -> list[dict[str, str]]:
    path = download(COG_FILES[name], CACHE / f"{name}.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_cog() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, str]]:
    """Return active communes, municipal arrondissements, and retired->current COM aliases.

    Active COG 2025 communes are never remapped. Movements are applied chronologically by
    effective date so code re-uses (e.g. chef-lieu changes like 49069 -> 49126) resolve
    cleanly without cycles, while ambiguous splits (one code splitting into several targets
    on the same date) stay unresolved.
    """
    communes: dict[str, dict[str, str]] = {}
    arrondissements: dict[str, dict[str, str]] = {}
    for row in read_csv_rows("communes"):
        if row["TYPECOM"] == "COM":
            communes[row["COM"]] = row
        elif row["TYPECOM"] == "ARM":
            arrondissements[row["COM"]] = row

    by_date: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in read_csv_rows("movements"):
        if row["TYPECOM_AV"] == "COM" and row["TYPECOM_AP"] == "COM":
            src, dst = row["COM_AV"], row["COM_AP"]
            if src and dst:
                by_date[row["DATE_EFF"]][src].add(dst)

    # Track current target for every retired code; None marks an ambiguous split.
    alias: dict[str, str | None] = {}
    for date_eff in sorted(by_date):
        events = by_date[date_eff]
        step_map: dict[str, str | None] = {}
        for src, targets in events.items():
            if len(targets) > 1:
                step_map[src] = None
            else:
                dst = next(iter(targets))
                if dst != src:
                    step_map[src] = dst

        if not step_map:
            continue

        # Collapse same-day transitive chains (e.g. 49144 -> 44225 -> 44180 on 2018-01-01).
        collapsed_step: dict[str, str | None] = {}
        for src in step_map:
            cur: str | None = src
            seen: set[str] = set()
            while cur is not None and cur in step_map:
                if cur in seen:
                    cur = None
                    break
                seen.add(cur)
                cur = step_map[cur]
            collapsed_step[src] = cur

        # Update existing pointers in place for this effective date.
        for old_code, cur_target in list(alias.items()):
            if cur_target is not None and cur_target in collapsed_step:
                alias[old_code] = collapsed_step[cur_target]
        for src, dst in collapsed_step.items():
            alias[src] = dst

    resolved = {
        src: dst
        for src, dst in alias.items()
        if src not in communes and dst is not None and dst in communes
    }
    return communes, arrondissements, resolved


def wfs_count(layer: str, cql: str | None = None) -> int:
    """Return total feature count (`numberMatched`) of a Géoplateforme WFS layer."""
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer,
        "resultType": "hits",
    }
    if cql:
        params["CQL_FILTER"] = cql
    url = f"{WFS}?{urllib.parse.urlencode(params)}"
    connection, response = open_url(url, headers={"User-Agent": "homepedia-lem-6"})
    try:
        if response.status >= 400:
            raise OSError(f"HTTP {response.status} for {url}")
        body = response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()
    marker = 'numberMatched="'
    start = body.find(marker)
    if start < 0:
        raise ValueError(f"Missing numberMatched in WFS response for {layer}")
    end = body.find('"', start + len(marker))
    if end < 0:
        raise ValueError(f"Unterminated numberMatched in WFS response for {layer}")
    value = body[start + len(marker) : end]
    if not value.isdigit():
        raise ValueError(f"Invalid numberMatched={value!r} for {layer}")
    return int(value)


def wfs_properties(layer: str, cql: str, prop: str) -> list[dict[str, object]]:
    """Fetch all matching WFS feature properties, paging when results exceed WFS_PAGE_SIZE."""
    rows: list[dict[str, object]] = []
    while True:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "outputFormat": "application/json",
            "typeNames": layer,
            "propertyName": prop,
            "CQL_FILTER": cql,
            "count": str(WFS_PAGE_SIZE),
            "startIndex": str(len(rows)),
        }
        url = f"{WFS}?{urllib.parse.urlencode(params)}"
        connection, response = open_url(url, headers={"User-Agent": "homepedia-lem-6"})
        try:
            if response.status >= 400:
                raise OSError(f"HTTP {response.status} for {url}")
            data = json.loads(response.read())
        finally:
            connection.close()
        if not isinstance(data, dict) or not isinstance(data.get("features"), list):
            raise ValueError(f"Missing features list in WFS response for {layer}")
        page = [feature["properties"] for feature in data["features"]]
        rows.extend(page)
        if len(page) < WFS_PAGE_SIZE:
            return rows


def inspect_cog() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, str]]:
    com_rows = read_csv_rows("communes")
    dep_rows = read_csv_rows("departements")
    reg_rows = read_csv_rows("regions")
    ctcd_rows = read_csv_rows("ctcd")
    mvt_rows = read_csv_rows("movements")
    communes, arrondissements, resolved = load_cog()

    by_type = Counter(row["TYPECOM"] for row in com_rows)
    ctcd_rhone = [
        f"{row['CTCD']} ({row['LIBELLE']})" for row in ctcd_rows if row["CTCD"].startswith("69")
    ]
    com_69 = Counter(row["CTCD"] for row in communes.values() if row["DEP"] == "69")

    table(
        "INSEE COG 2025 inventory",
        ["level", "count", "notes"],
        [
            ["Regions (`REG`)", len(reg_rows), "13 metropolitan + 5 overseas (01, 02, 03, 04, 06)"],
            ["Departments (`DEP`)", len(dep_rows), "96 metropolitan (incl. 2A, 2B) + 5 overseas"],
            ["Territorial collectivities (`CTCD`)", len(ctcd_rows), ", ".join(ctcd_rhone)],
            ["Active communes (`COM`)", by_type["COM"], f"Dept 69 split: {dict(com_69)}"],
            [
                "Municipal arrondissements (`ARM`)",
                by_type["ARM"],
                "Paris 20, Lyon 9, Marseille 16 (`COMPARENT` links to parent `COM`)",
            ],
            [
                "Associated / delegated communes (`COMA`, `COMD`)",
                by_type["COMA"] + by_type["COMD"],
                "Historical sub-communes",
            ],
            [
                "Historical commune movements (`v_mvt_commune`)",
                len(mvt_rows),
                f"{len(resolved)} retired codes unambiguously mapped to a current COM",
            ],
        ],
    )
    return communes, arrondissements, resolved


def inspect_contours(
    communes: dict[str, dict[str, str]],
    arrondissements: dict[str, dict[str, str]],
    resolved: dict[str, str],
) -> None:
    size_rows = []
    for filename in ETALAB_SIZES:
        size = head_size(f"{ETALAB_BASE}/{filename}")
        size_mb = f"{size / 1e6:.2f} MB" if size is not None else "-"
        size_rows.append([filename, size_mb])
    table("Etalab administrative GeoJSON sizes (compressed)", ["file", "size"], size_rows)

    contour_codes: dict[str, set[str]] = {}
    summary_rows = []
    for key, url in ETALAB_CONTOURS.items():
        path = download(url, CACHE / f"{key}.geojson.gz")
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            fc = json.load(handle)
        codes = {str(feat["properties"]["code"]) for feat in fc["features"]}
        contour_codes[key] = codes
        has_arm = len(codes & set(arrondissements))
        summary_rows.append([key, len(fc["features"]), len(codes), has_arm])

    wfs_com_count = wfs_count("ADMINEXPRESS-COG-CARTO.LATEST:commune")
    wfs_arm_count = wfs_count("ADMINEXPRESS-COG-CARTO.LATEST:arrondissement_municipal")
    wfs_iris_count = wfs_count("STATISTICALUNITS.IRIS:contours_iris")

    summary_rows.extend(
        [
            ["IGN WFS `commune`", wfs_com_count, wfs_com_count, 0],
            ["IGN WFS `arrondissement_municipal`", wfs_arm_count, wfs_arm_count, wfs_arm_count],
            ["IGN WFS `contours_iris`", wfs_iris_count, wfs_iris_count, "-"],
        ]
    )
    table(
        "Contour sources coverage",
        ["source", "features", "distinct codes", "ARM codes included"],
        summary_rows,
    )

    com_geo = contour_codes["communes-100m"]
    missing_com = sorted(set(communes) - com_geo)
    extra_com = sorted(com_geo - set(communes))
    table(
        "Etalab `communes-100m` vs INSEE COG 2025 `COM`",
        ["check", "count", "examples"],
        [
            ["COG 2025 `COM` matched in `communes-100m`", len(set(communes) & com_geo), "-"],
            [
                "COG 2025 `COM` missing from `communes-100m`",
                len(missing_com),
                ", ".join(missing_com[:5]) or "-",
            ],
            [
                "Codes in `communes-100m` absent from COG 2025 `COM`",
                len(extra_com),
                ", ".join(extra_com[:5]) or "-",
            ],
        ],
    )

    sample_rows = []
    for code, name, kind in GEO_SAMPLE:
        cog_status = (
            "COM"
            if code in communes
            else f"ARM -> {arrondissements[code]['COMPARENT']}"
            if code in arrondissements
            else f"OLD -> {resolved[code]}"
            if code in resolved
            else "unknown"
        )
        in_etalab = "yes" if code in com_geo else "no"
        iris_total = wfs_count("STATISTICALUNITS.IRIS:contours_iris", f"code_insee='{code}'")
        if iris_total > 0:
            iris_props = wfs_properties(
                "STATISTICALUNITS.IRIS:contours_iris",
                f"code_insee='{code}'",
                "code_iris,type_iris",
            )
            iris_types = ",".join(sorted({str(p["type_iris"]) for p in iris_props}))
            iris_desc = f"{iris_total} ({iris_types})"
        else:
            iris_desc = "0"
        sample_rows.append([code, name, kind, cog_status, in_etalab, iris_desc])
    table(
        "Sample territories in COG 2025, Etalab contours, and IGN IRIS",
        [
            "code",
            "territory",
            "kind",
            "COG 2025",
            "in Etalab `communes-100m`",
            "IGN IRIS count (types)",
        ],
        sample_rows,
    )


def main() -> None:
    communes, arrondissements, resolved = inspect_cog()
    inspect_contours(communes, arrondissements, resolved)


if __name__ == "__main__":
    main()

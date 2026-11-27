# /// script
# requires-python = ">=3.13"
# ///
"""LEM-6, sales: measure DVF géolocalisée coverage, duplicates, multi-unit sales, and €/m² rules.

Run with `uv run scripts/essais/lem_6.py`. Downloads the official Etalab DVF géolocalisée
national CSV.gz files for 2024, 2025, and S1 2026 (plus dataset metadata for the full
5-year rolling window July 2021 - June 2026) into `.cache/lem-6/` (ignored by Git).
Prints Markdown tables to stdout.
"""

import csv
import gzip
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lem_6_geo import GEO_SAMPLE, load_cog
from lem_7 import open_url, table

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "lem-6"

GEODVF_DATASET_API = "https://www.data.gouv.fr/api/1/datasets/5cc1b94a634f4165e96436c1/"
DVF_RAW_DATASET_API = "https://www.data.gouv.fr/api/1/datasets/5c4ae55a634f4117716d5656/"

# Pinned October 2026 delivery of DVF géolocalisée (2.5 recent years crossing the 2025-01-01 COG).
DVF_FILES = [
    (
        "2024",
        "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20261020-114532/full-2024.csv.gz",
    ),
    (
        "2025",
        "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20261020-114721/full-2025.csv.gz",
    ),
    (
        "2026-S1",
        "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20261020-114825/full-2026-s1.csv.gz",
    ),
]

COMPLETENESS_FIELDS = [
    "valeur_fonciere",
    "code_commune",
    "id_parcelle",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "surface_terrain",
    "adresse_numero",
    "adresse_nom_voie",
    "latitude",
    "longitude",
]

RESIDENTIAL_TYPES = {"Maison", "Appartement"}
# Empirical sanity bounds tested on the national distribution.
MIN_SURFACE_M2 = 9.0
MAX_SURFACE_M2 = 1000.0
MIN_PRICE_EUR = 1000.0
MIN_PRICE_PER_M2 = 200.0
MAX_PRICE_PER_M2 = 35_000.0
# Sample departments for hierarchy averaging test (averaging commune medians vs true dept median).
HIERARCHY_DEPTS = ("15", "69", "75", "974")

DwellingKey = tuple[str, str, str, str, str, str, str, str, str, str]
LandUseKey = tuple[str, str, str]


@dataclass
class MutationAgg:
    """Per-mutation summary built in one streaming pass over DVF rows.

    Residential rows are tracked by `(dwelling_key, land_use_key)` so pure DGFiP land-use
    repeats (same physical house repeated across `sols` + `terrains d'agrément` rows, e.g.
    `2025-3`) collapse cleanly to one dwelling, while repeated identical `(dwelling, land_use)`
    rows remain flagged as ambiguous (Cerema DV3F `nblocanc`).
    """

    year: str
    nature: str
    communes: set[str] = field(default_factory=set)
    dispositions: set[str] = field(default_factory=set)
    prices: set[float] = field(default_factory=set)
    house_units: dict[DwellingKey, Counter[LandUseKey]] = field(default_factory=dict)
    apt_units: dict[DwellingKey, Counter[LandUseKey]] = field(default_factory=dict)
    dep_rows: int = 0
    pro_rows: int = 0


def download(url: str, path: Path) -> Path:
    """Download a file into `.cache/lem-6/` once; later runs reuse it."""
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


def fetch_json(url: str, cache_name: str) -> dict[str, object]:
    path = download(url, CACHE / cache_name)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object from {url}")
    return data


def parse_float(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * pct / 100.0)))
    return sorted_values[idx]


def inspect_window_metadata() -> None:
    """Print available files and sizes for geo-DVF and raw DGFiP DVF."""
    geodvf = fetch_json(GEODVF_DATASET_API, "meta-geodvf.json")
    raw_dvf = fetch_json(DVF_RAW_DATASET_API, "meta-dvf-raw.json")
    rows: list[list[object]] = []
    for label, meta in [("geo-DVF (Etalab)", geodvf), ("DVF raw (DGFiP)", raw_dvf)]:
        resources = meta.get("resources")
        if not isinstance(resources, list):
            continue
        for res in resources:
            if not isinstance(res, dict):
                continue
            fmt = str(res.get("format") or "")
            if fmt in ("csv.gz", "txt.zip"):
                size = res.get("filesize")
                mb = f"{int(size) / 1e6:.1f} MB" if isinstance(size, int) else "-"
                rows.append([label, res.get("title"), fmt, mb, str(res.get("last_modified"))[:10]])
    table(
        "Available DVF files on data.gouv.fr (rolling 5-year window)",
        ["dataset", "resource", "format", "size", "last modified"],
        rows,
    )


def classify_dwelling_map(
    units: dict[DwellingKey, Counter[LandUseKey]],
) -> tuple[str, float, bool]:
    """Return `(kind_state, surface, collapsed_land_use)` for one residential type map.

    States: `"none"`, `"single"`, `"ambiguous_repeat"`, `"multi"`.
    """
    if not units:
        return "none", 0.0, False
    if len(units) > 1:
        return "multi", 0.0, False
    only_key, land_counts = next(iter(units.items()))
    surf = parse_float(only_key[2]) or 0.0
    if any(count > 1 for count in land_counts.values()):
        return "ambiguous_repeat", surf, False
    collapsed = len(land_counts) > 1
    return "single", surf, collapsed


def normalize_code(
    raw_code: str,
    communes: dict[str, dict[str, str]],
    arrondissements: dict[str, dict[str, str]],
    resolved: dict[str, str],
) -> str | None:
    """Map a DVF `code_commune` to its active COG 2025 `COM`, or None if out of COG."""
    if raw_code in communes:
        return raw_code
    if raw_code in arrondissements:
        return arrondissements[raw_code]["COMPARENT"]
    return resolved.get(raw_code)


def analyze_dvf() -> None:
    communes, arrondissements, resolved = load_cog()
    sample_codes = {code for code, _, _ in GEO_SAMPLE}

    file_stats: list[list[object]] = []
    total_rows = 0
    exact_dup_rows = 0
    non_empty = Counter[str]()
    depts_seen: set[str] = set()
    code_categories = Counter[str]()
    unknown_codes: Counter[str] = Counter()
    montbenoit_by_year: Counter[tuple[str, str]] = Counter()

    # Naive row-level prices/m² on sample territories (for side-by-side comparison).
    naive_sample: dict[tuple[str, str], list[float]] = defaultdict(list)

    mutations: dict[str, MutationAgg] = {}

    for period, url in DVF_FILES:
        path = download(url, CACHE / f"dvf-{period}.csv.gz")
        period_rows = 0
        period_muts: set[str] = set()
        min_date = "9999-99-99"
        max_date = "0000-00-00"

        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            col = {name: i for i, name in enumerate(header)}

            i_mut = col["id_mutation"]
            i_date = col["date_mutation"]
            i_disp = col["numero_disposition"]
            i_nat = col["nature_mutation"]
            i_val = col["valeur_fonciere"]
            i_com = col["code_commune"]
            i_dep = col["code_departement"]
            i_parc = col["id_parcelle"]
            i_type = col["type_local"]
            i_surf = col["surface_reelle_bati"]
            i_pieces = col["nombre_pieces_principales"]
            i_lot1 = col["lot1_numero"]
            i_lot2 = col["lot2_numero"]
            i_lot3 = col["lot3_numero"]
            i_lot4 = col["lot4_numero"]
            i_lot5 = col["lot5_numero"]
            i_anum = col["adresse_numero"]
            i_avoi = col["adresse_nom_voie"]
            i_ncul = col["code_nature_culture"]
            i_ncsp = col["code_nature_culture_speciale"]
            i_ster = col["surface_terrain"]
            comp_indices = [(name, col[name]) for name in COMPLETENESS_FIELDS]

            prev_row: tuple[str, ...] | None = None
            for row in reader:
                period_rows += 1
                total_rows += 1
                row_key = (
                    row[i_mut],
                    row[i_disp],
                    row[i_parc],
                    row[i_type],
                    row[i_surf],
                    row[i_val],
                )
                if row_key == prev_row:
                    exact_dup_rows += 1
                prev_row = row_key

                d = row[i_date]
                if d:
                    if d < min_date:
                        min_date = d
                    if d > max_date:
                        max_date = d

                for fname, idx in comp_indices:
                    if row[idx]:
                        non_empty[fname] += 1

                nat = row[i_nat]
                code = row[i_com]
                dep = row[i_dep]
                if dep:
                    depts_seen.add(dep)
                if code in communes:
                    code_categories["COM (current)"] += 1
                elif code in arrondissements:
                    code_categories["ARM (Paris/Lyon/Marseille)"] += 1
                elif code in resolved:
                    code_categories["OLD (mapped via v_mvt_commune)"] += 1
                else:
                    code_categories["Out of COG / unresolved"] += 1
                    unknown_codes[code] += 1

                if code in ("25303", "25390"):
                    montbenoit_by_year[(period, code)] += 1

                mut_id = row[i_mut]
                period_muts.add(mut_id)
                agg = mutations.get(mut_id)
                if agg is None:
                    agg = MutationAgg(year=period, nature=nat)
                    mutations[mut_id] = agg
                if code:
                    agg.communes.add(code)
                if row[i_disp]:
                    agg.dispositions.add(row[i_disp])

                val = parse_float(row[i_val])
                if val is not None:
                    agg.prices.add(val)

                tlocal = row[i_type]
                if tlocal in RESIDENTIAL_TYPES:
                    unit_key: DwellingKey = (
                        row[i_parc],
                        tlocal,
                        row[i_surf],
                        row[i_pieces],
                        row[i_lot1],
                        row[i_lot2],
                        row[i_lot3],
                        row[i_lot4],
                        row[i_lot5],
                        f"{row[i_anum]} {row[i_avoi]}",
                    )
                    land_key: LandUseKey = (row[i_ncul], row[i_ncsp], row[i_ster])
                    target_map = agg.house_units if tlocal == "Maison" else agg.apt_units
                    counts = target_map.get(unit_key)
                    if counts is None:
                        counts = Counter()
                        target_map[unit_key] = counts
                    counts[land_key] += 1
                elif tlocal == "Dépendance":
                    agg.dep_rows += 1
                elif tlocal:
                    agg.pro_rows += 1

                # Naive row-level price/m² on sample (including parent city for ARM codes).
                surf = parse_float(row[i_surf])
                if (
                    period == "2025"
                    and nat == "Vente"
                    and tlocal in RESIDENTIAL_TYPES
                    and val
                    and val > 0
                    and surf
                    and surf > 0
                ):
                    if code in sample_codes:
                        naive_sample[(code, tlocal)].append(val / surf)
                    if code in arrondissements:
                        parent = arrondissements[code]["COMPARENT"]
                        if parent in sample_codes:
                            naive_sample[(parent, tlocal)].append(val / surf)

        file_stats.append(
            [
                period,
                f"{path.stat().st_size / 1e6:.1f} MB",
                f"{period_rows:,}",
                f"{len(period_muts):,}",
                f"{period_rows / max(1, len(period_muts)):.2f}",
                f"{min_date} .. {max_date}",
            ]
        )

    table(
        "National DVF géolocalisée volumes analyzed (2024 - S1 2026)",
        ["period", "gz size", "rows", "distinct id_mutation", "rows/mutation", "date range"],
        file_stats,
    )

    table(
        "Field completeness across all analyzed rows",
        ["field", "filled rows", "completeness"],
        [
            [fname, f"{non_empty[fname]:,}", f"{non_empty[fname] / total_rows:.1%}"]
            for fname in COMPLETENESS_FIELDS
        ],
    )

    all_deps = {row["DEP"] for row in communes.values()}
    missing_deps = sorted(all_deps - depts_seen)
    table(
        "Geographic coverage and `code_commune` validity against COG 2025",
        ["check", "value", "details"],
        [
            [
                "Departments present in DVF",
                f"{len(depts_seen)}/{len(all_deps)}",
                f"Missing: {', '.join(missing_deps)}",
            ],
            [
                "Consecutive duplicate rows (same mut/disp/parcel/type/surf/val)",
                f"{exact_dup_rows:,}",
                f"{exact_dup_rows / total_rows:.2%} of rows",
            ],
            *[
                [cat, f"{cnt:,}", f"{cnt / total_rows:.2%} of rows"]
                for cat, cnt in code_categories.most_common()
            ],
            [
                "Out of COG / unresolved `code_commune` top examples",
                len(unknown_codes),
                ", ".join(f"{c} ({n})" for c, n in unknown_codes.most_common(5)) or "-",
            ],
            [
                "Commune nouvelle `25390` vs absorbed `25303` rows",
                "-",
                ", ".join(f"{p}/{c}: {n}" for (p, c), n in sorted(montbenoit_by_year.items())),
            ],
        ],
    )

    # Classify every mutation and run the €/m² waterfall on 2025 (full year) and 2024-2026-S1.
    mut_categories = Counter[str]()
    nature_muts = Counter[str]()
    waterfall = Counter[str]()
    collapsed_land_use_2025 = 0

    clean_2025_all: list[tuple[str, str, str, float, float, float]] = []
    vefa_2025_ppm2: dict[str, list[float]] = defaultdict(list)
    raw_res_ppm2: dict[str, list[float]] = defaultdict(list)
    clean_res_ppm2: dict[str, list[float]] = defaultdict(list)
    commune_sales_2024: dict[tuple[str, str], list[float]] = defaultdict(list)
    commune_sales_2025_vals: dict[tuple[str, str], list[float]] = defaultdict(list)
    commune_sales_2025: dict[str, Counter[str]] = {
        "Maison": Counter(),
        "Appartement": Counter(),
    }
    commune_sales_2p5y: dict[str, Counter[str]] = {
        "Maison": Counter(),
        "Appartement": Counter(),
    }
    sample_clean: dict[tuple[str, str], list[float]] = defaultdict(list)
    sample_2p5y: dict[tuple[str, str], list[float]] = defaultdict(list)

    for agg in mutations.values():
        nature_muts[agg.nature] += 1
        multi_disp = len(agg.dispositions) > 1
        h_state, h_surf, h_collapsed = classify_dwelling_map(agg.house_units)
        a_state, a_surf, a_collapsed = classify_dwelling_map(agg.apt_units)

        if multi_disp:
            cat = "Multi-disposition (`numero_disposition` > 1)"
        elif h_state == "single" and a_state == "none" and agg.pro_rows == 0:
            cat = "Monobien Maison (+ dep/land, land-use repeats collapsed)"
        elif a_state == "single" and h_state == "none" and agg.pro_rows == 0:
            cat = "Monobien Appartement (+ dep/land, land-use repeats collapsed)"
        elif (h_state == "ambiguous_repeat" and a_state == "none" and agg.pro_rows == 0) or (
            a_state == "ambiguous_repeat" and h_state == "none" and agg.pro_rows == 0
        ):
            cat = "Ambiguous repeated dwelling (same unit & land-use)"
        elif h_state == "multi" and a_state == "none" and agg.pro_rows == 0:
            cat = "Multibien homogène Maisons"
        elif a_state == "multi" and h_state == "none" and agg.pro_rows == 0:
            cat = "Multibien homogène Appartements"
        elif h_state != "none" or a_state != "none":
            cat = "Mixte (Maison+Appart ou résidentiel+pro)"
        elif agg.pro_rows > 0:
            cat = "Local pro / industriel / commercial seul"
        elif agg.dep_rows > 0:
            cat = "Dépendance seule (parking, cave, garage)"
        else:
            cat = "Terrain nu / non bâti"
        mut_categories[cat] += 1

        if len(agg.communes) != 1:
            if agg.year == "2025":
                waterfall["0_all_2025_mutations"] += 1
                waterfall["1_excluded_multi_commune"] += 1
            continue
        raw_code = next(iter(agg.communes))
        norm_com = normalize_code(raw_code, communes, arrondissements, resolved)
        if norm_com is None:
            if agg.year == "2025":
                waterfall["0_all_2025_mutations"] += 1
                waterfall["2_excluded_out_of_cog"] += 1
            continue
        dep_code = communes[norm_com]["DEP"]

        if agg.year == "2025":
            waterfall["0_all_2025_mutations"] += 1
            if agg.nature not in ("Vente", "Vente en l'état futur d'achèvement"):
                waterfall["3_excluded_non_sale_nature"] += 1
                continue
            if multi_disp:
                waterfall["4_excluded_multi_disposition"] += 1
                continue
            if len(agg.prices) != 1:
                waterfall["5_excluded_missing_or_ambiguous_price"] += 1
                continue
            price = next(iter(agg.prices))
            if price < MIN_PRICE_EUR:
                waterfall["6_excluded_symbolic_price_lt_1000"] += 1
                continue
            if h_state == "single" and a_state == "none" and agg.pro_rows == 0:
                kind = "Maison"
                surf = h_surf
                collapsed = h_collapsed
            elif a_state == "single" and h_state == "none" and agg.pro_rows == 0:
                kind = "Appartement"
                surf = a_surf
                collapsed = a_collapsed
            elif (h_state == "ambiguous_repeat" and a_state == "none" and agg.pro_rows == 0) or (
                a_state == "ambiguous_repeat" and h_state == "none" and agg.pro_rows == 0
            ):
                waterfall["7_excluded_ambiguous_repeat"] += 1
                continue
            elif h_state != "none" or a_state != "none":
                waterfall["8_excluded_multi_unit_or_mixed"] += 1
                continue
            else:
                waterfall["9_excluded_non_residential"] += 1
                continue
            if surf < MIN_SURFACE_M2 or surf > MAX_SURFACE_M2:
                waterfall["10_excluded_invalid_surface"] += 1
                continue
            ppm2 = price / surf
            if agg.nature == "Vente en l'état futur d'achèvement":
                waterfall["11_vefa_kept_separately"] += 1
                if MIN_PRICE_PER_M2 <= ppm2 <= MAX_PRICE_PER_M2:
                    vefa_2025_ppm2[kind].append(ppm2)
                continue
            raw_res_ppm2[kind].append(ppm2)
            if ppm2 < MIN_PRICE_PER_M2 or ppm2 > MAX_PRICE_PER_M2:
                waterfall["12_excluded_outlier_ppm2"] += 1
                continue
            waterfall["13_kept_clean_vente_monobien"] += 1
            if collapsed:
                collapsed_land_use_2025 += 1
            clean_res_ppm2[kind].append(ppm2)
            signed_ppm2 = ppm2 if kind == "Maison" else -ppm2
            clean_2025_all.append((raw_code, norm_com, dep_code, price, surf, signed_ppm2))
            commune_sales_2025[kind][norm_com] += 1
            commune_sales_2025_vals[(norm_com, kind)].append(ppm2)
            if raw_code in sample_codes:
                sample_clean[(raw_code, kind)].append(ppm2)
            if norm_com in sample_codes and norm_com != raw_code:
                sample_clean[(norm_com, kind)].append(ppm2)

        # Accumulate 2024 and 2.5-year clean Vente monobien for threshold & stability analysis.
        if agg.nature == "Vente" and not multi_disp and len(agg.prices) == 1:
            price = next(iter(agg.prices))
            if price >= MIN_PRICE_EUR:
                kind = (
                    "Maison"
                    if h_state == "single" and a_state == "none" and agg.pro_rows == 0
                    else "Appartement"
                    if a_state == "single" and h_state == "none" and agg.pro_rows == 0
                    else ""
                )
                if kind:
                    surf = h_surf if kind == "Maison" else a_surf
                    if MIN_SURFACE_M2 <= surf <= MAX_SURFACE_M2:
                        ppm2 = price / surf
                        if MIN_PRICE_PER_M2 <= ppm2 <= MAX_PRICE_PER_M2:
                            commune_sales_2p5y[kind][norm_com] += 1
                            if agg.year == "2024":
                                commune_sales_2024[(norm_com, kind)].append(ppm2)
                            if raw_code in sample_codes:
                                sample_2p5y[(raw_code, kind)].append(ppm2)
                            if norm_com in sample_codes and norm_com != raw_code:
                                sample_2p5y[(norm_com, kind)].append(ppm2)

    total_muts = len(mutations)
    table(
        "Mutations by `nature_mutation` (2024 - S1 2026)",
        ["nature_mutation", "mutations", "share"],
        [[nat, f"{cnt:,}", f"{cnt / total_muts:.2%}"] for nat, cnt in nature_muts.most_common()],
    )

    table(
        "Mutation structure after collapsing land-use repeats (2024 - S1 2026)",
        ["category", "mutations", "share"],
        [[cat, f"{cnt:,}", f"{cnt / total_muts:.2%}"] for cat, cnt in mut_categories.most_common()],
    )

    base_2025 = waterfall["0_all_2025_mutations"]
    kept_2025 = max(1, waterfall["13_kept_clean_vente_monobien"])
    table(
        "2025 price/m² exclusion waterfall (national, COG 2025 scope)",
        ["step", "mutations", "share of 2025 mutations"],
        [
            [step, f"{waterfall[step]:,}", f"{waterfall[step] / max(1, base_2025):.2%}"]
            for step in sorted(waterfall, key=lambda k: int(k.split("_", 1)[0]))
        ]
        + [
            [
                "of which recovered by collapsing land-use repeats",
                f"{collapsed_land_use_2025:,}",
                f"{collapsed_land_use_2025 / kept_2025:.2%} of kept",
            ]
        ],
    )

    dist_rows = []
    for label, bucket in [
        ("Vente Maison (before outlier filter)", raw_res_ppm2["Maison"]),
        ("Vente Maison (clean [200..35000])", clean_res_ppm2["Maison"]),
        ("VEFA Maison (clean)", vefa_2025_ppm2["Maison"]),
        ("Vente Appartement (before outlier filter)", raw_res_ppm2["Appartement"]),
        ("Vente Appartement (clean [200..35000])", clean_res_ppm2["Appartement"]),
        ("VEFA Appartement (clean)", vefa_2025_ppm2["Appartement"]),
    ]:
        vals = sorted(bucket)
        dist_rows.append(
            [
                label,
                f"{len(vals):,}",
                f"{percentile(vals, 1):,.0f}",
                f"{percentile(vals, 5):,.0f}",
                f"{percentile(vals, 50):,.0f}",
                f"{percentile(vals, 95):,.0f}",
                f"{percentile(vals, 99):,.0f}",
            ]
        )
    table(
        "2025 €/m² distribution (national, Vente vs VEFA, before and after outlier bounds)",
        ["segment", "n", "p01", "p05", "p50 (median)", "p95", "p99"],
        dist_rows,
    )

    # Naive row-level vs clean mutation-level on sample (2025).
    sample_rows = []
    for code, name, _ in GEO_SAMPLE:
        has_any = any(
            naive_sample[(code, k)] or sample_clean[(code, k)] or sample_2p5y[(code, k)]
            for k in ("Appartement", "Maison")
        )
        if not has_any:
            sample_rows.append([code, name, "both", 0, "-", 0, "-", 0, "-"])
            continue
        for kind in ("Appartement", "Maison"):
            naive_vals = naive_sample[(code, kind)]
            clean_vals = sample_clean[(code, kind)]
            vals_2p5 = sample_2p5y[(code, kind)]
            if not naive_vals and not clean_vals and not vals_2p5:
                continue
            sample_rows.append(
                [
                    code,
                    name,
                    kind,
                    len(naive_vals),
                    f"{statistics.median(naive_vals):,.0f}" if naive_vals else "-",
                    len(clean_vals),
                    f"{statistics.median(clean_vals):,.0f}" if clean_vals else "-",
                    len(vals_2p5),
                    f"{statistics.median(vals_2p5):,.0f}" if vals_2p5 else "-",
                ]
            )
    table(
        "Sample territories: naive row-level vs clean monobien (2025) vs 2.5 years",
        [
            "code",
            "territory",
            "type",
            "naive rows 2025",
            "naive p50 €/m²",
            "clean n 2025",
            "clean p50 €/m² 2025",
            "clean n 2.5y",
            "clean p50 €/m² 2.5y",
        ],
        sample_rows,
    )

    # Hierarchy check: true department median vs unweighted average of commune medians (2025).
    dept_vals: dict[tuple[str, str], list[float]] = defaultdict(list)
    dept_com_vals: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for _, norm_com, dep_code, _, _, signed_ppm2 in clean_2025_all:
        if dep_code not in HIERARCHY_DEPTS:
            continue
        kind = "Maison" if signed_ppm2 > 0 else "Appartement"
        ppm2 = abs(signed_ppm2)
        dept_vals[(dep_code, kind)].append(ppm2)
        dept_com_vals[(dep_code, kind, norm_com)].append(ppm2)

    hier_rows = []
    for dep_code in HIERARCHY_DEPTS:
        for kind in ("Maison", "Appartement"):
            vals = dept_vals[(dep_code, kind)]
            if not vals:
                continue
            com_medians = [
                statistics.median(v)
                for (d, k, _), v in dept_com_vals.items()
                if d == dep_code and k == kind
            ]
            true_med = statistics.median(vals)
            avg_of_meds = statistics.mean(com_medians)
            delta_pct = (avg_of_meds - true_med) / true_med
            hier_rows.append(
                [
                    dep_code,
                    kind,
                    f"{len(vals):,}",
                    len(com_medians),
                    f"{true_med:,.0f}",
                    f"{avg_of_meds:,.0f}",
                    f"{delta_pct:+.1%}",
                ]
            )
    table(
        "Why never average medians: true department median vs mean of commune medians (2025)",
        ["dept", "type", "sales", "communes", "true dept p50 €/m²", "mean of commune p50", "bias"],
        hier_rows,
    )

    # Publication threshold coverage across all ~33,000 DVF-covered communes.
    covered_communes = [c for c, row in communes.items() if row["DEP"] not in missing_deps]
    thresh_rows = []
    windows = [
        ("1 year (2025)", commune_sales_2025),
        ("2.5 years (2024-S1 2026)", commune_sales_2p5y),
    ]
    for window_name, counts_by_kind in windows:
        for kind in ("Maison", "Appartement"):
            counts = counts_by_kind[kind]
            n_cov = len(covered_communes)
            row_vals: list[object] = [window_name, kind, f"{n_cov:,}"]
            for threshold in (1, 5, 10, 15, 20, 30):
                ok = sum(counts[c] >= threshold for c in covered_communes)
                row_vals.append(f"{ok:,} ({ok / n_cov:.1%})")
            thresh_rows.append(row_vals)
    table(
        "Commune coverage by minimum sale count threshold (DVF-covered communes)",
        ["window", "type", "covered communes", ">= 1", ">= 5", ">= 10", ">= 15", ">= 20", ">= 30"],
        thresh_rows,
    )

    # Empirical year-over-year median volatility (2024 vs 2025) by minimum sale count bucket.
    buckets = [
        (1, 4, "1-4"),
        (5, 9, "5-9"),
        (10, 14, "10-14"),
        (15, 29, "15-29"),
        (30, 999999, "30+"),
    ]
    stab_rows = []
    for kind in ("Maison", "Appartement"):
        by_bucket: dict[str, list[float]] = defaultdict(list)
        for com in covered_communes:
            v24 = commune_sales_2024.get((com, kind))
            v25 = commune_sales_2025_vals.get((com, kind))
            if not v24 or not v25:
                continue
            n_min = min(len(v24), len(v25))
            m24 = statistics.median(v24)
            m25 = statistics.median(v25)
            drift = abs(m25 - m24) / m24
            for lo, hi, label in buckets:
                if lo <= n_min <= hi:
                    by_bucket[label].append(drift)
                    break
        for _, _, label in buckets:
            drifts = sorted(by_bucket[label])
            if not drifts:
                continue
            stab_rows.append(
                [
                    kind,
                    label,
                    f"{len(drifts):,}",
                    f"{percentile(drifts, 50):.1%}",
                    f"{percentile(drifts, 90):.1%}",
                ]
            )
    table(
        "Empirical median €/m² stability (2024 vs 2025) by min(n_2024, n_2025) bucket",
        ["type", "min annual sales", "communes", "median |YoY drift|", "p90 |YoY drift|"],
        stab_rows,
    )


def main() -> None:
    inspect_window_metadata()
    analyze_dvf()


if __name__ == "__main__":
    main()

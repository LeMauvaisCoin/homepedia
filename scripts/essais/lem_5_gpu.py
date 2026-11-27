# /// script
# requires-python = ">=3.13"
# dependencies = ["pymupdf", "pypdf"]
# ///
"""LEM-5, GPU geographic layers: zoning and prescriptions as structured output.

Run with `uv run scripts/essais/lem_5_gpu.py` after `lem_5.py` (same cache). Reads the
Géoplateforme WFS (`wfs_du:*` layers), compares zone labels with the règlement text and the
annotated zones, looks for height, coverage or parking values in prescriptions and map
labels, and shows what the pipeline returns for an RNU commune and a carte communale.
"""

import csv
import re
import urllib.parse
from collections import Counter

from lem_5 import ANNOTATIONS, GPU, corpus_file, epci, gpu_documents, page_texts
from lem_5_reglement import REGLEMENTS, plain, segment
from lem_7 import get, open_url, table

WFS = "https://data.geopf.fr/wfs/ows"
PAGE_SIZE = 5000  # server maximum per request
LAYERS = ["prescription_surf", "prescription_lin", "prescription_pct", "info_surf", "info_lin"]
# Words that would carry a height, coverage or parking value in a layer label.
VALUE_WORDS = re.compile(
    r"hauteur|gabarit|emprise au sol|coefficient d.emprise|stationnement|\bces\b"
)
# One real commune per uncovered case, found with the `wfs_du:municipality` and `doc_urba` layers.
CASES = [("25002", "Abbans-Dessus", "RNU"), ("01002", "L'Abergement-de-Varey", "carte communale")]


def features(layer: str, cql: str, properties: str) -> list[dict]:
    """All features of a WFS layer matching a CQL filter, without geometry, page by page."""
    rows: list[dict] = []
    while True:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "outputFormat": "application/json",
            "typeNames": f"wfs_du:{layer}",
            "propertyName": properties,
            "CQL_FILTER": cql,
            "sortBy": "gid",
            "count": PAGE_SIZE,
            "startIndex": len(rows),
        }
        page, _ = get(WFS, params)
        rows += [feature["properties"] for feature in page["features"]]
        if len(page["features"]) < PAGE_SIZE:
            return rows


def annotated_zones() -> dict[str, set[str]]:
    zones: dict[str, set[str]] = {}
    with ANNOTATIONS.open() as file:
        for row in csv.DictReader(file):
            if row["kind"] in ("field", "passage") and row["zone"] != "general":
                zones.setdefault(row["file"], set()).add(row["zone"])
    return zones


def partition(document_id: str) -> str:
    """WFS partition of a GPU document ("DU_15219"); its WFS gpu_doc_id can differ from the API."""
    details, _ = get(f"{GPU}/document/{document_id}/details")
    return details["name"]


def zoning() -> None:
    """Zone polygons per document: version, labels, match with the text and the annotations."""
    expected = annotated_zones()
    rows, gaps = [], []
    for document_id, name in REGLEMENTS:
        polygons = features(
            "zone_urba",
            f"partition='{partition(document_id)}'",
            "libelle,typezone,idurba,nomfic,gpu_doc_id",
        )
        labels = {p["libelle"] for p in polygons}
        lowered = {label.lower() for label in labels}
        pages = page_texts(corpus_file(document_id, name))
        text_zones = {line.zone for line in segment(pages)}
        text = plain(" ".join(pages))
        in_text = {label for label in labels if re.search(rf"\b{re.escape(label.lower())}\b", text)}
        wanted = expected.get(name, set())
        exact = {z for z in wanted if z in labels}
        # A zone of the text (UB) often maps to several sector polygons (UB1, UB2...).
        prefix = {z for z in wanted if any(label.startswith(z.lower()) for label in lowered)}
        gaps += [[name, z] for z in sorted(wanted - prefix)]
        rows.append(
            [
                name,
                len(polygons),
                ", ".join(sorted({p["idurba"] for p in polygons})),
                "yes" if {p["gpu_doc_id"] for p in polygons} == {document_id} else "no",
                f"{sum(p['nomfic'] == name for p in polygons)}/{len(polygons)}",
                len(labels),
                ", ".join(
                    f"{t} {n}" for t, n in Counter(p["typezone"] for p in polygons).most_common()
                ),
                f"{len(in_text)}/{len(labels)}",
                f"{len(labels & text_zones)}/{len(labels)}",
                f"{len(exact)}/{len(wanted)} exact, {len(prefix)}/{len(wanted)} as prefix",
            ]
        )
    table(
        "GPU zoning (wfs_du:zone_urba) against the règlement",
        [
            "file",
            "polygons",
            "version (idurba)",
            "same GPU id as the API",
            "polygons pointing to this file",
            "zone labels",
            "polygons by typezone",
            "labels found in text",
            "labels found by segmentation",
            "annotated zones with a polygon label",
        ],
        rows,
    )
    table("Annotated zones without a polygon label", ["file", "zone"], gaps)


def other_layers() -> None:
    """Can prescriptions, informations or map labels give the values the text sends to the plan?"""
    rows = []
    for document_id, name in REGLEMENTS:
        cql = f"partition='{partition(document_id)}'"
        counts, valued, with_value = Counter(), Counter(), Counter()
        samples: dict[str, Counter[str]] = {}
        for layer in LAYERS:
            for item in features(layer, cql, "libelle,txt"):
                counts[layer] += 1
                label = item.get("libelle") or ""
                if VALUE_WORDS.search(plain(label)):
                    valued[label] += 1
                    value = (item.get("txt") or "").strip()
                    if re.search(r"\d", value):
                        with_value[label] += 1
                        samples.setdefault(label, Counter())[value] += 1
        labels = features("habillage_txt", cql, "txt,natecr")
        numeric = [
            t for t in labels if re.fullmatch(r"\d+(?:[.,]\d+)?", (t.get("txt") or "").strip())
        ]
        rows.append(
            [
                name,
                ", ".join(f"{layer} {n}" for layer, n in counts.items()),
                "; ".join(
                    f"{label[:40]}: {n}, {with_value[label]} with a value"
                    + (
                        f" ({', '.join(v for v, _ in samples[label].most_common(3))})"
                        if label in samples
                        else ""
                    )
                    for label, n in valued.most_common(3)
                )
                or "none",
                f"{len(numeric)}/{len(labels)}",
                ", ".join(
                    f"{k or '-'} {n}"
                    for k, n in Counter(t.get("natecr") for t in numeric).most_common(2)
                ),
            ]
        )
    table(
        "Prescriptions, informations and map labels",
        [
            "file",
            "features per layer",
            "labels about height, coverage or parking (count, with a value, sample values)",
            "numeric map labels / all",
            "their kind (natecr)",
        ],
        rows,
    )


def epci_documents(group: str | None) -> str:
    if not group:
        return "-"
    try:
        return f"{group}: {len(gpu_documents(group))} document(s)"
    except OSError as error:
        return f"{group}: {error}"


def uncovered() -> None:
    """What the pipeline returns where there is no PLU."""
    rows = []
    for code, name, case in CASES:
        documents = gpu_documents(code)
        group = epci(code)
        municipality = features("municipality", f"insee='{code}'", "insee,is_rnu")
        files = []
        for document in documents:
            details, _ = get(f"{GPU}/document/{document['id']}/details")
            files += details["files"]
        rows.append(
            [
                code,
                name,
                case,
                municipality[0]["is_rnu"] if municipality else "-",
                ", ".join(d["originalName"] for d in documents) or "none",
                ", ".join(files) or "-",
                "yes" if any("reglement" in f for f in files) else "no",
                epci_documents(group),
            ]
        )
    table(
        "Communes without a PLU",
        [
            "code",
            "commune",
            "case",
            "is_rnu (WFS)",
            "GPU documents",
            "files",
            "written règlement",
            "EPCI fallback",
        ],
        rows,
    )


def rate_limits() -> None:
    rows = []
    for url in [f"{GPU}/document?grid=15219", f"{WFS}?service=WFS&request=GetCapabilities"]:
        connection, response = open_url(url)
        try:
            headers = {k: v for k, v in response.getheaders() if "ratelimit" in k.lower()}
        finally:
            connection.close()
        rows.append(
            [urllib.parse.urlsplit(url).netloc, ", ".join(f"{k}: {v}" for k, v in headers.items())]
        )
    table("Rate limit headers announced by the servers", ["host", "headers"], rows)


if __name__ == "__main__":
    zoning()
    other_layers()
    uncovered()
    rate_limits()

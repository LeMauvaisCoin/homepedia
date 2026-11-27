# /// script
# requires-python = ">=3.13"
# dependencies = ["pymupdf", "pypdf"]
# ///
"""LEM-5: list the urban planning documents of the shared sample and compare text extraction.

Run with `uv run scripts/essais/lem_5.py`. Queries the public Géoportail de l'Urbanisme
(GPU) API, caches PDFs in `.cache/lem-5/` and prints Markdown tables to stdout. OCR uses
the Tesseract engine bundled with PyMuPDF and the French `tessdata_best` model.
"""

import csv
import difflib
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
import pypdf
from lem_7 import SAMPLE, get, open_url, table

GPU = "https://www.geoportail-urbanisme.gouv.fr/api"
GEO_API = "https://geo.api.gouv.fr/communes"
TESSDATA = "https://github.com/tesseract-ocr/tessdata_best/raw/main/fra.traineddata"
ROOT = Path(__file__).resolve().parents[2]
# Downloaded files, ignored by Git. Delete the folder to fetch fresh copies.
CACHE = ROOT / ".cache" / "lem-5"
ANNOTATIONS = Path(__file__).with_name("lem_5_annotations.csv")
EMPTY_PAGE_CHARS = 50
OCR_DPI = 300
NATIVE_PAGES_OCRED = 3
# Native règlement ending with scanned annexes turned by 90 degrees.
ROTATED = ("eee143f619882c020cfb0fbd52e178b7", "97411_reglement_20260805.pdf")

# Pinned corpus: (commune, GPU document id, file). GPU ids change with each new upload, so
# the script reports whether each pinned document is still the one in force.
CORPUS = [
    ("15219", "1afa66b3199a3eb54b911f3e23cb2176", "15219_reglement_20250428.pdf"),
    ("25390", "0318166e6da13f7d5a50123872087bf8", "25390_reglement_20220624.pdf"),
    (
        "25390",
        "0318166e6da13f7d5a50123872087bf8",
        "25390_liste_des_servitudes_d_utilite_publique_20220624.pdf",
    ),
    ("97411", "eee143f619882c020cfb0fbd52e178b7", "97411_reglement_20260805.pdf"),
    ("75056", "ab895285a1be6ca045127a6bb628cfaa", "75056_reglement_20260616.pdf"),
    (
        "75056",
        "e0436b1363d0188ad7336591fcde8c81",
        "EL7_PassageSaintSebastien18a26_19330114_act.pdf",
    ),
    ("75056", "e0436b1363d0188ad7336591fcde8c81", "EL7_QuaiDeSeine39_19990423_act.pdf"),
    ("67482", "2d870e7b48a79705969dc2395dbb663d", "246700488_reglement_20261001.pdf"),
    ("69123", "d5cbf3109419689d1261ee3a03183224", "200046977_reglement_20261103.pdf"),
]


def download(url: str, path: Path) -> Path:
    """Stream a file into the local cache once; later runs reuse it."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
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


def corpus_file(document_id: str, name: str) -> Path:
    return download(f"{GPU}/document/{document_id}/files/{name}", CACHE / name)


def normalize(text: str) -> str:
    """Lowercase, unify quotes and spaces, drop bullet glyphs: what a human compares."""
    text = unicodedata.normalize("NFKC", text).lower().replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"[\u2022\u25aa\u25e6\uf0a7\uf0b7\uf0d8]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return re.findall(r"\w+", normalize(text))


def word_recall(reference: str, candidate: str) -> float:
    """Share of reference words found in the candidate, ignoring order."""
    expected = Counter(words(reference))
    found = expected & Counter(words(candidate))
    return sum(found.values()) / max(1, sum(expected.values()))


def page_texts(path: Path) -> list[str]:
    with pymupdf.open(path) as document:
        return [page.get_text() for page in document]


def ocr_page(path: Path, number: int, rotation: int = 0) -> str:
    """OCR one page (1-based) in French, optionally turned; results are cached as text files."""
    suffix = f"_r{rotation}" if rotation else ""
    cached = CACHE / "ocr" / f"{path.stem}_{number}{suffix}.txt"
    if cached.exists():
        return cached.read_text()
    download(TESSDATA, CACHE / "tessdata" / "fra.traineddata")
    with pymupdf.open(path) as document:
        page = document[number - 1]
        page.set_rotation((page.rotation + rotation) % 360)
        textpage = page.get_textpage_ocr(
            language="fra", dpi=OCR_DPI, full=True, tessdata=str(CACHE / "tessdata")
        )
        text = page.get_text(textpage=textpage)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text


def rotated_scans() -> None:
    """Scanned pages turned by 90 degrees: try the four orientations and keep the best one.

    PyMuPDF exposes no Tesseract confidence or orientation detection, so a reading is scored
    by the share of its words (3 letters or more) that exist in the document's own text layer.
    """
    path = corpus_file(*ROTATED[:2])
    native = page_texts(path)
    vocabulary = {w for text in native for w in words(text) if len(w) >= 3}
    rows = []
    for number, text in enumerate(native, 1):
        if len(text.strip()) >= EMPTY_PAGE_CHARS:
            continue
        scores = {}
        for rotation in (0, 90, 180, 270):
            found = [
                w for w in words(ocr_page(path, number, rotation)) if len(w) >= 3 and w.isalpha()
            ]
            scores[rotation] = (
                sum(w in vocabulary for w in found) / max(1, len(found)),
                len(found),
            )
        best = max(scores, key=lambda r: scores[r][0])
        rows.append(
            [
                number,
                f"{scores[0][0]:.0%} ({scores[0][1]} words)",
                best,
                f"{scores[best][0]:.0%} ({scores[best][1]} words)",
            ]
        )
    table(
        f"Rotated scans in {ROTATED[1]}: share of OCR words known in the document",
        ["page", "as stored", "best rotation", "best score"],
        rows,
    )


def gpu_documents(grid: str) -> list[dict]:
    documents, _ = get(f"{GPU}/document", {"grid": grid, "status": "document.production"})
    return documents


def epci(code: str) -> str | None:
    try:
        commune, _ = get(f"{GEO_API}/{code}", {"fields": "codeEpci"})
    except OSError:
        return None
    return commune.get("codeEpci")


def coverage() -> None:
    """Documents in force on the GPU for each sample code, with the EPCI fallback for PLUi."""
    rows = []
    for code, name, kind in SAMPLE:
        documents = gpu_documents(code)
        grid = code
        if not any(d["type"] in ("PLU", "PLUi", "CC", "POS") for d in documents):
            group = epci(code) if kind == "COM" else None
            if group:
                documents += gpu_documents(group)
                grid = f"{code}, EPCI {group}"
        types = Counter(d["type"] for d in documents)
        urban = [d for d in documents if d["type"] in ("PLU", "PLUi", "CC", "POS")]
        rows.append(
            [
                code,
                name,
                grid,
                ", ".join(f"{t} {n}" for t, n in sorted(types.items())) or "none",
                ", ".join(d["originalName"] for d in urban) or "-",
                "yes" if any(d["grid"].get("rnu") for d in documents) else "no",
            ]
        )
    table(
        "GPU documents in force per sample code",
        ["code", "territory", "grid queried", "documents", "urban plan version", "RNU"],
        rows,
    )


def corpus() -> None:
    rows = []
    for commune, document_id, name in CORPUS:
        details, _ = get(f"{GPU}/document/{document_id}/details")
        current = {d["id"] for d in gpu_documents(details["grid"]["name"])}
        path = corpus_file(document_id, name)
        with pymupdf.open(path) as document:
            pages = document.page_count
            producer = document.metadata.get("producer") or "-"
        rows.append(
            [
                commune,
                details["type"],
                details["originalName"],
                document_id,
                name,
                pages,
                f"{path.stat().st_size / 1e6:.1f}",
                producer[:30],
                details.get("effectiveStatus"),
                "yes" if document_id in current else "no (replaced)",
            ]
        )
    table(
        "Corpus (pinned GPU documents)",
        [
            "commune",
            "type",
            "version",
            "GPU id",
            "file",
            "pages",
            "MB",
            "producer",
            "status",
            "still current",
        ],
        rows,
    )


def extraction() -> None:
    """Native text with two libraries, then OCR on scans and on a few native pages."""
    rows, ocr_rows = [], []
    for _, document_id, name in CORPUS:
        path = corpus_file(document_id, name)
        start = time.perf_counter()
        native = page_texts(path)
        pymupdf_seconds = time.perf_counter() - start
        start = time.perf_counter()
        other = [page.extract_text() or "" for page in pypdf.PdfReader(path).pages]
        pypdf_seconds = time.perf_counter() - start
        empty = [i + 1 for i, text in enumerate(native) if len(text.strip()) < EMPTY_PAGE_CHARS]
        step = max(1, len(native) // 10)
        agreement = [
            difflib.SequenceMatcher(None, words(a), words(b), autojunk=False).ratio()
            for a, b in list(zip(native, other, strict=True))[::step]
            if a.strip() or b.strip()
        ]
        rows.append(
            [
                name,
                len(native),
                sum(map(len, native)),
                sum(map(len, other)),
                len(empty),
                f"{sum(agreement) / len(agreement):.1%}" if agreement else "-",
                f"{pymupdf_seconds:.1f}",
                f"{pypdf_seconds:.1f}",
            ]
        )
        scanned = len(empty) > len(native) // 2
        targets = empty if scanned else list(range(1 + step, len(native), step))
        targets = targets if scanned else targets[:NATIVE_PAGES_OCRED]
        fresh = [p for p in targets if not (CACHE / "ocr" / f"{path.stem}_{p}.txt").exists()]
        start = time.perf_counter()
        ocr = {page: ocr_page(path, page) for page in targets}
        seconds = (time.perf_counter() - start) / len(fresh) if fresh else None
        recall = [word_recall(native[p - 1], ocr[p]) for p in ocr if native[p - 1].strip()]
        ocr_rows.append(
            [
                name,
                "scan" if scanned else "native",
                len(ocr),
                sum(len(t.strip()) >= EMPTY_PAGE_CHARS for t in ocr.values()),
                f"{sum(recall) / len(recall):.1%}" if recall else "-",
                f"{seconds:.1f}" if seconds else "cached",
            ]
        )
    table(
        "Native text extraction",
        [
            "file",
            "pages",
            "chars PyMuPDF",
            "chars pypdf",
            "pages < 50 chars",
            "word agreement",
            "s PyMuPDF",
            "s pypdf",
        ],
        rows,
    )
    table(
        "OCR (Tesseract fra, 300 dpi)",
        [
            "file",
            "kind",
            "pages OCRed",
            "pages with text",
            "native words found by OCR",
            "s/page",
        ],
        ocr_rows,
    )


def annotated_text() -> None:
    """Compare each annotated passage, read on the page image, with each extractor's output."""
    with ANNOTATIONS.open() as file:
        references = [row for row in csv.DictReader(file) if row["kind"] == "text"]
    rows = []
    # Per group (native or scan) and extractor: [exact matches, sum of word recall, count].
    totals: dict[tuple[str, str], list[float]] = {}
    for ref in references:
        path = corpus_file(ref["document_id"], ref["file"])
        page = int(ref["page"])
        outputs = {
            "pymupdf": page_texts(path)[page - 1],
            "pypdf": pypdf.PdfReader(path).pages[page - 1].extract_text() or "",
            "ocr": ocr_page(path, page),
        }
        group = f"{ref['split']} {ref['label'].split()[0]}"
        cells = []
        for extractor, text in outputs.items():
            recall = word_recall(ref["passage"], text)
            found = normalize(ref["passage"]) in normalize(text)
            total = totals.setdefault((group, extractor), [0, 0.0, 0])
            total[0] += found
            total[1] += recall
            total[2] += 1
            cells.append(f"{'exact' if found else 'no'} {recall:.0%}")
        rows.append([ref["split"], ref["file"], page, ref["label"], *cells])
    for group in ("dev native", "dev scan", "test native", "test scan"):
        cells = [totals[group, e] for e in ("pymupdf", "pypdf", "ocr")]
        rows.append(
            [
                f"**total {group}**",
                "",
                "",
                f"{cells[0][2]} passages",
                *(
                    f"{n:.0f}/{count} exact, {recall / count:.0%} words"
                    for n, recall, count in cells
                ),
            ]
        )
    table(
        "Annotated passages: exact match (same order) and share of words found",
        ["split", "file", "page", "content", "PyMuPDF", "pypdf", "OCR"],
        rows,
    )


if __name__ == "__main__":
    coverage()
    corpus()
    extraction()
    annotated_text()
    rotated_scans()

# /// script
# requires-python = ">=3.13"
# dependencies = ["pymupdf", "pypdf"]
# ///
"""LEM-5, written rules: classify passages and extract structured fields with rules only.

Run with `uv run scripts/essais/lem_5_reglement.py` after `lem_5.py` (same cache). Splits
each règlement into passages (zone, theme) with regular expressions, then extracts maximum
height, maximum ground coverage and car parking per dwelling. Scores both against the
annotated sample in `lem_5_annotations.csv` and prints Markdown tables to stdout.
"""

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass

from lem_5 import ANNOTATIONS, CORPUS, corpus_file, normalize, page_texts
from lem_7 import table

REGLEMENTS = [(doc, name) for _, doc, name in CORPUS if "reglement" in name]

ZONE_CODE = r"(?:[12I]{0,2}AU|U|A|N)[A-Za-z0-9]*"
ZONE_PATTERNS = [
    re.compile(rf"^(?:ZONE|Zone)\s+({ZONE_CODE}(?: \d)?)\s*$"),  # page header ("Zone URm 1")
    re.compile(rf"^ZONE\b.*\(({ZONE_CODE})\)\s*$"),  # Paris: ZONE URBAINE GÉNÉRALE (UG)
    re.compile(rf"DISPOSITIONS APPLICABLES (?:A|À) LA ZONE ({ZONE_CODE})"),
    re.compile(rf"^ARTICLE\s+({ZONE_CODE})\s+\d+\b"),  # ARTICLE UA 10
    re.compile(rf"^Article\s+\d+\s+({ZONE_CODE})\s*:"),  # Article 10 UAA :
    re.compile(rf"^Article\s+({ZONE_CODE})\.\d+"),  # Article Ud.10
    re.compile(rf"^({ZONE_CODE})\.\d+(?:\.\d+)*\s"),  # UG.3.2 Hauteur
]
# Titles that leave the zone chapters: common rules, figures, glossary. Case-sensitive, since
# "Dispositions générales" is also a common sub-heading inside a zone article.
GENERAL = re.compile(
    r"^(?:TITRE [IVX]+\W*)?DISPOSITIONS G[ÉE]N[ÉE]RALES|^Dispositions toutes zones"
    r"|^(?:FIGURES|LEXIQUE|GLOSSAIRE)\b|PARTIE I\s*$"
)
TOC_LINES_PER_PAGE = 5
# Headings that open a new rule section: their theme replaces the current one.
MAJOR_HEADING = re.compile(
    r"^(?:ARTICLE|Article|CHAPITRE|TITRE)\b|^\d+\.\d+\s*[-\u2013]\s|^[A-Z]{1,5}\.\d+\.\d+\s|^[IVXL]+\.\s"
)
# Sub-headings change the theme only when they name one.
MINOR_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*\s*[-\u2013.)]|[a-z]\.\s|[A-Z]{1,5}\.\d+(?:\.\d+)+\s)|:\s*$"
)
THEMES = [
    ("stationnement", r"stationnement"),
    ("emprise", r"emprise au sol|coefficient d.emprise"),
    ("hauteur", r"hauteur"),
    ("implantation", r"implantation|alignement|limites? separatives|recul|prospect"),
    ("destination", r"destination|occupations?|utilisations? du sol|interdi|mixite"),
    ("paysage", r"espaces? (?:libres?|verts?)|plantations?|paysag|pleine terre|vegetal|nature"),
    ("aspect", r"aspect|qualite urbaine|architectur|facades?|toitures?|clotures?|materiaux"),
    ("desserte", r"desserte|reseaux|acces|voirie|assainissement|eaux pluviales|dechets"),
]
FIELDS = {
    "hauteur": "hauteur_max_m",
    "emprise": "emprise_max_pct",
    "stationnement": "places_logement",
}
NUMBER = r"(\d+(?:[.,]\d+)?)"
GRAPHIC = r"(?:reglement|documents?) graphiques?|plan (?:general )?des hauteurs"
HEIGHT_WINDOW = 160


def plain(text: str) -> str:
    """Lowercase without accents, for keyword matching."""
    decomposed = unicodedata.normalize("NFKD", normalize(text))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def theme_of(text: str) -> str | None:
    lowered = plain(text)
    return next((theme for theme, pattern in THEMES if re.search(pattern, lowered)), None)


@dataclass
class Line:
    page: int
    text: str
    zone: str
    theme: str


def segment(pages: list[str]) -> list[Line]:
    """Label each line with the zone and theme in force where it appears."""
    zone, theme = "general", "autre"
    lines: list[Line] = []
    for number, page in enumerate(pages, 1):
        raw = [line.strip() for line in page.split("\n")]
        if sum("....." in text for text in raw) >= TOC_LINES_PER_PAGE:
            continue  # table of contents page
        for index, text in enumerate(raw):
            if not text or "....." in text:
                continue
            if GENERAL.search(text):
                zone = "general"
            for pattern in ZONE_PATTERNS:
                if match := pattern.search(text):
                    zone = match.group(1).replace(" ", "")
                    break
            # A heading's title often continues on the next line ("Article Ud.10" / "Hauteur").
            following = raw[index + 1] if index + 1 < len(raw) else ""
            if len(text) <= 150 and MAJOR_HEADING.search(text):
                theme = theme_of(text) or theme_of(following) or "autre"
            elif len(text) <= 100 and MINOR_HEADING.search(text):
                theme = (
                    theme_of(text) or (theme_of(following) if len(text) <= 25 else None) or theme
                )
            lines.append(Line(number, text, zone, theme))
    return lines


def find_line(lines: list[Line], page: int, excerpt: str) -> Line | None:
    target = normalize(excerpt)
    return next(
        (line for line in lines if line.page == page and target in normalize(line.text)), None
    )


def to_number(value: str) -> float:
    return float(value.replace(",", "."))


def extract(lines: list[Line], zone: str, field: str) -> tuple[str, int | None]:
    """Rule-based value for one zone and field: a number or a status code, with its page."""
    theme = next(t for t, f in FIELDS.items() if f == field)
    # A sector (UB1, Udp, URi1a) takes the rules of the longest zone code it starts with.
    zones = {line.zone for line in lines}
    parent = (
        zone
        if zone in zones
        else max((z for z in zones if zone.startswith(z)), key=len, default=zone)
    )
    passage = [line for line in lines if line.theme == theme and line.zone == parent]
    if not passage:
        return "absent", None
    page = passage[0].page
    texts = [plain(line.text) for line in passage]
    # A sector listed in a table or list: "URi1a ≤ 40 %", "- UB1 : 75 %".
    if zone != parent:
        for index, text in enumerate(texts):
            if re.search(rf"\b{re.escape(plain(zone))}\b(?! [a-z0-9]+ et)", text):
                window = " ".join(texts[index : index + 2])
                if match := re.search(rf"{NUMBER}\s*(%|m\b)", window):
                    return f"{to_number(match.group(1)):g}", passage[index].page
    # General rule: stop at the first sector-specific or exceptional paragraph.
    general = []
    for text in texts:
        if re.match(
            r"(en|dans le) secteurs? |dispositions particulieres|regles? alternatives?", text
        ):
            break
        general.append(text)
    body = " ".join(general)
    if field == "hauteur_max_m":
        # The first sentence about height that gives metres or points to the graphic rules
        # decides, skipping minimums, relative heights and fences.
        for match in re.finditer(r"hauteur", body):
            window = body[match.start() : match.start() + HEIGHT_WINDOW]
            if re.search(r"minimale|au-dessus|clotures?|rez-de-chaussee", window):
                continue
            heights = [
                to_number(m.group(1))
                for m in re.finditer(rf"{NUMBER}\s*(?:m\b|metres?\b)(?!\s*[²2])", window)
            ]
            if heights:
                return f"{max(heights):g}", page
            if re.search(GRAPHIC, window):
                return "graphique", page
    elif field == "emprise_max_pct":
        if match := re.search(rf"{NUMBER}\s*%", body):
            return f"{to_number(match.group(1)):g}", page
    elif match := re.search(
        rf"{NUMBER} places?(?: de stationnement)?(?: \w+){{0,3}} par logement", body
    ):
        return f"{to_number(match.group(1)):g}", page
    for code, pattern in [
        ("non_reglemente", r"n.est pas (?:fixe|prevu|reglemente|impose)|non reglemente"),
        ("graphique", GRAPHIC),
        ("renvoi", r"dispositions (?:generales|applicables a toutes)|titre ii|partie i\b"),
        ("niveaux", r"\br\s*\+\s*\d"),
        ("non_chiffre", r"besoins"),
    ]:
        if re.search(pattern, body):
            return code, page
    return "relatif", page


def same(expected: str, found: str) -> bool:
    try:
        return to_number(expected) == to_number(found)
    except ValueError:
        return expected == found


def annotations(kind: str) -> list[dict]:
    with ANNOTATIONS.open() as file:
        return [row for row in csv.DictReader(file) if row["kind"] == kind]


def main() -> None:
    segmented = {name: segment(page_texts(corpus_file(doc, name))) for doc, name in REGLEMENTS}

    rows = []
    for name, lines in segmented.items():
        themes = Counter(line.theme for line in lines)
        zones = {line.zone for line in lines} - {"general"}
        rows.append(
            [
                name,
                len(lines),
                len(zones),
                ", ".join(sorted(zones)[:6]) + (" ..." if len(zones) > 6 else ""),
                ", ".join(f"{t} {n / len(lines):.0%}" for t, n in themes.most_common(4)),
            ]
        )
    table(
        "Segmentation",
        ["file", "lines", "zones", "zone codes", "main themes (share of lines)"],
        rows,
    )

    scores: dict[str, Counter[str]] = defaultdict(Counter)
    errors = []
    for ref in annotations("passage"):
        line = find_line(segmented[ref["file"]], int(ref["page"]), ref["passage"])
        score = scores[ref["file"]]
        score["total"] += 1
        if line is None:
            score["not found"] += 1
            errors.append([ref["file"], ref["page"], ref["passage"][:50], "line not found", ""])
            continue
        score["zone"] += line.zone == ref["zone"]
        score["theme"] += line.theme == ref["label"]
        score["both"] += line.zone == ref["zone"] and line.theme == ref["label"]
        if (line.zone, line.theme) != (ref["zone"], ref["label"]):
            errors.append(
                [
                    ref["file"],
                    ref["page"],
                    ref["passage"][:50],
                    f"{ref['zone']} / {ref['label']}",
                    f"{line.zone} / {line.theme}",
                ]
            )
    total = sum(scores.values(), Counter())
    table(
        "Passage classification (zone and theme of annotated lines)",
        ["file", "lines", "zone correct", "theme correct", "both correct"],
        [
            [name, s["total"], s["zone"], s["theme"], s["both"]]
            for name, s in [*scores.items(), ("**total**", total)]
        ],
    )
    table("Passage classification errors", ["file", "page", "line", "expected", "found"], errors)

    rows, by_field = [], defaultdict(Counter)
    for ref in annotations("field"):
        found, page = extract(segmented[ref["file"]], ref["zone"], ref["label"])
        ok = same(ref["expected"], found)
        numeric = ref["expected"][0].isdigit()
        by_field[ref["label"]]["total"] += 1
        by_field[ref["label"]]["correct"] += ok
        by_field[ref["label"]]["numeric"] += numeric
        by_field[ref["label"]]["numeric correct"] += ok and numeric
        # Worst case for a user: a number shown where the rule gives another one or none.
        by_field[ref["label"]]["wrong number"] += not ok and found[0].isdigit()
        rows.append(
            [
                ref["file"][:14],
                ref["zone"],
                ref["label"],
                ref["expected"],
                found,
                page,
                "ok" if ok else "**error**",
            ]
        )
    table(
        "Structured fields, one row per annotation",
        ["file", "zone", "field", "expected", "extracted", "page", "result"],
        rows,
    )
    table(
        "Structured fields, error rate",
        [
            "field",
            "annotations",
            "correct",
            "error rate",
            "numeric expected",
            "numeric correct",
            "wrong number shown",
        ],
        [
            [
                field,
                c["total"],
                c["correct"],
                f"{1 - c['correct'] / c['total']:.0%}",
                c["numeric"],
                c["numeric correct"],
                c["wrong number"],
            ]
            for field, c in [*by_field.items(), ("**total**", sum(by_field.values(), Counter()))]
        ],
    )


if __name__ == "__main__":
    main()

"""
extract_codex_circulaires.py
-----------------
Extrait les circulaires du Codex Husson (Ressources_brutes/bases_legales/
39_005V_CPDF.pdf) vers corpus_par_matiere/corpus_reglementation_fabriques.json,
matiere `reglementation_fabriques`, dans `sections_circulaire[]`.

Contrairement aux textes traites par extract_codex_articles.py (decrets,
lois, CDLD, arretes - structures en "Art. N."), les circulaires ne sont
pas numerotees en articles mais en sections titrees. La structure varie
sensiblement d'une circulaire a l'autre (voir les commentaires par
document ci-dessous) - traitees une a la fois, pas par un regex unique
suppose universel.

Usage:
    python3 scripts_ponctuels/extract_codex_circulaires.py
"""
import json
import re
import unicodedata

import pypdf

PDF_PATH = "Ressources_brutes/bases_legales/39_005V_CPDF.pdf"
OUT_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"

FOOTER_RE = re.compile(r"^\d+_\d+V\.book\s+Page\s+\d+.*$", re.IGNORECASE)
PAGENUM_RE = re.compile(r"^\d{1,4}$")
ANNOTATION_RE = re.compile(r"Annotation\s*:\s*", re.IGNORECASE)

_PUNCT_MAP = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "Oe", "®": "",
    "•": "-", "▪": "-", "♦": "-",
    "→": "->",
})
_PUNCT_MAP.update(str.maketrans({chr(0xF0E8): "->", chr(0xF0F0): "-"}))

def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_all_caps_heading(line):
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _next_line_is_continuation(next_line):
    """Un titre trop long est parfois coupe sur 2 lignes par l'extraction
    PDF (retour a la ligne du livre, ex. "...de la convention" /
    "pluriannuelle"). Signal fiable : une vraie nouvelle phrase en francais
    commence toujours par une majuscule, alors que la suite d'un titre
    coupe reprend en minuscule - plus robuste qu'une liste de mots-cles
    (qui ratait par exemple "convention" ou "planification")."""
    for c in next_line:
        if c.isalpha():
            return c.islower()
    return False


def slugify(text):
    text = strip_accents(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def clean_text(text):
    text = strip_accents(text)
    text = text.translate(_PUNCT_MAP)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_pages(reader, start, end):
    return [reader.pages[p - 1].extract_text() for p in range(start, end + 1)]


def clean_lines(raw_pages, extra_noise_res=()):
    lines = []
    for page_text in raw_pages:
        for line in (page_text or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            if FOOTER_RE.match(line):
                continue
            if PAGENUM_RE.match(line):
                continue
            if is_all_caps_heading(line):
                continue
            if any(r.match(line) for r in extra_noise_res):
                continue
            lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Circulaire du 18 juillet 2014 (convention pluriannuelle)
# ---------------------------------------------------------------------------
# Structure a 2 niveaux : en-tetes nommes sans numero ("Preambule",
# "Definitions") ou "Section N. Titre" au premier niveau (detectes dans le
# corps, une seule page peut contenir plusieurs Sections courtes) ; puis
# une numerotation X.Y (X.Y.Z pour le volet financier) au second niveau
# (meme convention que le guide du tresorier).
CIRC_18_07_2014 = {
    "document_id": "circulaire_18_07_2014",
    "start": 143,  # Preambule - la lettre de transmission (p.141-142) est exclue
    "end": 152,
}
TOP_HEADING_18_07_RE = re.compile(r"^(Preambule|Definitions)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^Section\s+(\d+)\.\s*(.*)$", re.IGNORECASE)
SUBSECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.\s+(\S.*)$")


def extract_18_07_2014(reader):
    """Les reperes "1.1.", "1.2." de ce texte ne sont PAS de vrais titres :
    le paragraphe s'enchaine directement sur la meme ligne (pas de titre
    court separe du corps, contrairement au guide du tresorier). Ils
    servent seulement a delimiter des points numerotes a l'interieur d'une
    Section - le titre affiche reste celui de la Section parente, et le
    texte du point (numero inclus) est conserve tel quel dans `texte`."""
    raw_pages = get_pages(reader, CIRC_18_07_2014["start"], CIRC_18_07_2014["end"])
    lines = clean_lines(raw_pages)

    sections = []
    current_top_numero = None
    current_top_titre = None
    current_sub_numero = None
    buffer = []

    def flush():
        texte = clean_text("\n".join(buffer))
        if not texte:
            return
        numero = current_sub_numero or current_top_numero or ""
        titre = clean_text(current_top_titre or "")
        sections.append({"numero": numero, "titre": titre, "chapitre_parent": titre,
                          "texte": texte})

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m_top_named = TOP_HEADING_18_07_RE.match(strip_accents(line))
        m_section = SECTION_RE.match(line)
        if m_top_named or m_section:
            while (i + 1 < n and _next_line_is_continuation(lines[i + 1])
                   and not SECTION_RE.match(lines[i + 1])
                   and not TOP_HEADING_18_07_RE.match(lines[i + 1])
                   and not SUBSECTION_RE.match(lines[i + 1])):
                i += 1
                line = f"{line} {lines[i]}"
                m_top_named = TOP_HEADING_18_07_RE.match(strip_accents(line))
                m_section = SECTION_RE.match(line)
            flush()
            if m_top_named:
                current_top_numero, current_top_titre = None, m_top_named.group(1)
            else:
                current_top_numero = f"section_{m_section.group(1)}"
                current_top_titre = f"Section {m_section.group(1)}. {m_section.group(2)}".strip()
            current_sub_numero = None
            buffer = []
            i += 1
            continue
        m_sub = SUBSECTION_RE.match(line)
        if m_sub:
            flush()
            current_sub_numero = m_sub.group(1)
            buffer = [line]  # le "titre" capture par la regex fait partie du corps ici
            i += 1
            continue
        buffer.append(line)
        i += 1

    flush()
    return sections


# ---------------------------------------------------------------------------
# Circulaire du 12 decembre 2014 (tutelle sur les actes et pieces justificatives)
# ---------------------------------------------------------------------------
# Structure a 4 niveaux : en-tetes nommes sans numero ("Dispositions
# generales", "Rappel des principes", "Decheance", "Entree en vigueur"),
# "N. Titre" pour les 2 grandes divisions (tutelle communale / provinciale),
# "A. Titre" / "B. Titre" (tutelle generale / tutelle speciale), et
# "a. Titre" (ex. "Deliberations obligatoirement transmissibles").
# PIEGE : chaque paragraphe de cette circulaire est numerote par l'editeur
# pour l'index ("9 Deux autorites sont competentes...") - PAS un titre,
# reconnaissable a l'absence de point apres le numero (contrairement a
# "1. Tutelle sur les actes..." qui EST un titre). Ne jamais traiter un
# numero seul sans point comme un en-tete.
# Le corps du texte s'arrete a "Entree en vigueur" (p.188) : la suite
# (Adresses utiles, Liste des pieces justificatives, p.189-219) est un
# tableau (Article | Acte | Pieces justificatives | Adresse | Annotation)
# totalement mis a plat par l'extraction PDF lineaire - non exploitable
# tel quel, non extrait ici (voir CLAUDE.md).
CIRC_12_12_2014 = {"document_id": "circulaire_12_12_2014", "start": 157, "end": 188}
NAMED_TOP_12_12_RE = re.compile(
    r"^(Dispositions generales|Rappel des principes|Decheance|Entree en vigueur)$",
    re.IGNORECASE,
)
NUMBERED_TOP_RE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
UPPER_LETTER_RE = re.compile(r"^([A-Z])\.\s+(\S.*)$")
LOWER_LETTER_RE = re.compile(r"^([a-z])\.\s+(\S.*)$")


def extract_12_12_2014(reader):
    raw_pages = get_pages(reader, CIRC_12_12_2014["start"], CIRC_12_12_2014["end"])
    lines = clean_lines(raw_pages)

    sections = []
    level_titre = [None, None, None]  # [N. Titre, A./B. Titre, a./b. Titre] ou nom sans numero
    level_numero = [None, None, None]
    buffer = []

    def flush():
        texte = clean_text("\n".join(buffer))
        if not texte:
            return
        numero = next((n for n in reversed(level_numero) if n), "")
        titre_parts = [t for t in level_titre if t]
        chapitre_parent = clean_text(" - ".join(titre_parts[:-1])) if len(titre_parts) > 1 else clean_text(titre_parts[0]) if titre_parts else ""
        titre = clean_text(titre_parts[-1]) if titre_parts else ""
        sections.append({"numero": numero, "titre": titre, "chapitre_parent": chapitre_parent,
                          "texte": texte})

    # (niveau, regex, appliquer_sur_accents_retires)
    HEADING_KINDS = (
        (0, NAMED_TOP_12_12_RE, True),
        (0, NUMBERED_TOP_RE, False),
        (1, UPPER_LETTER_RE, False),
        (2, LOWER_LETTER_RE, False),
    )

    def match_any(line):
        for level, regex, use_stripped in HEADING_KINDS:
            m = regex.match(strip_accents(line) if use_stripped else line)
            if m:
                return level, regex, m
        return None

    def try_match_heading(line, i, n, lines):
        found = match_any(line)
        if not found:
            return None
        level, regex, m = found
        while i + 1 < n and _next_line_is_continuation(lines[i + 1]) and not match_any(lines[i + 1]):
            i += 1
            line = f"{line} {lines[i]}"
            level, regex, m = match_any(line)
        return level, regex, m, i

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        result = try_match_heading(line, i, n, lines)
        if result:
            level, regex, m, i = result
            flush()
            if regex is NAMED_TOP_12_12_RE:
                level_numero[0], level_titre[0] = None, m.group(0)
            else:
                level_numero[level], level_titre[level] = m.group(1), m.group(2)
            for lvl in range(level + 1, 3):
                level_numero[lvl], level_titre[lvl] = None, None
            buffer = []
            i += 1
            continue
        buffer.append(line)
        i += 1

    flush()
    return sections


def main():
    reader = pypdf.PdfReader(PDF_PATH)

    with open(OUT_PATH, encoding="utf-8") as f:
        corpus = json.load(f)

    doc_by_id = {d["document_id"]: d for d in corpus["documents"]}

    jobs = [
        (CIRC_18_07_2014["document_id"], extract_18_07_2014(reader)),
        (CIRC_12_12_2014["document_id"], extract_12_12_2014(reader)),
    ]

    note_suffix = (" Texte extrait du Codex Husson 2025 (Ressources_brutes/bases_legales/"
                   "39_005V_CPDF.pdf).")

    for document_id, sections in jobs:
        if note_suffix.strip() not in doc_by_id[document_id].get("notes", ""):
            doc_by_id[document_id]["notes"] = (doc_by_id[document_id].get("notes", "") + note_suffix).strip()

        # Remplace integralement les entrees de ce document a chaque
        # execution (plutot que de deduppliquer par entry_id) : le script
        # est appele a nouveau apres chaque correction de l'extraction, et
        # l'entry_id depend de l'ordre d'apparition dans `sections`, qui
        # peut changer d'une version a l'autre du script.
        corpus["sections_circulaire"] = [
            e for e in corpus.get("sections_circulaire", []) if e["document_id"] != document_id
        ]
        added = 0
        for idx, sec in enumerate(sections, start=1):
            # Index de sequence (pas juste le numero) : une meme paire
            # numero+titre peut se repeter sous 2 parents differents (ex.
            # "A. Tutelle generale d'annulation" existe a la fois sous "1."
            # et sous "2." dans la circulaire du 12/12/2014).
            entry_id = f"{document_id}#section_{idx:03d}_{slugify(sec['titre'])[:30]}"
            corpus["sections_circulaire"].append({
                "entry_id": entry_id,
                "document_id": document_id,
                "chapitre_parent": sec["chapitre_parent"],
                "numero_section": sec["numero"],
                "titre": sec["titre"],
                "texte": sec["texte"],
                "categorie": "reglementation_fabriques",
                "sous_categorie": document_id,
                "articles_references": [],
            })
            added += 1
        print(f"  {document_id}: {added} section(s) ecrite(s)")

    corpus["documents"] = list(doc_by_id.values())

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {OUT_PATH} mis a jour")


if __name__ == "__main__":
    main()

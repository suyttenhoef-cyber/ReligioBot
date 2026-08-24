"""
extract_guide_tresorier.py
-----------------
Extrait "Le guide du tresorier" (Ressources_brutes/bases_legales/
39_004V_CPDF.pdf) vers corpus_par_matiere/corpus_reglementation_fabriques.json,
matiere `reglementation_fabriques`.

Contrairement au Codex Husson (extract_codex_articles.py), ce livre n'est
pas structure en "Art. N." mais en chapitres/sous-sections numerotees
(ex. "4.1.5. Question technique : le calcul du supplement communal"). Ce
n'est pas non plus un texte officiel : c'est un guide pratique commercial
(doctrine), stocke dans `sections_circulaire[]` (reutilise du schema
existant, la cle est generique dans chunk_builder.py malgre son nom) avec
`document.type = "guide_pratique"` pour que le SYSTEM_PROMPT le traite
comme une source doctrinale, jamais comme un texte legal.

Les annexes (pages 231-264 : tableau des pieces justificatives, calendrier
du tresorier, adresses utiles...) et l'index ne sont PAS traites par ce
script (structure differente, a evaluer separement).

Usage:
    python3 scripts_ponctuels/extract_guide_tresorier.py
"""
import json
import re
import unicodedata

import pypdf

PDF_PATH = "Ressources_brutes/bases_legales/39_004V_CPDF.pdf"
OUT_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"
DOCUMENT_ID = "guide_tresorier_2025"

# Plages de pages (numeros imprimes = index pypdf + 1, meme convention que
# le Codex) reperees via la table des matieres du livre (pages 5-9).
CHAPTERS = [
    {"numero": "1", "titre": "Introduction", "start": 11, "end": 14},
    {"numero": "2", "titre": "La fabrique d'eglise", "start": 15, "end": 70},
    {"numero": "3", "titre": "La comptabilite - entree en matiere", "start": 71, "end": 94},
    {"numero": "4", "titre": "La planification - le budget et les modifications budgetaires",
     "start": 95, "end": 150},
    {"numero": "5", "titre": "L'execution - le compte annuel", "start": 151, "end": 230},
]

FOOTER_RE = re.compile(r"^\d+_\d+V\.book\s+Page\s+\d+.*$", re.IGNORECASE)
PAGENUM_RE = re.compile(r"^\d{1,4}$")
CHAPTER_HEADER_RE = re.compile(r"^Chapitre\s+\d+", re.IGNORECASE)
BOOK_TITLE_RE = re.compile(r"^Le guide du tresorier$", re.IGNORECASE)
# Titre de sous-section : numerotation a au moins 2 niveaux ("4.1", pas
# juste "1") pour ne jamais confondre avec une simple liste a puces
# numerotee dans la prose (ex. "1. Decret imperial..." en annexe).
SUBSECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.\s+(\S.*)$")

_PUNCT_MAP = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "Oe", "®": "",
    # Puces de liste (police standard ou symbolique mal mappee a
    # l'extraction PDF) -> marqueur de liste generique. Le symbole euro
    # est conserve tel quel (pertinent dans un guide comptable).
    "•": "-", "▪": "-", "♦": "-", "": "->", "": "-",
    "→": "->", "➔": "->",
})

_TRUNCATION_ENDINGS = {
    "de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en",
    "sur", "dans", "pour", "par", "l", "d", "ou", "un", "une",
}


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_all_caps_heading(line):
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _looks_truncated(line):
    words = line.split()
    if not words:
        return False
    last_word = re.sub(r"[^a-zA-Z]", "", words[-1]).lower()
    return last_word in _TRUNCATION_ENDINGS


def clean_lines(raw_pages):
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
            if CHAPTER_HEADER_RE.match(line):
                continue  # en-tete courant repete sur chaque page du chapitre
            if BOOK_TITLE_RE.match(line):
                continue  # en-tete courant (titre du livre, pages "verso")
            if is_all_caps_heading(line):
                continue
            lines.append(line)
    return lines


def slugify(text):
    text = strip_accents(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def clean_text(text):
    text = strip_accents(text)
    text = text.translate(_PUNCT_MAP)
    # Artefact d'extraction propre a ce PDF : la premiere lettre capitale
    # de certains mots (T, I, L...) est suivie d'un espace parasite avant
    # le reste du mot ("T out" -> "Tout", "I er" -> "Ier"), et de meme
    # avant une apostrophe ("L 'exercice" -> "L'exercice"). Attention : ne
    # PAS inclure "A" dans la fusion mot-a-mot, car "A defaut"/"A ce" sont
    # ici deux mots legitimes ("a" prefixe/preposition, accent deja retire
    # par strip_accents) - seule la fusion devant apostrophe reste sure
    # pour "A" (aucun cas ou "A" seul precede legitimement une apostrophe).
    text = re.sub(r"\b(\w{1,3}) (?=')", r"\1", text)
    text = re.sub(r"\b([B-Z]) (?=[a-z])", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_sections(lines, chapitre_numero, chapitre_titre):
    """Scinde les lignes nettoyees d'un chapitre en sous-sections sur base
    de la numerotation (4.1, 4.1.5...). Si aucune sous-section n'est
    detectee (ex. chapitre Introduction), tout le chapitre forme une seule
    section."""
    sections = []
    current_numero = chapitre_numero
    current_titre = chapitre_titre
    buffer = []

    def flush():
        texte = clean_text("\n".join(buffer))
        if not texte:
            return
        sections.append({
            "numero": current_numero,
            "titre": clean_text(current_titre),
            "texte": texte,
        })

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = SUBSECTION_RE.match(line)
        if m:
            while (_looks_truncated(line) and i + 1 < n
                   and not SUBSECTION_RE.match(lines[i + 1])):
                i += 1
                line = f"{line} {lines[i]}"
                m = SUBSECTION_RE.match(line)
            flush()
            current_numero = m.group(1)
            current_titre = m.group(2)
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
    doc_by_id[DOCUMENT_ID] = {
        "document_id": DOCUMENT_ID,
        "titre": "Le guide du tresorier - La gestion comptable des fabriques d'eglise (edition 2025)",
        "type": "guide_pratique",
        "statut": "en_vigueur",
        "notes": (
            "Guide pratique commercial (doctrine, PAS un texte officiel) - Vanden Broele, "
            "edition 2025. Extrait de Ressources_brutes/bases_legales/39_004V_CPDF.pdf, "
            "chapitres 1 a 5 (pages 11-230). Annexes (pieces justificatives, calendrier, "
            "adresses utiles) et index non extraits a ce stade."
        ),
    }
    corpus["documents"] = list(doc_by_id.values())

    existing_ids = {e["entry_id"] for e in corpus.get("sections_circulaire", [])}
    total_new = 0

    for chap in CHAPTERS:
        raw_pages = [reader.pages[p - 1].extract_text() for p in range(chap["start"], chap["end"] + 1)]
        lines = clean_lines(raw_pages)
        sections = extract_sections(lines, chap["numero"], chap["titre"])

        added = 0
        for sec in sections:
            entry_id = f"{DOCUMENT_ID}#section_{slugify(sec['numero'])}_{slugify(sec['titre'])[:40]}"
            if entry_id in existing_ids:
                continue
            corpus.setdefault("sections_circulaire", []).append({
                "entry_id": entry_id,
                "document_id": DOCUMENT_ID,
                "chapitre_parent": f"Chapitre {chap['numero']}. {clean_text(chap['titre'])}",
                "numero_section": sec["numero"],
                "titre": sec["titre"],
                "texte": sec["texte"],
                "categorie": "reglementation_fabriques",
                "sous_categorie": "guide_tresorier",
                "articles_references": [],
            })
            existing_ids.add(entry_id)
            added += 1
        total_new += added
        print(f"  Chapitre {chap['numero']} ({chap['titre']}): {added} section(s) ajoutee(s) "
              f"(sur {len(sections)} detectee(s))")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {total_new} nouvelles sections ecrites dans {OUT_PATH}")


if __name__ == "__main__":
    main()

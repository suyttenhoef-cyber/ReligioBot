"""
extract_codex_articles.py
-----------------
Extrait les textes legaux structures en "Art. N." (decrets, lois, arretes,
extraits du CDLD) depuis le Codex Husson (Ressources_brutes/bases_legales/
39_005V_CPDF.pdf), en s'appuyant sur la table des matieres du livre pour
delimiter chaque texte par plage de pages.

Chaque article est scinde en deux :
  - le texte legal lui-meme (verbatim, jusqu'a la premiere mention
    "Annotation :")
  - le ou les commentaires de Jean-Francois Husson qui suivent
    ("Annotation :"), stockes a part dans `exemples` et clairement
    prefixes "Annotation Husson (doctrine, pas le texte legal) :" pour
    qu'ils ne soient jamais cites comme faisant partie du texte officiel
    (cf. SYSTEM_PROMPT, groupe A3).

Les circulaires (structurees en sections titrees, pas en "Art. N.") ne sont
PAS traitees par ce script - voir extract_codex_circulaires.py.

Usage:
    python3 scripts_ponctuels/extract_codex_articles.py
"""
import json
import re
import unicodedata

import pypdf

PDF_PATH = "Ressources_brutes/bases_legales/39_005V_CPDF.pdf"
OUT_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"

# Plages de pages (numeros imprimes dans le livre = index pypdf + 1 pour ce
# PDF, verifie manuellement) reperees via la table des matieres du Codex.
# start/end = premiere et derniere page REELLEMENT extraite (les pages de
# titre et de table des matieres propres a chaque texte sont exclues).
DOCUMENTS = [
    {
        "document_id": "decret_imperial_30_12_1809",
        "titre": "Decret imperial du 30 decembre 1809 concernant les fabriques d'eglise",
        "type": "decret",
        "date_texte": "1809-12-30",
        "start": 37, "end": 54,
    },
    {
        "document_id": "loi_04_03_1870",
        "titre": "Loi du 4 mars 1870 sur le temporel des cultes",
        "type": "loi",
        "date_texte": "1870-03-04",
        "start": 59, "end": 68,
    },
    {
        "document_id": "cdld",
        "titre": "Code de la Democratie Locale et de la Decentralisation (CDLD)",
        "type": "code",
        "start": 75, "end": 92,
    },
    {
        "document_id": "decret_18_05_2017",
        "titre": "Decret du 18 mai 2017 relatif a la reconnaissance et aux obligations des etablissements cultuels",
        "type": "decret",
        "date_texte": "2017-05-18",
        "start": 99, "end": 112,
    },
    {
        # Les annexes (119-132) sont des modeles de formulaires/convention
        # avec leur propre numerotation interne ("Art. 12", "Art. 13"...
        # dans le texte-type d'une convention) qui se ferait passer pour la
        # suite des articles 1-11 de l'arrete lui-meme - non extraites ici.
        "document_id": "agw_25_01_2018",
        "titre": "Arrete du Gouvernement wallon du 25 janvier 2018",
        "type": "arrete",
        "date_texte": "2018-01-25",
        "start": 117, "end": 118,
    },
    {
        "document_id": "agw_25_02_2021",
        "titre": "Arrete du Gouvernement wallon du 25 fevrier 2021",
        "type": "arrete",
        "date_texte": "2021-02-25",
        "start": 135, "end": 136,
    },
]

FOOTER_RE = re.compile(r"^\d+_\d+V\.book\s+Page\s+\d+.*$", re.IGNORECASE)
PAGENUM_RE = re.compile(r"^\d{1,4}$")
HEADING_RE = re.compile(
    r"^(?:Chapitre|Section|TITRE|PARTIE|Livre|ANNEXE)\b|^§", re.IGNORECASE
)
ART_RE = re.compile(
    r"^\[?\s*Art(?:icle)?\.?\s*(L?\d+(?:[/\-]\d+)*(?:er|bis|ter|quater|quinquies|sexies)?)\.?\s*(.*)$",
    re.IGNORECASE,
)
# Certains textes reproduits dans une Annotation citent in extenso un
# article d'un AUTRE texte legal (ex. l'art. 22 d'un decret de 2022 cite
# dans le commentaire de l'art. L3111-1 du CDLD) : sans garde-fou, ce
# "Art. N." imbrique serait pris pour un nouvel article du document en
# cours. Pour le CDLD, tous les vrais articles de cet extrait sont
# numerotes "Lxxxx" (jamais un nombre nu) - on rejette donc tout numero
# qui ne commence pas par "L" pour ce document precis.
NUMERO_MUST_MATCH = {
    "cdld": re.compile(r"^L\d", re.IGNORECASE),
}
ANNOTATION_RE = re.compile(r"Annotation\s*:\s*", re.IGNORECASE)

# Un titre de chapitre/section trop long est parfois coupe sur 2 lignes par
# l'extraction PDF (retour a la ligne du livre) ; une ligne de titre qui se
# termine par une de ces prepositions/articles est presque surement coupee -
# on rattache alors la ligne suivante au meme titre plutot que de la traiter
# comme du texte independant.
_TRUNCATION_ENDINGS = {
    "de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en",
    "sur", "dans", "pour", "par", "l", "d", "ou", "un", "une", "aux",
}


def _looks_truncated(line):
    last_word = re.sub(r"[^a-zA-Z]", "", line.split()[-1]).lower() if line.split() else ""
    return last_word in _TRUNCATION_ENDINGS

_PUNCT_MAP = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "Oe", "®": "",
})


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_all_caps_heading(line):
    """Detecte une ligne d'en-tete/titre courant (toujours en capitales dans
    ce livre), a distinguer des titres de chapitre/section (casse mixte,
    geres par HEADING_RE) et du texte des articles (casse normale)."""
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


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
            if is_all_caps_heading(line):
                continue  # en-tete courant / titre de page repete
            lines.append(line)
    return lines


def slugify(text):
    text = strip_accents(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def clean_text(text):
    text = strip_accents(text)
    text = text.translate(_PUNCT_MAP)
    # Le Codex encadre de crochets le texte insere/modifie par un decret
    # ulterieur (convention editoriale de reperage des versions) - ce ne
    # sont pas des crochets du texte legal lui-meme, on les retire.
    text = text.replace("[", "").replace("]", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_articles(lines, document_id):
    """Parcourt les lignes nettoyees d'un texte et retourne une liste de
    dicts {numero, titre_contexte, texte, annotations}."""
    articles = []
    current_chapitre = ""
    current_section = ""
    current_sub = ""  # niveau "§"
    current_numero = None
    buffer = []

    def flush():
        if current_numero is None:
            return
        raw = "\n".join(buffer).strip()
        parts = ANNOTATION_RE.split(raw)
        legal_text = clean_text(parts[0])
        annotations = [clean_text(p) for p in parts[1:] if clean_text(p)]
        titre_contexte_parts = [p for p in [current_chapitre, current_section, current_sub] if p]
        articles.append({
            "numero": current_numero,
            "titre_contexte": clean_text(" - ".join(titre_contexte_parts)) if titre_contexte_parts else "",
            "texte": legal_text,
            "annotations": annotations,
        })

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if HEADING_RE.match(line):
            # Titre coupe sur 2 lignes par l'extraction PDF (ex. "... du
            # budget de" / "la fabrique") : rattache la ligne suivante tant
            # qu'elle ne demarre pas elle-meme un nouvel en-tete/article.
            while (_looks_truncated(line) and i + 1 < n
                   and not HEADING_RE.match(lines[i + 1])
                   and not ART_RE.match(lines[i + 1])):
                i += 1
                line = f"{line} {lines[i]}"
            if line.lower().startswith("section"):
                current_section = line
                current_sub = ""
            elif line.startswith("§"):
                current_sub = line
            else:
                current_chapitre = line
                current_section = ""
                current_sub = ""
            i += 1
            continue
        m = ART_RE.match(line)
        numero_filter = NUMERO_MUST_MATCH.get(document_id)
        if m and (numero_filter is None or numero_filter.match(m.group(1))):
            flush()
            current_numero = m.group(1)
            buffer = [m.group(2)] if m.group(2) else []
            i += 1
            continue
        if current_numero is not None:
            buffer.append(line)
        # sinon : texte avant le premier "Art." (annotation d'introduction
        # du texte, ex. sur l'AGW 2021) - non rattache a un article, ignore
        # ici (reste consultable dans le PDF source si besoin).
        i += 1

    flush()
    return articles


def main():
    reader = pypdf.PdfReader(PDF_PATH)

    with open(OUT_PATH, encoding="utf-8") as f:
        corpus = json.load(f)

    doc_by_id = {d["document_id"]: d for d in corpus["documents"]}
    existing_article_ids = {a["entry_id"] for a in corpus["articles"]}

    total_new = 0
    for doc_cfg in DOCUMENTS:
        raw_pages = [reader.pages[p - 1].extract_text() for p in range(doc_cfg["start"], doc_cfg["end"] + 1)]
        lines = clean_lines(raw_pages)
        articles = extract_articles(lines, doc_cfg["document_id"])

        doc_id = doc_cfg["document_id"]
        if doc_id in doc_by_id:
            doc_by_id[doc_id]["notes"] = (
                f"Texte extrait du Codex Husson 2025 (Ressources_brutes/bases_legales/"
                f"39_005V_CPDF.pdf), pages {doc_cfg['start']}-{doc_cfg['end']}."
            )
        else:
            doc_by_id[doc_id] = {
                "document_id": doc_id,
                "titre": doc_cfg["titre"],
                "type": doc_cfg["type"],
                "statut": "en_vigueur",
                "notes": (
                    f"Texte extrait du Codex Husson 2025 (Ressources_brutes/bases_legales/"
                    f"39_005V_CPDF.pdf), pages {doc_cfg['start']}-{doc_cfg['end']}."
                ),
            }
            if doc_cfg.get("date_texte"):
                doc_by_id[doc_id]["date_texte"] = doc_cfg["date_texte"]

        added = 0
        for art in articles:
            entry_id = f"{doc_id}#art_{slugify(art['numero'])}"
            if entry_id in existing_article_ids:
                continue  # deja extrait (re-execution du script)
            if not art["texte"]:
                continue
            exemples = [
                f"Annotation Husson (doctrine, pas le texte legal) : {a}"
                for a in art["annotations"]
            ]
            corpus["articles"].append({
                "entry_id": entry_id,
                "document_id": doc_id,
                "numero": art["numero"],
                "titre_contexte": art["titre_contexte"],
                "texte": art["texte"],
                "categorie": "reglementation_fabriques",
                "sous_categorie": doc_id,
                "articles_lies": [],
                "exemples": exemples,
            })
            existing_article_ids.add(entry_id)
            added += 1
        total_new += added
        print(f"  {doc_id}: {added} article(s) ajoute(s) (sur {len(articles)} detecte(s))")

    corpus["documents"] = list(doc_by_id.values())

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {total_new} nouveaux articles ecrits dans {OUT_PATH}")


if __name__ == "__main__":
    main()

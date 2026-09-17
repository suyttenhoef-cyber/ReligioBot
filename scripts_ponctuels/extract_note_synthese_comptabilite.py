"""
extract_note_synthese_comptabilite.py
-----------------
Integre Ressources_brutes/notes_synthese/note_synthese_comptabilite_2026.md dans
corpus_par_matiere/corpus_reglementation_fabriques.json, sous forme de
sections_circulaire[] (cle reutilisee, structurellement generique - voir
extract_guide_tresorier.py pour le precedent).

Nature de ce document : PAS un texte legal ni une circulaire officielle, mais une
note de synthese redigee pour alimenter directement cette base de connaissance
(markdown deja structure en chunks, avec ses propres marqueurs [A VERIFIER]).
Document declare avec type "note_synthese" pour le distinguer des textes
officiels (type "circulaire"/"decret"/"loi"/"code") et du guide pratique
commercial existant (type "guide_pratique") - coherent avec la regle A3 du
SYSTEM_PROMPT (ne jamais presenter une source secondaire comme le texte legal
lui-meme).

Verifie avant integration (voir conversation) : pas de contradiction relevee
avec le corpus existant sur les points factuels verifiables (dates limites
30/8 et 25/4 - loi du 4 mars 1870 art. 1/6/16/16ter ; delais de tutelle
generale d'annulation 15/30/15 jours et seuils marches publics 300.000/250.000
EUR - CDLD art. L3161-4, deja dans le corpus et plus precis que le "[A
VERIFIER]" du document source sur ce point precis). Les marqueurs [A VERIFIER]
du document source sont conserves tels quels dans le texte integre (ne pas les
faire disparaitre : ils aident le modele a rester prudent sur ces points via
les regles B4/B5 du SYSTEM_PROMPT, pas remplaces par une fausse certitude).

Sections 14 (mapping questions -> sections, un aide-memoire editorial qui pointe
vers CE document, pas un contenu citable en soi), 15 (bibliographie/sources -
metadonnee, pas une assertion verifiable) et 16 (points a valider avant mise
en production - liste de doute assumee par l'auteur, destinee aux mainteneurs
du projet, pas aux utilisateurs finaux du chatbot) sont delibererement EXCLUES
de l'ingestion et reportees dans CLAUDE.md a la place.

Sections 4, 5, 6, 7, 8, 10 sont decoupees par sous-section "### N.M" (meme
logique que pour le guide du tresorier - un chunk = une procedure/un tableau
bien delimite). Les autres (1, 2, 3, 9, 11, 12, 13) restent un chunk unique
(deja de taille raisonnable, pas de sous-titres dans la source).

Usage:
    python3 scripts_ponctuels/extract_note_synthese_comptabilite.py
"""
import json
import re
import unicodedata

SRC_PATH = "Ressources_brutes/notes_synthese/note_synthese_comptabilite_2026.md"
CORPUS_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"

DOCUMENT_ID = "note_synthese_comptabilite_2026"

# Sections a decouper par sous-titre "### N.M ..." plutot que gardees en un bloc
SPLIT_SECTIONS = {"4", "5", "6", "7", "8", "10"}
# Sections purement editoriales/meta, non ingerees comme contenu citable
EXCLUDED_SECTIONS = {"14", "15", "16"}

TOP_RE = re.compile(r"^## (\d+)\.\s+(.+?)\s*$", re.MULTILINE)
SUB_RE = re.compile(r"^### (\d+\.\d+)\s+(.+?)\s*$", re.MULTILINE)


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def slugify(text):
    text = strip_accents(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def clean_text(text):
    text = strip_accents(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Le document source separe ses "## N." par une ligne "---" (regle
    # markdown horizontale) : bruit une fois le decoupage par titre fait.
    text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def split_top_sections(raw):
    """Retourne une liste de (numero, titre, corps_brut) pour chaque '## N. Titre'."""
    matches = list(TOP_RE.finditer(raw))
    sections = []
    for i, m in enumerate(matches):
        numero, titre = m.group(1), m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections.append((numero, titre, raw[start:end]))
    return sections


def split_subsections(body):
    """Retourne [(numero_sub, titre_sub, texte)] + un eventuel intro sans numero."""
    matches = list(SUB_RE.finditer(body))
    if not matches:
        return [(None, None, body)]
    result = []
    intro = body[: matches[0].start()].strip()
    if len(clean_text(intro)) > 30:
        result.append((None, None, intro))
    for i, m in enumerate(matches):
        numero, titre = m.group(1), m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        result.append((numero, titre, body[start:end]))
    return result


def main():
    with open(SRC_PATH, encoding="utf-8") as f:
        raw = f.read()

    corpus = json.load(open(CORPUS_PATH, encoding="utf-8"))

    doc_ids = {d["document_id"] for d in corpus["documents"]}
    if DOCUMENT_ID not in doc_ids:
        corpus["documents"].append({
            "document_id": DOCUMENT_ID,
            "type": "note_synthese",
            "titre": "Comptabilite des fabriques d'eglise en Wallonie - note de synthese",
            "date_texte": "2026-09-17",
            "statut": "en_vigueur",
            "source_document": (
                "Ressources_brutes/notes_synthese/note_synthese_comptabilite_2026.md "
                "(note redigee pour alimenter directement cette base de connaissance, "
                "pas un texte officiel)"
            ),
            "notes": (
                "Synthese datee (etat du droit arrete au 17 septembre 2026), PAS un texte "
                "legal/circulaire officiel : a recouper avec les textes primaires "
                "(decrets/CDLD/circulaires deja dans ce corpus) en cas de doute, et a "
                "reviser periodiquement (comme les circulaires budgetaires communales). "
                "Conserve les marqueurs [A VERIFIER] de son auteur tels quels - un point "
                "signale incertain dans le texte reste incertain apres ingestion, pas "
                "presente comme confirme. Verifie a l'integration (2026-09-17) : pas de "
                "contradiction relevee avec les textes deja extraits (dates limites du "
                "budget/compte, delais et seuils de tutelle generale d'annulation). "
                "Sections 14 (mapping questions), 15 (bibliographie) et 16 (points a "
                "valider) du document source volontairement exclues de l'ingestion - "
                "editoriales/meta, pas du contenu citable pour un utilisateur final."
            ),
        })

    existing_ids = {s["entry_id"] for s in corpus.setdefault("sections_circulaire", [])}
    added = 0

    for numero, titre, body in split_top_sections(raw):
        if numero in EXCLUDED_SECTIONS:
            continue
        top_slug = slugify(titre)
        if numero in SPLIT_SECTIONS:
            for sub_numero, sub_titre, sub_body in split_subsections(body):
                texte = clean_text(sub_body)
                if not texte:
                    continue
                if sub_numero is None:
                    entry_numero = numero
                    entry_titre = titre
                    slug = top_slug
                else:
                    entry_numero = sub_numero
                    entry_titre = sub_titre
                    slug = slugify(sub_titre)
                entry_id = f"{DOCUMENT_ID}#section_{entry_numero.replace('.', '_')}_{slug}"[:110]
                if entry_id in existing_ids:
                    continue
                corpus["sections_circulaire"].append({
                    "entry_id": entry_id,
                    "document_id": DOCUMENT_ID,
                    "chapitre_parent": f"{numero}. {clean_text(titre)}",
                    "numero_section": entry_numero,
                    "titre": clean_text(entry_titre),
                    "texte": texte,
                })
                existing_ids.add(entry_id)
                added += 1
        else:
            texte = clean_text(body)
            if not texte:
                continue
            entry_id = f"{DOCUMENT_ID}#section_{numero}_{top_slug}"[:110]
            if entry_id in existing_ids:
                continue
            corpus["sections_circulaire"].append({
                "entry_id": entry_id,
                "document_id": DOCUMENT_ID,
                "chapitre_parent": None,
                "numero_section": numero,
                "titre": clean_text(titre),
                "texte": texte,
            })
            existing_ids.add(entry_id)
            added += 1

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"sections_circulaire ajoutees: {added}")


if __name__ == "__main__":
    main()

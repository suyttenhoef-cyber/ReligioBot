"""
extract_circulaire_budgetaire_2027.py
-----------------
Integre l'extrait "Fabriques d'eglise et communautes philosophiques non
confessionnelles reconnues" de la circulaire budgetaire communale 2027
(Ressources_brutes/bases_legales/Circulaire budgetaire-2027-communes.docx,
document Word natif - PAS un scan, extraction directe via python-docx) dans
`sections_circulaire[]` du document deja declare `circulaires_budgetaires_communales`.

Ce .docx est la circulaire budgetaire COMPLETE adressee aux communes (3382
paragraphes, format questions/reponses, 23 tableaux) : seule la section dediee
aux fabriques (Heading 3 "Fabriques d'eglise...", 4 questions/reponses, entre
la section "Regies" et la section "Depenses de dette") est extraite - le reste
(fiscalite, dette, personnel...) est hors perimetre de ce corpus.

CONSTAT IMPORTANT a signaler a l'utilisateur (pas seulement dans ce
commentaire) : la regle "evolution des dotations aux fabriques plafonnee a 1%
par an + tableau de bord prospectif (TBP)" mentionnee dans la note de synthese
2026 (note_synthese_comptabilite_2026, section 11, sourcee sur la circulaire
budgetaire 2026) est ABSENTE de cette circulaire 2027 - recherche par mot-cle
sur l'ensemble du document (pas seulement la section fabriques), aucune
occurrence de "1 %"/"TBP"/"tableau de bord prospectif" en lien avec les
fabriques. Egalement absente de l'extrait Codex Husson 2015-2025 deja au
corpus (document circulaires_budgetaires_communales, qui ne mentionne aucun
plafond chiffre d'evolution). Sans acces au texte integral de la circulaire
2026 elle-meme (on ne dispose que du resume qu'en fait la note de synthese),
impossible de trancher si la regle a ete abandonnee, deplacee ailleurs dans le
document 2026, ou si le resume de la note de synthese est imprecis - a
signaler comme incertitude plutot qu'a trancher arbitrairement.

Usage:
    python3 scripts_ponctuels/extract_circulaire_budgetaire_2027.py
"""
import json
import re
import unicodedata

import docx

DOCX_PATH = "Ressources_brutes/bases_legales/Circulaire budgetaire-2027-communes.docx"
CORPUS_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"
DOCUMENT_ID = "circulaires_budgetaires_communales"
ENTRY_ID = f"{DOCUMENT_ID}#section_002_fabriques_2027"

SECTION_HEADING = "Fabriques d’eglise et communautes philosophiques non confessionnelles reconnues"


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def extract_section(paragraphs):
    """Renvoie les paragraphes du Heading 3 'Fabriques d'eglise...' jusqu'au Heading
    de niveau <= 3 suivant (exclu)."""
    start = None
    for i, p in enumerate(paragraphs):
        if p.style.name == "Heading 3" and strip_accents(p.text).strip() == strip_accents(
            SECTION_HEADING
        ):
            start = i
            break
    if start is None:
        raise RuntimeError("Section 'Fabriques d'eglise...' introuvable (structure du document a-t-elle change ?)")

    block = []
    for p in paragraphs[start + 1:]:
        style = p.style.name
        if style in ("Heading 1", "Heading 2", "Heading 3"):
            break
        if p.text.strip():
            block.append((style, p.text.strip()))
    return block


def format_block(block):
    lines = []
    for style, text in block:
        if style == "Heading 4":
            lines.append(f"\nQ. {text}")
        else:
            lines.append(f"R. {text}")
    text = "\n".join(lines).strip()
    text = strip_accents(text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def main():
    doc = docx.Document(DOCX_PATH)
    block = extract_section(doc.paragraphs)
    texte = format_block(block)
    print(f"{len(block)} paragraphes extraits, {len(texte)} caracteres")

    corpus = json.load(open(CORPUS_PATH, encoding="utf-8"))
    sections = corpus.setdefault("sections_circulaire", [])
    sections[:] = [s for s in sections if s["entry_id"] != ENTRY_ID]

    doc_entry = next(d for d in corpus["documents"] if d["document_id"] == DOCUMENT_ID)
    doc_entry["titre"] = "Circulaires budgetaires communales annuelles (2015 a 2027)"
    doc_entry["notes"] = (
        "Deux extraits distincts : (1) une compilation multi-annees 2015-2025 tiree du Codex "
        "Husson 2025 (voir extract_codex_circulaires.py) et (2) l'extrait ci-dessous, ajoute le "
        "2026-09-17, tire directement du .docx natif de la circulaire budgetaire 2027 (pas un "
        "scan, extraction python-docx directe) fourni par l'utilisateur. "
        "INCERTITUDE A SIGNALER : la note de synthese comptable 2026 "
        "(note_synthese_comptabilite_2026, section 11) mentionne pour la circulaire budgetaire "
        "2026 une regle 'evolution des dotations aux fabriques plafonnee a 1% par an + tableau "
        "de bord prospectif (TBP)' qui n'apparait ni dans la compilation Codex 2015-2025 ni dans "
        "cet extrait de la circulaire 2027 (recherche par mot-cle sur l'integralite du document "
        "2027, pas seulement la section fabriques - aucune occurrence). Sans le texte integral "
        "de la circulaire 2026 elle-meme, impossible de savoir si cette regle a ete abandonnee, "
        "deplacee dans une autre section du document 2026, ou si le resume de la note de "
        "synthese est approximatif sur ce point precis - ne pas presenter cette regle comme "
        "certainement toujours en vigueur en 2027 sans le signaler."
    )

    sections.append({
        "entry_id": ENTRY_ID,
        "document_id": DOCUMENT_ID,
        "chapitre_parent": "Circulaire budgetaire communale 2027 - Regies, fabriques d'eglise et dette",
        "numero_section": "2027",
        "titre": "Fabriques d'eglise et communautes philosophiques non confessionnelles reconnues (circulaire budgetaire 2027)",
        "texte": texte,
        "categorie": "reglementation_fabriques",
        "sous_categorie": "circulaires_budgetaires_communales",
        "articles_references": [],
    })

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print("section ajoutee:", ENTRY_ID)


if __name__ == "__main__":
    main()

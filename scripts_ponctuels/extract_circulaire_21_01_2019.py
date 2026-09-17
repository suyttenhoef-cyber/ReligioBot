"""
extract_circulaire_21_01_2019.py
-----------------
Integre Ressources_brutes/bases_legales/Circulaire_21_01_2019.pdf dans
corpus_par_matiere/corpus_reglementation_fabriques.json, document deja declare
`circulaire_21_01_2019` (jusqu'ici 0 articles/sections - gap connu, voir
CLAUDE.md).

Particularite de ce PDF : c'est un SCAN (image), aucune couche texte (pypdf
extrait 0 caractere sur les 21 pages) - extraction par OCR (pymupdf pour
rasteriser chaque page + pytesseract/Tesseract, langue "fra"), pas un simple
decoupage de texte comme les autres scripts extract_*.py de ce projet.

Contenu du document : une lettre de couverture (1 page, non ingeree - pure
formule administrative sans information reutilisable) suivie de la "Liste des
pieces justificatives requises" par type d'acte soumis a la tutelle (pages
2-20, un grand tableau) et d'un formulaire signaletique vierge en annexe
(page 21, non ingere - un formulaire a remplir n'est pas une assertion
verifiable). C'est exactement le tableau que `extract_codex_circulaires.py`
avait du laisser de cote pour la circulaire du 12/12/2014 ("Article/Acte/
Pieces/Adresse/Annotation totalement mis a plat par l'extraction PDF
lineaire, non exploitable tel quel") - cette circulaire de 2019 EST la version
mise a jour de cette meme annexe (elle le dit explicitement en page 1 : "il en
resulte que l'annexe a la circulaire du 12 decembre 2014 doit etre adaptee").

Structure du tableau, identifiee par les en-tetes trouves dans l'OCR :
  "Actes des etablissements finances au niveau communal|provincial"
    "TUTELLE GENERALE D'ANNULATION" (ref. CDLD L3161-4 communal / L3161-8
     provincial, sous-points 1 a 5)
    "TUTELLE SPECIALE D'APPROBATION" (ref. CDLD L3162-1 par. 1er communal /
     par. 2 provincial - budget et compte)
Chaque sous-point (ex. "L3161-4, 1 ,a)") devient une entree sections_circulaire
distincte : question type "quelles pieces pour un marche de travaux / une
donation avec charge / ..." -> une seule entree courte et ciblee, plutot qu'un
gros bloc table dilue.

Piege OCR corrige : une ligne "L3161-4  3. Le cas echeant, l'avis de marche
publie..." (pas de virgule apres le code) est la SUITE d'une liste numerotee
au sein d'un sous-point deja ouvert (item "3." de l'enumeration des pieces),
PAS un nouveau sous-point "3" - seule une virgule immediatement apres le code
CDLD ("L3161-4, 3 , a)") marque un vrai debut de sous-point. Sans cette regle,
ces lignes de continuation (reference reimprimee en marge par l'OCR sur les
lignes de tableau qui debordent sur la page suivante) auraient coupe les
sous-points en fragments incoherents.

ATTENTION signalee explicitement dans les notes du document et a rappeler a
l'utilisateur : les MONTANTS cites dans certaines cases de ce tableau de 2019
(ex. seuil pret vise a L3161-4/L3161-8, 1 degre, e) peuvent etre PERIMES depuis
la reforme du CDLD par le decret du 6 octobre 2022 (deja visible dans
cdld#art_l3161_4, deja au corpus, qui porte la mention "(Remplace D.
6.10.2022...)"). La partie utile et non perimee de cette circulaire est la
liste des pieces justificatives + destinataire par type d'acte, PAS les
montants ponctuellement cites dans les descriptions - ne jamais citer un
montant de cette circulaire sans le recouper avec le texte CDLD actuel.

OCR imparfait par nature (scan, mise en page tableau multi-colonnes) : des
erreurs de caracteres isolees peuvent subsister malgre le nettoyage applique
(espaces parasites, barres "|" de bordure de tableau retirees). A verifier au
cas par cas si un doute surgit sur un point precis lors d'un usage reel.

Usage:
    python3 scripts_ponctuels/extract_circulaire_21_01_2019.py
"""
import io
import json
import os
import re
import unicodedata

import pymupdf
import pytesseract
from PIL import Image

# Sur ce poste, tesseract.exe n'est pas sur le PATH herite par ce script -
# chemin d'installation par defaut Windows, avec repli sur le PATH ailleurs.
_DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_DEFAULT_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = _DEFAULT_TESSERACT

PDF_PATH = "Ressources_brutes/bases_legales/Circulaire_21_01_2019.pdf"
CORPUS_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"
DOCUMENT_ID = "circulaire_21_01_2019"

# Page 1 = lettre de couverture, page 21 = formulaire signaletique vierge :
# ni l'une ni l'autre n'est un contenu citable pour le chatbot.
FIRST_TABLE_PAGE = 2
LAST_TABLE_PAGE = 20

FINANCEMENT_RE = re.compile(r"etablissements finances? au niveau (communal|provincial)", re.IGNORECASE)
TUTELLE_RE = re.compile(r"TUTELLE (GENERALE D.ANNULATION|SPECIALE D.APPROBATION)", re.IGNORECASE)

# Un vrai debut de sous-point a TOUJOURS une virgule juste apres le code CDLD
# (ex. "L3161-4, 1 ,a)") - une simple reprise du code en debut de ligne de
# continuation ("L3161-4  3. Le cas echeant...") n'en a pas et doit rester
# rattachee au sous-point en cours (voir piege OCR documente plus haut).
REF_RE = re.compile(
    r"^(L316[12]-\d),\s*"
    r"((?:[S$8]\s?\d\s?(?:er)?,?\s*)?\d[\u00b0\"'\u201d]?[,.]?\s*[a-h]?\)?\.?)"
)


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def ocr_pdf_pages(path, first_page, last_page):
    """Renvoie [(numero_page, texte_ocr)] pour les pages first_page..last_page (1-indexees)."""
    doc = pymupdf.open(path)
    pages = []
    for i in range(first_page - 1, last_page):
        pix = doc[i].get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="fra", config="--psm 6")
        pages.append((i + 1, text))
    return pages


def slugify(text):
    text = strip_accents(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def clean_ref_label(numero, suffix):
    label = f"{numero}, {suffix}"
    # L'OCR lit parfois le symbole degre "°" comme un guillemet courbe -
    # ex. "4”," pour "4°," - remplace uniquement ce cas (chiffre suivi
    # d'un guillemet) plutot que de risquer d'alterer un vrai guillemet ailleurs.
    label = re.sub(r"(\d)[\"'’”]", r"\1°", label)
    label = strip_accents(label)
    label = re.sub(r"\s+", " ", label).strip()
    label = re.sub(r"\s*,\s*", ", ", label)
    return label


def clean_block(lines):
    text = "\n".join(lines)
    text = strip_accents(text)
    # Barres de bordure de tableau laissees par l'OCR - bruit, pas de la ponctuation utile.
    text = text.replace("|", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    return text.strip()


def parse_table(pages):
    """Retourne une liste de dicts {ref, is_l3162, financement, tutelle, lignes}."""
    entries = []
    current = None
    financement = None
    tutelle = None

    for page_num, text in pages:
        for raw_line in text.split("\n"):
            line = strip_accents(raw_line.strip())
            if not line:
                continue
            fm = FINANCEMENT_RE.search(line)
            if fm:
                financement = fm.group(1).lower()
                continue
            tm = TUTELLE_RE.search(line)
            if tm:
                tutelle = tm.group(1).lower().replace("d'annulation", "d'annulation")
                continue
            refm = REF_RE.match(raw_line.strip())
            if refm:
                if current:
                    entries.append(current)
                numero, suffix = refm.group(1), refm.group(2)
                current = {
                    "ref": clean_ref_label(numero, suffix),
                    "is_l3162": numero.startswith("L3162"),
                    "financement": financement,
                    "tutelle": tutelle,
                    "page": page_num,
                    "lignes": [line],
                }
            elif current:
                current["lignes"].append(line)
    if current:
        entries.append(current)
    return entries


def main():
    print("OCR des pages", FIRST_TABLE_PAGE, "a", LAST_TABLE_PAGE, "(peut prendre 1-2 minutes)...")
    pages = ocr_pdf_pages(PDF_PATH, FIRST_TABLE_PAGE, LAST_TABLE_PAGE)
    entries = parse_table(pages)
    print(f"{len(entries)} sous-points detectes dans le tableau")

    corpus = json.load(open(CORPUS_PATH, encoding="utf-8"))
    doc = next(d for d in corpus["documents"] if d["document_id"] == DOCUMENT_ID)
    doc["notes"] = (
        "Circulaire du 21 janvier 2019 (SPW Interieur), qui met a jour l'annexe 'Liste des "
        "pieces justificatives requises' de la circulaire du 12/12/2014 - annexe qui n'avait "
        "justement pas pu etre extraite depuis le Codex Husson (tableau totalement aplati par "
        "l'extraction PDF lineaire, voir extract_codex_circulaires.py). PDF source scanne "
        "(aucune couche texte), extrait par OCR (pymupdf + pytesseract, langue francaise) via "
        "scripts_ponctuels/extract_circulaire_21_01_2019.py - qualite verifiee bonne sur "
        "echantillon mais des erreurs de caracteres isolees peuvent subsister. "
        "ATTENTION : les montants cites ponctuellement dans certaines cases de ce tableau "
        "(ex. seuil du marche de pret vise a L3161-4/L3161-8, 1 degre, e) datent de 2019 et "
        "peuvent etre perimes depuis la reforme du CDLD par le decret du 6 octobre 2022 (voir "
        "cdld#art_l3161_4, deja au corpus, pour les seuils actuels) - ne jamais citer un "
        "montant depuis cette circulaire sans le recouper avec le texte CDLD en vigueur. La "
        "partie non perimee et utile de ce document est la liste des pieces justificatives et "
        "du destinataire par type d'acte. Lettre de couverture (page 1) et formulaire "
        "signaletique vierge en annexe (page 21) non ingeres (pas du contenu citable)."
    )

    existing_ids = {s["entry_id"] for s in corpus.setdefault("sections_circulaire", [])}
    # Reprise propre : retire d'abord toute entree deja produite par un essai precedent
    # de ce meme script, pour ne jamais accumuler de doublons a chaque relance.
    corpus["sections_circulaire"] = [
        s for s in corpus["sections_circulaire"] if s["document_id"] != DOCUMENT_ID
    ]
    existing_ids = {s["entry_id"] for s in corpus["sections_circulaire"]}

    l3162_counters = {}
    added = 0
    for e in entries:
        texte = clean_block(e["lignes"])
        if len(texte) < 15:
            continue
        financement = e["financement"] or "non precise"
        tutelle = e["tutelle"] or "non precisee"
        chapitre = strip_accents(f"Actes finances au niveau {financement} - tutelle {tutelle}")

        if e["is_l3162"]:
            # Le contenu lui-meme precise "document budgetaire" vs "document comptable" -
            # pas la peine de forcer une distinction budget/compte depuis un OCR bruyant sur
            # le libelle du sous-point ; un compteur suffit a garantir l'unicite.
            key = financement
            l3162_counters[key] = l3162_counters.get(key, 0) + 1
            ref_display = f"L3162-1 ({financement}), partie {l3162_counters[key]}"
        else:
            ref_display = e["ref"]

        slug = slugify(ref_display)[:60]
        entry_id = f"{DOCUMENT_ID}#{slug}"
        base_id, i = entry_id, 2
        while entry_id in existing_ids:
            entry_id = f"{base_id}_{i}"
            i += 1

        corpus["sections_circulaire"].append({
            "entry_id": entry_id,
            "document_id": DOCUMENT_ID,
            "chapitre_parent": chapitre,
            "numero_section": ref_display,
            "titre": f"Pieces justificatives - {ref_display}",
            "texte": texte,
        })
        existing_ids.add(entry_id)
        added += 1

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"sections_circulaire ajoutees: {added}")


if __name__ == "__main__":
    main()

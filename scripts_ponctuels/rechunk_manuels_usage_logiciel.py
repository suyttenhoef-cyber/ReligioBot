"""
rechunk_manuels_usage_logiciel.py
-----------------
Remplace le decoupage de convert_manuels_usage_logiciel.py (un chunk par
CHAPITRE entier, jusqu'a 25000 caracteres) par une extraction directe
depuis les PDF sources, avec un vrai decoupage par sous-section - la
structure existe deja dans les manuels (ex. "3.1.1. Encodage d'une
dette/creance" dans le manuel de l'encodage des ecritures) mais n'etait
pas exploitee par l'ancienne extraction du prototype anterieur, qui avait
lumpe tout le chapitre 3 (18000+ caracteres) en un seul bloc - noyant des
details precis (ex. le champ "Statut" d'une dette/creance) dans un chunk
trop gros pour que l'embedding les fasse remonter correctement au moment
de la recherche (cas reel observe le 2026-08-25).

En-tetes reconnus (case cumulable selon le manuel) :
  - "Chapitre N." (avec suffixe ordinal eventuel, "1er")
  - "I.", "II.", "III."... (chiffres romains, utilise par les manuels qui
    n'ont pas de "Chapitre", ex. le manuel de creation de compte personnel)
  - "X.Y" / "X.Y.Z" (sous-section numerotee a l'interieur d'un chapitre)
Un manuel qui ne presente AUCUN de ces marqueurs reste un chunk unique
(comportement inchange pour les manuels courts, deja bien dimensionnes).

Usage:
    python3 scripts_ponctuels/rechunk_manuels_usage_logiciel.py
"""
import json
import re
import unicodedata

import pypdf

OUT_PATH = "corpus_par_matiere/corpus_usage_logiciel.json"
PDF_DIR = "Ressources_brutes/manuels_religiosoft"

# Reprise de la table de correspondance de convert_manuels_usage_logiciel.py
# (memes document_id/titre/sous_categorie - seul le decoupage change).
MANUELS = {
    "01": ("manuel_01_en_quelques_clics", "ReligioSoft en quelques clics (2024)",
           "prise_en_main", "01. ReligiosoftEnQuelquesClics2024.pdf"),
    "02": ("manuel_02_gestion_droits_profils", "Ma Fabrique - Gestion des droits et des profils",
           "droits_profils", "02. MaFabriqueGestionDesDroitsEtDesProfils.pdf"),
    "03": ("manuel_03_encodage_ecritures", "L'encodage des ecritures",
           "encodage_ecritures", "03. L'EncodageDesEcritures.pdf"),
    "04": ("manuel_04_plan_comptable", "Le plan comptable",
           "plan_comptable", "04. LePlanComptable.pdf"),
    "05": ("manuel_05_mandats_paiement", "Les mandats de paiement",
           "mandats_paiement", "05. LesMandatsDePaiement.pdf"),
    "06b": ("manuel_06b_approbation_compte_annuel", "Approbation du compte annuel (2024)",
            "compte_annuel", "06b. ApprobationDuCompteAnnuel2024.pdf"),
    "07": ("manuel_07_compte_annuel", "Compte annuel (2024)",
           "compte_annuel", "07. CompteAnnuel2024.pdf"),
    "08": ("manuel_08_modification_budgetaire", "Modification budgetaire (2025)",
           "budget", "08. ModificationBudgétaire 2025.pdf"),
    "09": ("manuel_09_fiches_projet", "Fiches de projet",
           "fiches_projet", "09. FichesDeProjet.pdf"),
    "11": ("manuel_11_deliberations_stockage", "Deliberations (stockage)",
           "deliberations", "11. Délibérations(Stockage).pdf"),
    "14": ("manuel_14_situation_patrimoniale", "La situation patrimoniale",
           "situation_patrimoniale", "14. LaSituationPatrimoniale.pdf"),
    "15": ("manuel_15_ajustements_internes", "Les ajustements internes",
           "ajustements_internes", "15. LesAjustementsInternes.pdf"),
    "18": ("manuel_18_compte_annuel_en_quelques_clics", "Le compte annuel 2024 en quelques clics",
           "compte_annuel", "18. Le compte annuel 2024 en quelques clics.pdf"),
    "19": ("manuel_19_compte_annuel_annexes", "Compte annuel 2024 - Annexes",
           "compte_annuel", "19. CompteAnnuel2024 - Annexes.pdf"),
    "20": ("manuel_20_module_commune_deliberations", "Module Commune - Version deliberations",
           "module_commune", "20. Module Commune Version délibérations.pdf"),
    "21": ("manuel_21_module_eveche", "Module Eveche",
           "module_eveche", "21. Module Evêché.pdf"),
    "22": ("manuel_22_module_groupement", "Module groupement",
           "module_groupement", "22. Module groupement.pdf"),
    "23": ("manuel_23_pieces_justificatives_stockage", "Pieces justificatives (stockage)",
           "pieces_justificatives", "23. PiècesJustificativesStockage.pdf"),
    "24": ("manuel_24_automatisation_ecritures", "Automatisation des ecritures",
           "encodage_ecritures", "24. Automatisation des écritures.pdf"),
    "25": ("manuel_25_astuces_techniques", "Les astuces techniques",
           "astuces_techniques", "25. Les astuces techniques.pdf"),
    "26": ("manuel_26_releves_creance", "Releves de creance",
           "releves_creance", "26. Relevés de créance.pdf"),
    "27": ("manuel_27_droits_constates", "Droits constates",
           "droits_constates", "27. Droits constatés.pdf"),
    "28": ("manuel_28_etapes_tutelle", "Gestion des etapes de tutelle",
           "tutelle", "28. Gestion des étapes de tutelle.pdf"),
    "29": ("manuel_29_creation_compte_personnel", "Creation du compte personnel",
           "creation_compte", "29. CréationDuComptePersonnel.pdf"),
    "66": ("manuel_66_fusion_fabriques", "Fusion de fabriques",
           "fusion_fabriques", "66. Fusion de fabriques.pdf"),
}

# Bruit d'en-tete/pied de page : la maquette de ces manuels repete le
# titre du manuel + la mention "Vanden Broele" + l'URL sur (presque)
# chaque page (avant OU apres le numero de page selon la page).
# "Vanden Broele" seul suffit (verifie : toujours present dans le pied de
# page reel) - NE PAS filtrer sur la seule presence d'une URL religio(soft)
# .be, qui peut aussi apparaitre dans du vrai contenu (ex. un titre "III.
# www.religiosoft.be - connexion directe !").
NOISE_RE = re.compile(r"Vanden Broele", re.IGNORECASE)
PAGENUM_RE = re.compile(r"^\d{1,4}$")

# PAS de re.IGNORECASE ici : une reference en milieu de phrase ("... Le
# chapitre 3 explique...", "chapitre" en minuscule car pas en debut de
# phrase) doit rester du texte normal, pas etre prise pour un titre reel
# (toujours "Chapitre" avec un C majuscule dans ces manuels).
CHAPTER_RE = re.compile(r"^Chapitre\s+(\S+)\.?\s*(.*)$")
ROMAN_RE = re.compile(r"^(X{0,3}(?:IX|IV|V?I{1,3}))\.\s+(\S.*)$")
SUBSECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.\s+(\S.*)$")
# Certains manuels "pas a pas" (ex. le compte annuel) numerotent leurs
# sous-etapes "1re etape :", "2e etape :"... plutot que X.Y - la presence
# du ":" en plus du chiffre+suffixe ordinal limite le risque de faux
# positif sur une phrase qui mentionnerait une etape en passant.
ETAPE_RE = re.compile(r"^(\d+)(?:re|ère|e|ème)\s+[ée]tape\s*:\s*(\S.*)$", re.IGNORECASE)
# D'autres manuels (ex. les annexes du compte annuel) n'ont ni "Chapitre"
# ni chiffres romains mais des lettres majuscules ("A. Titre", "B. Titre").
# Essayee seulement si ROMAN_RE n'a pas matche (une lettre isolee comme
# "I."/"V."/"X." reste traitee comme chiffre romain en priorite).
UPPER_LETTER_RE = re.compile(r"^([A-Z])\.\s+(\S.*)$")

_PUNCT_MAP = str.maketrans({
    "’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "…": "...", "œ": "oe", "Œ": "Oe", "®": "",
    "•": "-", "▪": "-", "♦": "-",
    "→": "->", "➔": "->",
})
_PUNCT_MAP.update(str.maketrans({chr(0xF0E8): "->", chr(0xF0F0): "-", chr(0xF0B7): "-",
                                  chr(0xF04B): "-", chr(0xF05A): "-"}))


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def is_all_caps_heading(line):
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _next_line_is_continuation(next_line):
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
    text = re.sub(r"\b([A-Z]) (?=')", r"\1", text)
    text = re.sub(r"\b([B-Z]) (?=[a-z])", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_lines(reader):
    lines = []
    for page in reader.pages:
        for line in (page.extract_text() or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            if PAGENUM_RE.match(line):
                continue
            if NOISE_RE.search(line):
                continue
            if is_all_caps_heading(line):
                continue
            lines.append(line)
    return lines


def extract_manual(pdf_path):
    """Retourne une liste de sections {numero, titre_contexte, texte}."""
    reader = pypdf.PdfReader(pdf_path)
    lines = clean_lines(reader)

    sections = []
    current_top = ""
    current_sub_numero = None
    current_sub_titre = None
    buffer = []

    def flush():
        texte = clean_text("\n".join(buffer))
        if len(texte) < 30:
            return  # residu de sommaire/page de garde, sans valeur
        titre_contexte_parts = [p for p in [current_top, current_sub_titre] if p]
        sections.append({
            "numero": current_sub_numero or "",
            "titre_contexte": clean_text(" - ".join(titre_contexte_parts)) if titre_contexte_parts else "",
            "texte": texte,
        })

    def match_top(candidate):
        return (CHAPTER_RE.match(candidate) or ROMAN_RE.match(candidate)
                or UPPER_LETTER_RE.match(candidate))

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m_top = match_top(line)
        if m_top:
            while (i + 1 < n and _next_line_is_continuation(lines[i + 1])
                   and not match_top(lines[i + 1]) and not SUBSECTION_RE.match(lines[i + 1])
                   and not ETAPE_RE.match(lines[i + 1])):
                i += 1
                line = f"{line} {lines[i]}"
                m_top = match_top(line)
            flush()
            current_top = m_top.group(2).strip() or m_top.group(1)
            current_sub_numero, current_sub_titre = None, None
            buffer = []
            i += 1
            continue
        m_sub = SUBSECTION_RE.match(line) or ETAPE_RE.match(line)
        if m_sub:
            while (i + 1 < n and _next_line_is_continuation(lines[i + 1])
                   and not SUBSECTION_RE.match(lines[i + 1]) and not ETAPE_RE.match(lines[i + 1])
                   and not match_top(lines[i + 1])):
                i += 1
                line = f"{line} {lines[i]}"
                m_sub = SUBSECTION_RE.match(line) or ETAPE_RE.match(line)
            flush()
            current_sub_numero, current_sub_titre = m_sub.group(1), m_sub.group(2)
            buffer = []
            i += 1
            continue
        buffer.append(line)
        i += 1

    flush()
    return sections


def main():
    with open(OUT_PATH, encoding="utf-8") as f:
        corpus = json.load(f)

    documents = []
    all_articles = []
    for numero, (document_id, titre, sous_categorie, pdf_name) in MANUELS.items():
        pdf_path = f"{PDF_DIR}/{pdf_name}"
        sections = extract_manual(pdf_path)
        documents.append({
            "document_id": document_id,
            "titre": titre,
            "type": "manuel_utilisateur",
            "statut": "en_vigueur",
            "notes": f"Source: Ressources_brutes/manuels_religiosoft/{pdf_name}",
        })
        for idx, sec in enumerate(sections, start=1):
            entry_slug = slugify(sec["numero"] or sec["titre_contexte"] or str(idx))
            all_articles.append({
                "entry_id": f"{document_id}#{idx:03d}_{entry_slug}",
                "document_id": document_id,
                "numero": sec["numero"] or str(idx),
                "titre_contexte": sec["titre_contexte"],
                "texte": sec["texte"],
                "categorie": "usage_logiciel",
                "sous_categorie": sous_categorie,
                "articles_lies": [],
                "exemples": [],
            })
        print(f"  manuel {numero} ({titre}): {len(sections)} section(s)")

    corpus["documents"] = documents
    corpus["articles"] = all_articles

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {len(documents)} documents, {len(all_articles)} articles ecrits dans {OUT_PATH}")


if __name__ == "__main__":
    main()

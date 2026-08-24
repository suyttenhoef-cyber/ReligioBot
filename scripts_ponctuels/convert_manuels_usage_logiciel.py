"""
convert_manuels_usage_logiciel.py
-----------------
Script ponctuel : convertit les extractions JSON deja realisees sur le
prototype anterieur (Ressources_brutes/extraction_manuels_ancienne/
manuel_structure_llm_bis_*.json) vers le schema du corpus attendu par
chunk_builder.py, pour les 25 VRAIS manuels utilisateur ReligioSoft
(hors les 4 ouvrages CPDF - Codex Husson, guide du tresorier, guide
tutelle, histoire des fabriques - traites separement vu leur volume et
leur decoupage encore a construire).

Remappe champ a champ (pas de nouvelle extraction LLM - le texte source
existe deja dans contenu_texte) :
  id/chemin/titre        -> entry_id / titre_contexte
  contenu_texte           -> texte
  categorie (matiere)     -> "usage_logiciel" fixe
  sous-categorie          -> table MANUELS ci-dessous (par manuel)
  etapes_processus +
  questions_frequentes    -> exemples (liste de chaines)

Usage:
    python3 scripts_ponctuels/convert_manuels_usage_logiciel.py
"""
import glob
import json
import re
import unicodedata
from pathlib import Path

SRC_DIR = Path("Ressources_brutes/extraction_manuels_ancienne")
OUT_PATH = Path("corpus_par_matiere/corpus_usage_logiciel.json")

# Les 4 ouvrages CPDF (Codex, guide tresorier, guide tutelle, histoire des
# fabriques) sont exclus de cette conversion - traites separement.
EXCLUDE_PATTERNS = ["39_001V_CPDF", "39_004V_CPDF", "39_005V_CPDF", "41_039V_CPDF"]

# Table de correspondance numero de manuel -> (document_id, titre lisible,
# sous_categorie, nom du PDF source dans Ressources_brutes/manuels_religiosoft/).
# Construite a la main (25 entrees) car le titre reel du document n'est pas
# fiable dans l'extraction JSON (les fichiers a une seule section portent le
# titre generique "Document complet").
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


def strip_accents(text):
    """Retire les accents francais - contrainte d'encodage du pipeline
    (convention deja en usage sur chatbot_etat_civil, cf. README)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def slugify(text):
    text = strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


# Ponctuation typographique -> equivalent ASCII simple, meme convention que
# chatbot_etat_civil (verifie sur son corpus : apostrophes/guillemets
# courbes normalises en droits).
_PUNCT_MAP = str.maketrans({
    "’": "'", "‘": "'",
    "“": '"', "”": '"',
    "«": '"', "»": '"',
    "–": "-", "—": "-",
    "…": "...",
    "œ": "oe", "Œ": "Oe",
    "®": "",
    # Puces/icones de listes provenant de polices symboliques (Wingdings et
    # assimiles) mal mappees en Unicode lors de l'extraction PDF - aucune
    # de ces polices n'est incluse dans le PDF, donc le glyphe reel est
    # perdu ; on les normalise en un marqueur de liste generique.
    "•": "-", "": "-", "": "-", "": "-", "": "-",
    # Fleches (meme cause) -> equivalent ASCII "->"
    "➔": "->", "": "->",
})


def clean(text):
    """Nettoyage minimal : accents retires + ponctuation typographique
    normalisee en ASCII (convention du pipeline, cf. chatbot_etat_civil),
    espaces normalises. Ne touche pas au contenu autrement (pas de
    reformulation)."""
    if not text:
        return ""
    text = strip_accents(text)
    text = text.translate(_PUNCT_MAP)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def find_source_file(numero):
    pattern = str(SRC_DIR / f"manuel_structure_llm_bis_{numero}._*.json")
    matches = glob.glob(pattern)
    if len(matches) != 1:
        raise RuntimeError(f"Attendu 1 fichier pour le manuel {numero}, trouve {len(matches)}: {matches}")
    return matches[0]


def build_articles(numero, document_id, sous_categorie):
    path = find_source_file(numero)
    with open(path, encoding="utf-8") as f:
        sections = json.load(f)

    articles = []
    for idx, section in enumerate(sections, start=1):
        texte = clean(section.get("contenu_texte", ""))
        if not texte:
            continue  # section vide, rien a indexer

        titre_section = clean(section.get("titre", ""))
        entry_slug = slugify(section.get("id") or titre_section or str(idx))

        exemples = []
        for etape_idx, etape in enumerate(section.get("etapes_processus") or [], start=1):
            exemples.append(f"Etape {etape_idx}: {clean(etape)}")
        for qa in section.get("questions_frequentes") or []:
            q = clean(qa.get("question", ""))
            r = clean(qa.get("reponse", ""))
            if q and r:
                exemples.append(f"Q: {q} R: {r}")

        articles.append({
            "entry_id": f"{document_id}#{entry_slug}",
            "document_id": document_id,
            "numero": str(idx),
            "titre_contexte": titre_section,
            "texte": texte,
            "categorie": "usage_logiciel",
            "sous_categorie": sous_categorie,
            "articles_lies": [],
            "exemples": exemples,
        })

    return articles


def main():
    excluded = []
    for numero, (document_id, titre, sous_categorie, pdf_name) in MANUELS.items():
        try:
            find_source_file(numero)
        except RuntimeError as e:
            excluded.append((numero, str(e)))
    if excluded:
        for numero, msg in excluded:
            print(f"ATTENTION - manuel {numero} ignore : {msg}")

    documents = []
    all_articles = []
    for numero, (document_id, titre, sous_categorie, pdf_name) in MANUELS.items():
        articles = build_articles(numero, document_id, sous_categorie)
        documents.append({
            "document_id": document_id,
            "titre": titre,
            "type": "manuel_utilisateur",
            "statut": "en_vigueur",
            "notes": f"Source: Ressources_brutes/manuels_religiosoft/{pdf_name}",
        })
        all_articles.extend(articles)
        print(f"  manuel {numero} ({titre}): {len(articles)} article(s)")

    corpus = {
        "_matiere": "usage_logiciel",
        "documents": documents,
        "articles": all_articles,
        "sections_circulaire": [],
        "pratiques_validees": [],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"\nOK - {len(documents)} documents, {len(all_articles)} articles ecrits dans {OUT_PATH}")


if __name__ == "__main__":
    main()

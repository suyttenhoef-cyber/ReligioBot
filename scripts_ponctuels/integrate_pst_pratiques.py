"""
integrate_pst_pratiques.py
-----------------
Integre Ressources_brutes/emails_pst/candidats.json (voir dump_pst_emails.py
et parse_pst_emails.py) dans le corpus, sous forme de `pratiques_validees[]` -
meme format que l'import FAQ Connect de chatbot_etat_civil (document_id
`faq_connect_xml`, type "faq_export_helpdesk", 1257 -> 530 entrees).

Filtre supplementaire applique ici : une reponse de moins de 50 caracteres
est presque toujours un accuse de reception pur ("Nous avons fait le
necessaire.", "Merci pour ce document.") sans valeur generalisable pour
une future question - exclue.

Classification automatique (heuristique par mots-cles, pas une lecture
individuelle de 1400 entrees) :
  - matiere : reglementation_fabriques si des mots-cles legaux/tutelle
    dominent, usage_logiciel sinon (majoritaire dans l'echantillon observe).
  - sous_categorie : bucket approximatif par mots-cles (encodage, budget,
    compte_annuel, droits_acces, peppol_mercurius, tutelle_reglementation,
    autre) - moins fin qu'une revue individuelle mais suffisant pour un
    filtrage grossier, comme le corpus existant le fait deja pour les
    manuels.

Code de reference : PV-UL-NNN / PV-RF-NNN, sequentiel a partir du nombre
de pratiques_validees deja presentes dans chaque fichier de matiere.

Usage:
    python3 scripts_ponctuels/integrate_pst_pratiques.py
"""
import json
import re
import unicodedata

IN_PATH = "Ressources_brutes/emails_pst/candidats.json"
USAGE_LOGICIEL_PATH = "corpus_par_matiere/corpus_usage_logiciel.json"
REGLEMENTATION_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"

MIN_REPONSE_LEN = 50

DOCUMENT_ID = "helpdesk_pst_2026"

LEGAL_KEYWORDS = [
    "cdld", "decret", "circulaire", "tutelle", "gouverneur", "arrete du gouvernement",
    "conseil communal", "conseil provincial", "loi du", "eveque", "dissolution",
    "fusion de fabrique", "reconnaissance", "desaffectation", "gouvernement wallon",
]
SOUS_CATEGORIE_KEYWORDS = [
    ("peppol_mercurius", ["peppol", "mercurius", "facture electronique", "facture digitale"]),
    ("encodage_ecritures", ["encoder", "encodage", "ecriture", "dettes et creances",
                            "comptes bancaires", "coda", "extrait bancaire"]),
    ("budget", ["budget", "modification budgetaire", " mb ", "mb2"]),
    ("compte_annuel", ["compte annuel", "compte de rectification", "cloture", "clôture"]),
    ("droits_acces", ["acces", "accès", "droit de lecture", "mot de passe", "compte personnel",
                       "creer un compte", "créer un compte"]),
    ("tutelle_reglementation", LEGAL_KEYWORDS),
]


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
    return text.strip()


def classify_matiere(text_lower):
    legal_hits = sum(1 for kw in LEGAL_KEYWORDS if kw in text_lower)
    return "reglementation_fabriques" if legal_hits >= 2 else "usage_logiciel"


def classify_sous_categorie(text_lower):
    for name, keywords in SOUS_CATEGORIE_KEYWORDS:
        if any(kw in text_lower for kw in keywords):
            return name
    return "autre"


def ensure_document(corpus):
    doc_ids = {d["document_id"] for d in corpus["documents"]}
    if DOCUMENT_ID not in doc_ids:
        corpus["documents"].append({
            "document_id": DOCUMENT_ID,
            "type": "faq_export_helpdesk",
            "titre": "Archives email du helpdesk Vanden Broele (cultes@religiosoft.be)",
            "date_texte": None,
            "statut": "en_vigueur",
            "source_document": "backup.pst (dossier \"archives Lisa\")",
            "notes": (
                "Export d'archives email du helpdesk Religiosoft (1722 emails bruts, "
                "septembre 2026). Anonymise (noms/emails/telephones/adresses retires par "
                "coupure structurelle de la salutation et de la signature, pas seulement "
                "masquage cible) et filtre : entrees sans question d'origine identifiable "
                "(newsletters, invitations) ou avec reponse de moins de 50 caracteres (simple "
                "accuse de reception sans valeur generalisable) exclues. "
                f"{{added}} entrees retenues sur 1722 emails bruts au total. "
                "Matiere et sous-categorie determinees par mots-cles (heuristique automatique, "
                "pas une revue individuelle de chaque entree)."
            ),
        })


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        candidates = json.load(f)

    usage = json.load(open(USAGE_LOGICIEL_PATH, encoding="utf-8"))
    regl = json.load(open(REGLEMENTATION_PATH, encoding="utf-8"))
    corpora = {"usage_logiciel": usage, "reglementation_fabriques": regl}

    codes_seen = {
        "usage_logiciel": len(usage.get("pratiques_validees", [])),
        "reglementation_fabriques": len(regl.get("pratiques_validees", [])),
    }
    code_prefix = {"usage_logiciel": "PV-UL", "reglementation_fabriques": "PV-RF"}

    added_count = {"usage_logiciel": 0, "reglementation_fabriques": 0}
    skipped_short = 0

    for cand in candidates:
        reponse = clean_text(cand["reponse"])
        question = clean_text(cand["question"])
        if len(reponse) < MIN_REPONSE_LEN:
            skipped_short += 1
            continue

        subject = clean_text(cand.get("subject", "")) or "Question du helpdesk"
        subject_display = re.sub(r"^(re|rv|tr)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()

        text_lower = (question + " " + reponse + " " + subject).lower()
        matiere = classify_matiere(text_lower)
        sous_categorie = classify_sous_categorie(text_lower)

        codes_seen[matiere] += 1
        code = f"{code_prefix[matiere]}-{codes_seen[matiere]:03d}"
        entry_id = f"pratique_{cand['index']:04d}_{slugify(subject_display)[:40]}"

        date_reponse = (cand.get("received_time") or "").split(" ")[0] or None

        corpora[matiere].setdefault("pratiques_validees", []).append({
            "entry_id": entry_id,
            "document_id": DOCUMENT_ID,
            "code": code,
            "titre": subject_display[:120],
            "question_origine": question,
            "texte": reponse,
            "precise_ou_complete": [],
            "date_reponse": date_reponse,
            "source_validation": "Archives email helpdesk Vanden Broele (anonymise, backup.pst)",
            "categorie": matiere,
            "sous_categorie": sous_categorie,
        })
        added_count[matiere] += 1

    for matiere, corpus in corpora.items():
        ensure_document(corpus)
        for d in corpus["documents"]:
            if d["document_id"] == DOCUMENT_ID and "{added}" in d.get("notes", ""):
                d["notes"] = d["notes"].replace("{added}", str(added_count["usage_logiciel"] + added_count["reglementation_fabriques"]))

    with open(USAGE_LOGICIEL_PATH, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)
    with open(REGLEMENTATION_PATH, "w", encoding="utf-8") as f:
        json.dump(regl, f, ensure_ascii=False, indent=2)

    print(f"Candidats traites: {len(candidates)}")
    print(f"  reponse trop courte (<{MIN_REPONSE_LEN} car., accuse de reception): {skipped_short}")
    print(f"  ajoutes a usage_logiciel: {added_count['usage_logiciel']}")
    print(f"  ajoutes a reglementation_fabriques: {added_count['reglementation_fabriques']}")
    print(f"  total pratiques_validees ajoutees: {sum(added_count.values())}")


if __name__ == "__main__":
    main()

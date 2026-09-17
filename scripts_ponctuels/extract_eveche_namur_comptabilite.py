"""
extract_eveche_namur_comptabilite.py
-----------------
Integre Ressources_brutes/bases_legales/12a_rappel_des_grands_principes_de_comptabilite_2020.pdf
("La comptabilite fabricienne", Eveche de Namur, Vicariat du temporel du culte,
service aux fabriques d'eglise, 02/2020) dans corpus_par_matiere/corpus_reglementation_fabriques.json,
sous forme de sections_circulaire[] - nouveau document `eveche_namur_comptabilite_2020`.

C'est l'un des 3 documents recommandes a l'utilisateur a partir de la bibliographie (section
"Sources") de note_synthese_comptabilite_2026, celle-ci le qualifiant explicitement de "source
la plus complete sur le plan comptable article par article". PDF avec une vraie couche texte
(pas un scan, contrairement a Circulaire_21_01_2019.pdf) - extraction directe via pypdf, decoupage
par ancres de texte fixes (document court et bien connu, 12 pages dont les 4 dernieres blanches -
pas la peine d'un parseur regex generique pour un document traite une seule fois).

Chevauchement assume avec note_synthese_comptabilite_2026 (section 4, plan comptable R1-R28/D1-D62)
: CE document est plus detaille (explications en prose completes, references legales en note de
bas de page - art. 45 et 26 du decret de 1809, loi du 3 juillet 2005 sur le volontariat...) et
donne des montants precis SPECIFIQUES AU DIOCESE DE NAMUR (droits de fabrique sur inhumations :
25 EUR funerailles/mariages, 12,50 EUR absoutes, 5 EUR autres services, "depuis le 1er janvier
2020") explicitement absents de la note de synthese (qui ne disait que "tarif fixe par decret
episcopal, variable par diocese"). Les deux documents sont conserves plutot que l'un au detriment
de l'autre - la redondance partielle est un compromis assume plutot qu'un probleme a resoudre,
cf. meme logique deja appliquee pour le Codex Husson et le guide du tresorier (deux sources sur la
meme base legale, cadrees differemment).

Verifie a l'integration (recoupement demande par l'utilisateur) : aucune contradiction relevee
avec le corpus existant sur les points verifiables - tarif des messes fondees (13/25/7 EUR,
arrete ministeriel du 2 avril 2010) identique a la note de synthese ET confirme encore valide en
02/2020 (pas d'indexation entre 2010 et 2020, meme si le "[A VERIFIER]" de la note de synthese sur
une eventuelle indexation PLUS RECENTE reste ouvert) ; remise du tresorier (5% hors art. 17/18a),
subsides provinciaux (>= 1% du montant des travaux subsidies), dates limites (30 aout / 25 avril),
delais de tutelle (20j / 40j+20j) : tous coherents avec ce qui est deja au corpus.

Usage:
    python3 scripts_ponctuels/extract_eveche_namur_comptabilite.py
"""
import json
import re
import unicodedata

import pypdf

PDF_PATH = "Ressources_brutes/bases_legales/12a_rappel_des_grands_principes_de_comptabilite_2020.pdf"
CORPUS_PATH = "corpus_par_matiere/corpus_reglementation_fabriques.json"
DOCUMENT_ID = "eveche_namur_comptabilite_2020"

# Ancres de texte (debut de section, tel qu'elles apparaissent dans le texte extrait par pypdf)
# -> (numero_section, titre). Document court et connu une fois pour toutes : decoupage par
# ancres fixes plutot qu'un parseur regex generique.
ANCHORS = [
    ("1. PRINCIPES", "1", "Les six principes de la comptabilite fabricienne"),
    ("2. LE BUDGET", "2", "Le budget"),
    ("3.  LE COMPTE", "3", "Le compte"),
    ("4. ELEMENTS DE LA COMPTABILITE FABRICIENNE", "4", "Elements de la comptabilite fabricienne"),
    ("LES RECETTES", "5", "Les recettes - introduction et recettes ordinaires (articles 1 a 18)"),
    ("2. RECETTES EXTRAORDINAIRES", "5.2", "Recettes extraordinaires (articles 19 a 28)"),
    ("LES DEPENSES", "6", "Les depenses - introduction et depenses du chapitre I (articles 1 a 15)"),
    ("2. DEPENSES DU CHAPITRE II", "6.2", "Depenses du chapitre II, ordinaires et extraordinaires (articles 16 a 62)"),
]
# Pied de page a couper avant integration (mentions/coordonnees, pas du contenu).
FOOTER_MARKER = "Eveche de Namur"


def strip_accents(text):
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def clean_text(text):
    text = strip_accents(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def main():
    reader = pypdf.PdfReader(PDF_PATH)
    full_text = strip_accents("\n".join(p.extract_text() for p in reader.pages))
    footer_pos = full_text.find(FOOTER_MARKER)
    if footer_pos == -1:
        raise RuntimeError(f"Marqueur de pied de page introuvable : {FOOTER_MARKER!r}")
    full_text = full_text[:footer_pos]

    positions = []
    for anchor, numero, titre in ANCHORS:
        pos = full_text.find(anchor)
        if pos == -1:
            raise RuntimeError(f"Ancre introuvable : {anchor!r} (structure du PDF a-t-elle change ?)")
        positions.append((pos, anchor, numero, titre))
    positions.sort()

    corpus = json.load(open(CORPUS_PATH, encoding="utf-8"))
    doc_ids = {d["document_id"] for d in corpus["documents"]}
    if DOCUMENT_ID not in doc_ids:
        corpus["documents"].append({
            "document_id": DOCUMENT_ID,
            "type": "guide_pratique",
            "titre": "La comptabilite fabricienne - rappel des grands principes",
            "date_texte": "2020-02-01",
            "statut": "en_vigueur",
            "source_document": (
                "12a_rappel_des_grands_principes_de_comptabilite_2020.pdf - Eveche de Namur, "
                "Vicariat du temporel du culte, service aux fabriques d'eglise (02/2020)"
            ),
            "notes": (
                "Document de doctrine (PAS un texte officiel) redige par l'Eveche de Namur pour "
                "expliquer le plan comptable des fabriques article par article - recommande dans "
                "la bibliographie de note_synthese_comptabilite_2026 comme 'la source la plus "
                "complete sur le plan comptable article par article'. Certains montants cites "
                "(droits de fabrique sur inhumations/mariages) sont EXPLICITEMENT propres au "
                "diocese de Namur ('depuis le 1er janvier 2020') - ne pas les generaliser aux "
                "autres dioceses wallons sans verification (le document le precise lui-meme, "
                "tarif fixe par decret episcopal, variable par diocese). Chevauchement assume "
                "avec note_synthese_comptabilite_2026 (section 4, meme plan comptable R1-R28/"
                "D1-D62) - conserve pour ses explications plus completes et ses references "
                "legales en note de bas de page, meme logique que la coexistence Codex "
                "Husson / guide du tresorier deja dans ce corpus. Verifie a l'integration "
                "(2026-09-17) : aucune contradiction relevee avec le corpus existant."
            ),
        })

    sections = corpus.setdefault("sections_circulaire", [])
    sections[:] = [s for s in sections if s["document_id"] != DOCUMENT_ID]

    added = 0
    for i, (pos, anchor, numero, titre) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(full_text)
        texte = clean_text(full_text[pos:end])
        if not texte:
            continue
        entry_id = f"{DOCUMENT_ID}#section_{numero.replace('.', '_')}"
        sections.append({
            "entry_id": entry_id,
            "document_id": DOCUMENT_ID,
            "chapitre_parent": None,
            "numero_section": numero,
            "titre": titre,
            "texte": texte,
        })
        added += 1

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"sections_circulaire ajoutees: {added}")


if __name__ == "__main__":
    main()

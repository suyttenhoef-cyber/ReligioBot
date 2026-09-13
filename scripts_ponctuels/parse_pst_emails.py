"""
parse_pst_emails.py
-----------------
Traite Ressources_brutes/emails_pst/raw_dump.json (1722 emails bruts du
helpdesk Religiosoft, voir dump_pst_emails.py) pour en tirer des candidats
question/reponse anonymises, prets pour une revue humaine avant integration
eventuelle en `pratiques_validees`.

Chaque email du helpdesk contient typiquement :
  - la reponse (en haut du corps) ;
  - une signature Vanden Broele fixe (Mazerin Business Center, BTW BE...) ;
  - un separateur puis l'email d'origine cite ("From:"/"De :"/"Van:" ou
    "Le <date>, <nom> a ecrit :") avec la question du tresorier et sa
    propre signature.

Etapes :
  1. Scinder reponse / question citee sur le premier marqueur de citation.
  2. Tronquer la reponse a la signature Vanden Broele (bloc fixe).
  3. Extraire l'expediteur/destinataire de la question citee.
  4. Anonymiser : remplacer les noms connus (sender/to/cc de l'email ET de
     la citation), les adresses email et les numeros de telephone par des
     placeholders generiques.
  5. Filtrer : ne garder que les emails ou une vraie question a ete
     retrouvee (longueur minimale des deux cotes) - ecarte naturellement
     les newsletters/invitations qui ne citent aucune question.
  6. Ecrire un JSON de candidats (`Ressources_brutes/emails_pst/candidats.json`,
     NON commite) + un apercu Markdown lisible pour une revue rapide
     (`Ressources_brutes/emails_pst/apercu.md`, NON commite non plus).

Rien n'est integre au corpus par ce script - c'est une etape de
preparation pour revue humaine (voir CLAUDE.md).

Usage:
    python3 scripts_ponctuels/parse_pst_emails.py
"""
import json
import re

IN_PATH = "Ressources_brutes/emails_pst/raw_dump.json"
OUT_JSON = "Ressources_brutes/emails_pst/candidats.json"
OUT_MD = "Ressources_brutes/emails_pst/apercu.md"

# Marqueur de debut de citation (email d'origine repris dans la reponse).
QUOTE_RE = re.compile(
    r"^(From|De|Van)\s*:\s*.*$|^Le\s+.{3,60}\s+a\s+écrit\s*:\s*$",
    re.MULTILINE | re.IGNORECASE,
)
# Champs de l'en-tete de citation (nom + email eventuel).
QUOTE_FIELD_RE = re.compile(
    r"^(From|Sent|To|Cc|Subject|De|Envoyé|À|Objet|Van|Verzonden|Aan|Onderwerp)\s*:\s*(.*)$",
    re.IGNORECASE,
)
NAME_EMAIL_RE = re.compile(r"^(.*?)\s*<([^>]+@[^>]+)>\s*$")

# Ancres fixes de la signature Vanden Broele (bloc identique sur ~99% des
# emails du helpdesk) - tout ce qui suit dans la reponse est coupe.
SIGNATURE_ANCHORS = [
    "Vanden Broele SA", "Mazerin Business Center", "Helpdesk Religiosoft",
    "BTW BE 0451", "Part of the Vanden Broele Group",
]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# (?<![\d/]) / (?!\d) : evite de mordre sur une date ("07/08/2026 14:52:46")
# qui, sans ces gardes-fous, se fait partiellement engloutir par le motif.
PHONE_RE = re.compile(r"(?<![\d/])(?:\+32\s?|0)\d(?:[\s./]?\d{2}){3,4}(?!\d)")
# Avertissement automatique Outlook sur les expediteurs peu familiers -
# bruit sans valeur, a retirer (peut apparaitre dans la reponse ou dans la
# question citee). Outlook formule cet avertissement de 2 facons ("Certaines
# personnes..." a la 3e personne, ou "Vous n'obtenez pas souvent..." a la
# 2e personne selon le contexte) - les deux terminent par le meme lien.
OUTLOOK_WARNING_RE = re.compile(
    r"(Certaines personnes qui ont reçu cet e-mail|Vous n.obtenez pas souvent d.e-mail)"
    r".*?LearnAboutSenderIdentification>\s*",
    re.DOTALL,
)
# Longue ligne de tirets/underscores : marque une citation imbriquee
# (reponse a une reponse) meme sans en-tete "From:" explicite juste apres.
SEPARATOR_LINE_RE = re.compile(r"^[_-]{10,}$")

# Anonymiser au coup par coup (noms connus via metadonnees, emails,
# telephones) laissait passer trop de donnees personnelles : le poste,
# l'organisation et l'adresse postale dans une signature ne sont pas
# couverts par ces regex cible. Approche retenue : COUPER structurellement
# la salutation d'ouverture et tout le bloc de signature/cloture, pour ne
# garder que le coeur du message - plus robuste qu'essayer de masquer
# chaque type de donnee personnelle un par un.

# Salutation d'ouverture ("Bonjour Madame X", "Bonjour,", "Cher Monsieur"...)
# sur la ou les toutes premieres lignes non vides.
GREETING_RE = re.compile(
    r"^(bonjour|bonsoir|cher|ch[eè]re|chers|mesdames|messieurs|madame|monsieur)\b.*$",
    re.IGNORECASE,
)

# Formules de cloture qui marquent le debut du bloc signature (nom, poste,
# organisation, adresse, telephone...) - tout ce qui suit est ecarte.
# Phrases choisies suffisamment specifiques pour eviter un faux positif
# sur une phrase normale de la question (ex. pas de simple "merci" seul,
# trop frequent en milieu de question : "merci de me dire...").
CLOSING_PHRASES = [
    r"cordialement", r"bien à vous", r"bien à toi", r"bien cordialement",
    r"sinc[eè]res salutations", r"meilleures salutations",
    r"salutations distingu[ée]es?", r"recevez.{0,40}salutations",
    r"veuillez agr[ée]er", r"je vous prie d.agr[ée]er",
    r"merci d.avance", r"merci beaucoup et bonne", r"bonne r[ée]ception",
    r"^salutations\s*$", r"^bien à vous\s*$",
    r"^belle\s+(journée|soirée|semaine)\s*[!.]*\s*$",
    r"^bonne\s+(journée|soirée|semaine)\s*[!.]*\s*$",
    # "Merci" seul (ligne complete, pas suivi d'une vraie demande) est un
    # signal de cloture sur - contrairement a "merci de me confirmer..."
    # (une demande en milieu de question) qui continue sur la meme ligne
    # et ne correspond donc pas a ce motif ancre en debut ET fin de ligne.
    r"^merci\s*[!.]{0,3}\s*$",
]
CLOSING_RE = re.compile("|".join(CLOSING_PHRASES), re.IGNORECASE)

# Ligne d'adresse postale belge typique (code postal a 4 chiffres + ville)
# - sert de filet de securite meme sans formule de cloture explicite.
ADDRESS_LINE_RE = re.compile(r"^\W*\d{4}\s+\S")

# Nom de tiers mentionne AU FIL DU TEXTE (pas seulement dans la salutation
# d'ouverture ou la signature deja coupees) - "Madame Chemotti" (personnel
# Vanden Broele interpelle par son nom), "Mme Ploumhans" (tiers dont il est
# question) - motif generique et sur (une civilite + nom propre n'est
# quasiment jamais un faux positif) plutot qu'une liste de noms connus.
NAME_TITLE_RE = re.compile(
    r"\b(?:M\.|Mme\.?|Mr\.?|Madame|Monsieur|Mademoiselle)\s+"
    r"[A-ZÀ-Ý][a-zà-ÿ]+(?:[-\s][A-ZÀ-Ý][a-zà-ÿ]+){0,2}"
)
# NOTE (essaye puis abandonne le 2026-09-11) : une liste globale de tous
# les prenoms/noms vus dans Sender/To/Cc sur les 1722 emails, decoupee en
# tokens et reinjectee comme regex de redaction generique, semblait couvrir
# le cas du prenom seul sans civilite ("Paul, le tresorier..."). En
# pratique elle etait bien trop agressive : des mots courants ("sur",
# "sous") et des noms de lieux/fabriques (Charleroi, Tournai, "Notre Dame",
# "Peppol") coincidaient avec des fragments de noms de famille ailleurs
# dans le jeu de donnees et rendaient le texte incomprehensible. Un prenom
# isole non detecte est un risque bien plus tolerable que la destruction
# du sens du texte - reste donc a la charge de la revue humaine.


def strip_noise(text):
    return OUTLOOK_WARNING_RE.sub("", text)


def isolate_core_text(text):
    """Coupe la salutation d'ouverture et tout ce qui suit la premiere
    formule de cloture (ou la premiere ligne d'adresse postale) - ne garde
    que le coeur substantiel du message, sans nom, poste, organisation,
    adresse ni telephone de signature."""
    text = strip_noise(text)
    lines = text.split("\n")

    # Coupe la salutation d'ouverture (1-2 premieres lignes non vides).
    start = 0
    stripped_greeting = 0
    while start < len(lines) and stripped_greeting < 2:
        line = lines[start].strip()
        if not line:
            start += 1
            continue
        if GREETING_RE.match(line):
            start += 1
            stripped_greeting += 1
            continue
        break
    lines = lines[start:]

    # Coupe au premier signal de cloture/signature (formule ou ligne
    # d'adresse), sur les lignes RESTANTES.
    cut_at = len(lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if CLOSING_RE.search(stripped) or ADDRESS_LINE_RE.match(stripped) or SEPARATOR_LINE_RE.match(stripped):
            cut_at = i
            break
    lines = lines[:cut_at]

    return "\n".join(lines).strip()


def clean_reply(text):
    text = strip_noise(text)
    cut_at = len(text)
    for anchor in SIGNATURE_ANCHORS:
        idx = text.find(anchor)
        if idx != -1:
            cut_at = min(cut_at, idx)
    text = text[:cut_at]
    return isolate_core_text(text)


def split_reply_and_quote(body):
    m = QUOTE_RE.search(body)
    if not m:
        return body.strip(), None
    reply = body[: m.start()]
    rest = body[m.start():]
    return reply.strip(), rest


def parse_quote_header(quoted_block):
    """Extrait les champs d'en-tete (From/Sent/To/Cc/Subject) en tete du
    bloc cite, et retourne (header_dict, texte_apres_entete)."""
    lines = quoted_block.split("\n")
    header = {}
    i = 0
    # Ligne 0 = le marqueur lui-meme (From: ... ou "Le X a ecrit :") - deja
    # capture si c'est un champ From/De/Van, sinon on saute juste la ligne.
    first_field = QUOTE_FIELD_RE.match(lines[0].strip())
    if first_field:
        header[first_field.group(1).lower()] = first_field.group(2).strip()
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        fm = QUOTE_FIELD_RE.match(line)
        if fm:
            header[fm.group(1).lower()] = fm.group(2).strip()
            i += 1
            continue
        if not line:
            i += 1
            continue
        break
    remaining = "\n".join(lines[i:])
    return header, remaining.strip()


def extract_name_email(field_value):
    if not field_value:
        return "", ""
    m = NAME_EMAIL_RE.match(field_value.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return field_value.strip(), ""


def anonymize(text, names_emails):
    """Remplace les noms/emails connus pour CET echange (pas une detection
    generique) par des placeholders - beaucoup plus fiable qu'une
    heuristique NLP generique, car on connait deja les personnes
    impliquees via les metadonnees Outlook et l'en-tete de citation."""
    for name in names_emails.get("names", []):
        name = name.strip()
        if len(name) >= 3:
            text = re.sub(re.escape(name), "[PERSONNE]", text, flags=re.IGNORECASE)
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[TELEPHONE]", text)
    text = NAME_TITLE_RE.sub("[PERSONNE]", text)
    return text


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    candidates = []
    skipped_no_quote = 0
    skipped_too_short = 0

    for rec in raw:
        reply_raw, quoted_block = split_reply_and_quote(rec["body"])
        if quoted_block is None:
            skipped_no_quote += 1
            continue

        header, question_raw = parse_quote_header(quoted_block)
        # Coupe la question a la citation suivante si le fil contient
        # plusieurs allers-retours (on ne garde que l'echange le plus
        # recent, le plus susceptible d'etre la question a laquelle la
        # reponse repond directement).
        m2 = QUOTE_RE.search(question_raw)
        if m2:
            question_raw = question_raw[: m2.start()]

        reply_clean = clean_reply(reply_raw)
        question_clean = isolate_core_text(question_raw)

        # Seuil abaisse par rapport a la version precedente : l'isolation
        # structurelle (salutation + signature retirees) raccourcit
        # legitimement des questions/reponses courtes qui passaient avant
        # uniquement grace au volume de la signature qu'elles contenaient.
        if len(reply_clean) < 25 or len(question_clean) < 25:
            skipped_too_short += 1
            continue

        from_name, from_email = extract_name_email(header.get("from") or header.get("de") or header.get("van") or "")
        names = {rec.get("sender_name", ""), from_name}
        for field in (rec.get("to", ""), rec.get("cc", ""), header.get("to", ""), header.get("cc", "")):
            for part in re.split(r"[;,]", field or ""):
                part = extract_name_email(part)[0]
                if part:
                    names.add(part)
        names = {n for n in names if n and n.lower() != "religiosoft - cultes"}

        anon = {"names": names}
        question_anon = anonymize(question_clean, anon)
        reply_anon = anonymize(reply_clean, anon)
        subject_anon = anonymize(rec.get("subject", ""), anon)

        candidates.append({
            "index": rec["index"],
            "entry_id": rec["entry_id"],
            "subject": subject_anon,
            "received_time": rec["received_time"],
            "question": question_anon,
            "reponse": reply_anon,
        })

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# Apercu des candidats question/reponse ({len(candidates)} au total)\n\n")
        f.write("Genere automatiquement pour revue humaine - anonymisation par "
                "remplacement des noms/emails/telephones connus, a verifier "
                "avant toute integration au corpus.\n\n---\n\n")
        for c in candidates:
            f.write(f"## {c['index']}. {c['subject']} ({c['received_time']})\n\n")
            f.write(f"**Question :**\n\n{c['question']}\n\n")
            f.write(f"**Reponse :**\n\n{c['reponse']}\n\n---\n\n")

    print(f"Emails traites: {len(raw)}")
    print(f"  sans citation retrouvee (newsletters/annonces/etc.): {skipped_no_quote}")
    print(f"  question ou reponse trop courte apres nettoyage: {skipped_too_short}")
    print(f"  candidats retenus: {len(candidates)}")
    print(f"\nOK - {OUT_JSON} et {OUT_MD} ecrits")


if __name__ == "__main__":
    main()

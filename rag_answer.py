"""
rag_answer.py
-----------------
Point d'entree du POC : pose une question, recupere le contexte pertinent
dans le corpus ReligioSoft (reglementation des fabriques d'eglise + usage du
logiciel), et genere une reponse en forcant la citation des sources (texte
legal + article/section exact, ou manuel utilisateur + section exacte).

IMPORTANT : fait de vrais appels reseau vers l'API OpenAI. Ne peut PAS etre
execute dans le sandbox Claude. A executer dans ton environnement avec
OPENAI_API_KEY.

Prerequis:
    pip install openai numpy
    export OPENAI_API_KEY="sk-..."
    (avoir deja lance chunk_builder.py puis embed_chunks.py au prealable)

Usage:
    python3 rag_answer.py "Comment injecter un fichier CODA dans ReligioSoft ?"
"""
import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import OpenAI

from retrieve import Retriever, format_results_for_prompt

load_dotenv()  # charge OPENAI_API_KEY depuis un fichier .env si present

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"  # ajuster selon budget/qualite souhaitee (ex: gpt-4o)

SYSTEM_PROMPT = """Tu es un assistant expert du logiciel ReligioSoft (Editions Vanden Broele) et \
de la reglementation comptable/legale des fabriques d'eglise en Region wallonne (Belgique). \
Deux publics t'utilisent : des tresoriers de fabriques d'eglise (souvent des benevoles, pas \
forcement a l'aise avec l'informatique ni le jargon comptable/juridique), et l'equipe support/ \
helpdesk Vanden Broele qui repond a ces tresoriers et a besoin d'une reponse rapide et sourcee. \
Tu reponds UNIQUEMENT a partir des extraits de manuels utilisateur et de textes legaux/circulaires \
fournis en contexte ci-dessous.

Regles strictes, groupees par theme :

## A. Citation des sources
A1. Chaque affirmation factuelle doit etre appuyee par une source du contexte, citee \
explicitement. Pour un texte legal/circulaire : nom du texte + numero d'article ou de section \
(ex. "(CDLD, art. L3162-1)" ou "(Circulaire du 12 decembre 2014 relative a la tutelle sur les \
actes, section 3)"). Pour le manuel utilisateur ReligioSoft : nom du manuel + section/chapitre \
concerne (ex. "(Manuel 'Les mandats de paiement', chapitre 2)").
A2. Avant de rediger ta reponse, parcours TOUT le contexte fourni (pas seulement les passages \
les plus pertinents en tete de liste) : une question peut relever a la fois du fonctionnement du \
logiciel ET d'une regle comptable/legale sous-jacente (ex. une question sur l'encodage d'une \
ecriture peut impliquer une regle du plan comptable impose par la reglementation). Cite les deux \
niveaux quand ils sont tous deux presents et pertinents, plutot que de n'en retenir qu'un.
A3. Distingue toujours la norme legale/reglementaire (decret, loi, CDLD, arrete) de son \
interpretation administrative (circulaire), du mode d'emploi du logiciel (manuel utilisateur \
ReligioSoft), d'un guide pratique commercial (ex. "Le guide du tresorier" - doctrine et bonnes \
pratiques d'un editeur, PAS un texte officiel meme s'il cite et explique la loi), et de toute \
pratique validee (clarification de terrain issue d'un cas concret, validee par un expert \
interne, mais qui n'est ni un texte legal ni un manuel officiel) quand \
plusieurs de ces niveaux apparaissent dans le contexte. Une pratique validee ne remplace jamais \
un texte officiel ni le manuel : signale-la explicitement comme telle, par exemple "(pratique \
interne validee, ref. VDB-PV-RF-014)" - reprends TOUJOURS le code de reference tel qu'il \
apparait dans la source (prefixe "VDB-" inclus), sans jamais la presenter comme une circulaire, \
un article de loi ou une page du manuel officiel. Meme logique pour un passage marque \
"Annotation Husson (doctrine, pas le texte legal)" dans le contexte : c'est le commentaire \
personnel de l'auteur du Codex annote, jamais le texte legal lui-meme meme s'il figure juste \
apres l'article qu'il commente - utile pour expliquer ou nuancer, mais ne le cite jamais comme \
si c'etait l'article de loi, et signale-le explicitement comme une interpretation doctrinale \
si tu t'en sers pour repondre.
A4. EXCEPTION a A3 : si la source d'une pratique validee indique "[S'APPUIE SUR : ...]", cite en \
PRIORITE cette reference (legale ou manuel) pour l'affirmation concernee, et ne mentionne la \
pratique validee qu'en complement.
A5. Chaque pratique validee indique sa date de reponse dans sa source (entre parentheses). Si le \
contexte contient a la fois une pratique validee et un texte officiel ou un manuel plus recent \
traitant du meme sujet et pouvant la contredire, privilegie toujours la source officielle la plus \
recente (les circulaires budgetaires communales annuelles et les versions du manuel evoluent \
chaque annee). Si une pratique validee comporte une mention "ATTENTION - POTENTIELLEMENT \
OBSOLETE", signale-le explicitement et invite l'utilisateur a verifier aupres de la source \
officielle citee.

## B. Face a l'incertitude : ne jamais inventer
B1. Si le contexte fourni ne permet pas de repondre avec certitude, dis-le clairement plutot \
que d'inventer une reponse. Ne comble jamais une lacune par une supposition, meme plausible - \
une reponse fausse mais assuree est pire qu'une reponse honnetement incertaine, en particulier \
pour un tresorier benevole qui n'a pas les moyens de la remettre en question lui-meme.
B2. NE CITE JAMAIS un numero d'article ou une section de manuel precis qui n'apparait PAS \
textuellement dans le contexte fourni pour ce numero-la, meme si le sujet general de la question \
concerne un texte ou un manuel present dans le contexte. Si aucun passage du contexte ne traite \
reellement du sujet precis de la question, dis-le clairement (B1) et cite au mieux la source \
generale par son nom SANS numero invente, plutot que d'inventer une reference par plausibilite. \
Une reference inventee est une des pires erreurs possibles pour ce public : elle donne une \
fausse impression de certitude verifiee.
B3. Quand un ELEMENT FACTUEL DECISIF manque dans la question pour trancher entre plusieurs \
reponses possibles selon la situation reelle (par exemple : type de fabrique concernee, montant \
en jeu, exercice budgetaire concerne, presence ou non d'une convention pluriannuelle, version du \
logiciel utilisee, module concerne), TA PRIORITE ABSOLUE EST DE POSER LA QUESTION QUI TE MANQUE, \
PAS DE DEVINER NI DE TOUT ENUMERER. La PREMIERE phrase de ta reponse doit alors demander \
explicitement l'information manquante, avec une phrase expliquant pourquoi elle change la \
reponse - pas une enumeration qui tente de couvrir tous les cas a la place de demander. Reserve \
l'enumeration des cas (regle D1) aux situations ou il y a EXACTEMENT DEUX cas possibles, tres \
simples, ET ou les deux reponses tiennent chacune en une phrase courte.
B4. Le score de pertinence indique entre parentheses apres chaque source ("pertinence: X.XX") \
est une indication de confiance sur le retrieval, pas une garantie que le sujet precis de la \
question est couvert. Si les scores disponibles sont visiblement bas, ou si aucun passage ne \
traite reellement de la situation precise decrite (meme s'ils abordent un theme general voisin), \
dis-le CLAIREMENT et EXPLICITEMENT ("le corpus disponible ne semble pas couvrir precisement ce \
cas" ou une formulation equivalente) plutot que d'assembler une reponse a partir de ces passages \
partiellement pertinents comme si elle etait bien fondee. Dans ce cas, rappelle egalement que le \
helpdesk Vanden Broele (cultes@religiosoft.be, 02 308 29 06) peut etre contacte directement.
B5. Cas particulier et frequent de B4, a traiter avec une vigilance renforcee : une question qui \
decrit une SITUATION PRECISE ET COMPOSEE DE PLUSIEURS FAITS SPECIFIQUES ne doit donner lieu a \
une reponse tranchee ("oui c'est correct", "voici les etapes") QUE si au moins un passage du \
contexte traite EXPLICITEMENT de cette situation precise - pas seulement du meme theme ou \
principe general. Concerne notamment deux cas frequents sur ce corpus :
   - une ACTION PRECISE dans le logiciel (ex. "comment supprimer/modifier/effacer X", "ou \
   trouver le bouton Y", "quelle etape suit Z apres avoir fait W") : le contexte qui traite du \
   compte annuel en general ne documente pas forcement comment supprimer une date de validation \
   apres suppression d'une modification budgetaire ;
   - un CAS COMPTABLE COMPOSE DE PLUSIEURS FAITS PARTICULIERS SUCCESSIFS (ex. une correction, \
   suivie d'un remboursement demande, suivi d'un virement interne effectue par erreur par la \
   fabrique, creant un doublon a corriger) : un passage qui explique le principe general \
   ("le resultat comptable doit correspondre au solde bancaire", "toute erreur doit etre \
   corrigee") ne suffit PAS a valider ou invalider une solution proposee pour CETTE combinaison \
   precise de faits - ce type de situation est par nature un jugement d'expert au cas par cas, \
   pas quelque chose qu'un guide general peut trancher.
Dans les deux cas, si le contexte ne couvre que le sujet general sans traiter la situation \
precise decrite, NE CONSTRUIS PAS une reponse plausible par extrapolation ou par raisonnement \
comptable/logiciel general : dis explicitement que cette situation precise n'est pas documentee \
dans le corpus disponible (B1/B4) et oriente vers le helpdesk ou, pour un cas comptable \
compose, vers une verification par un professionnel/le diocese. Une reponse tranchee construite \
par extrapolation sur un cas compose est aussi grave qu'un numero d'article invente (B2) : \
l'utilisateur (ou l'agent du helpdesk) risque de considerer a tort qu'une solution a ete validee \
par la documentation. En cas de doute sur le fait qu'un passage couvre vraiment la situation \
precise ou seulement un theme voisin, tranche TOUJOURS en faveur de la prudence (B1) plutot que \
de l'exhaustivite apparente.

## C. Ne jamais transposer aveuglement une pratique validee a un cas different
Une pratique validee documente un cas CONCRET anterieur, avec ses propres faits precis. Avant \
d'en reprendre quoi que ce soit pour la question actuelle, verifie systematiquement :
C1. DETAILS SPECIFIQUES : une pratique illustre souvent son raisonnement avec des details ou \
donnees propres a ce cas-la (ex. un montant precis, une fabrique precise, un exercice budgetaire \
precis). Ne les reprends JAMAIS comme s'ils s'appliquaient au dossier actuel, meme si le sujet \
est similaire. Retiens uniquement la methode ou le raisonnement general qu'elle illustre, et \
base ta reponse sur les donnees fournies dans la question. Si ces donnees manquent, dis-le et \
demande-les (voir B3), plutot que de combler le vide avec l'exemple d'un autre dossier.
C2. PREMISSES DE FOND : verifie que les PREMISSES ou conditions de fond decisives de la pratique \
(type de fabrique, existence ou non d'une convention pluriannuelle avec la commune, module ou \
version du logiciel concerne, exercice budgetaire) correspondent reellement a la situation \
decrite - pas seulement le sujet general. Le retrieval se base sur une ressemblance semantique \
globale, pas sur cette nuance comptable ou legale precise - c'est a toi de la verifier a chaque \
fois. Si une premisse ne correspond pas, NE PLAQUE PAS la conclusion de la pratique sur le cas \
actuel : signale explicitement que la situation differe, explique en quoi, et base ta reponse \
uniquement sur les sources officielles disponibles, ou indique qu'une verification specifique \
aupres du helpdesk Vanden Broele est necessaire.
C3. ALTERNATIVES SECONDAIRES : cette meme vigilance s'applique aux ALTERNATIVES ou SUGGESTIONS \
secondaires mentionnees par une pratique, pas seulement a sa conclusion principale.
C4. NE CONTREDIS JAMAIS la conclusion EXPLICITE d'une pratique validee par ta propre deduction a \
partir d'un detail annexe qu'elle mentionne. En cas de doute entre ce que dit explicitement la \
pratique et ta propre inference, la pratique a toujours raison.
C5. N'ATTRIBUE JAMAIS une affirmation a une reference (VDB-... ou source officielle) qui ne la \
soutient pas reellement. Une citation incorrecte (bon raisonnement, mauvaise reference) est aussi \
grave qu'une affirmation inventee : en cas de doute sur la source exacte, cite la source generale \
plutot qu'une reference precise incertaine, ou omets la reference plutot que d'en inventer une.

## D. Structure et ton de la reponse (public non-specialiste par defaut)
Le public par defaut (tresorier benevole) n'est pas a l'aise avec le jargon comptable, juridique \
ou informatique : sois clair et pragmatique, mais ne sacrifie jamais la substance a la brievete. \
Structure chaque reponse ainsi :
D1. Une PREMIERE phrase qui donne directement l'essentiel de la reponse, adaptee au TYPE de \
question - ne force JAMAIS un verdict "Oui/Non" sur une question qui n'en appelle pas un :
   - Question fermee (peut-on, doit-on, a-t-on le droit de...) : "Oui, vous pouvez...", "Non, il \
   faut d'abord...", "Cela depend de X : ...".
   - Question ouverte (comment/quand/quelles pieces/ou trouver...) : une phrase qui donne \
   directement le coeur de la reponse sans "Oui" ou "Non" artificiel.
D2. Ensuite, explique en quelques phrases normales (pas uniquement des puces) le raisonnement : \
sur quelle base (legale ou fonctionnement du logiciel), quelle logique, quelle condition precise \
justifie cette reponse. Utilise une liste a puces uniquement quand il y a reellement plusieurs \
elements a enumerer (pieces a fournir, etapes a l'ecran, conditions).
D3. Des qu'une question porte sur une MANIPULATION PRECISE dans ReligioSoft (une procedure a \
suivre a l'ecran, pas juste une explication generale) et que le contexte la documente \
explicitement (condition de la regle B5) : la reponse DOIT prendre la forme d'une liste \
NUMEROTEE (1. 2. 3. ...), une action concrete et executable par etape, jamais un paragraphe de \
prose qui noie les etapes dans du texte continu. Reprends l'ORDRE exact du manuel, sans en \
sauter ni en supposer une qui n'y figure pas explicitement, et cite le nom exact de chaque \
element d'interface (menu, bouton, onglet, champ) entre guillemets tel qu'il apparait dans le \
contexte (ex. "Cliquez sur "comptabilite", puis sur "dettes et creances""), plutot qu'une \
paraphrase approximative. Si le manuel decoupe deja la procedure en etapes numerotees ou en \
"1re etape", "2e etape"..., reprends cette meme numerotation et ce meme decoupage - ne les \
fusionne pas et n'en resume pas plusieurs en une seule ligne. Une etape qui suppose un clic ou \
un ecran non mentionne dans le contexte ne doit pas etre ajoutee (B5) : indique plutot, a la fin \
de la liste, que la suite n'est pas documentee precisement si c'est le cas.
D4. Les exceptions ou cas particuliers, s'il y en a, dans une section separee et clairement \
annoncee ("Attention, cas particuliers : ..."), jamais noyees dans la reponse principale.
D5. Phrases courtes et vocabulaire simple - mais chaque phrase doit rester complete et \
argumentee, pas un fragment telegraphique. La regle A1 (citation systematique) s'applique a \
CHAQUE affirmation, y compris dans les puces. Tout terme technique, comptable ou juridique peu \
courant doit etre explique en quelques mots entre parentheses des sa premiere apparition.

## E. Format technique
E1. Ne termine PAS ta reponse par un avertissement/disclaimer : celui-ci est ajoute \
automatiquement apres coup par l'application, ne le repete pas toi-meme.
E2. Meme si la question est collee sous la forme d'un ticket, d'un email ou d'un echange avec un \
tresorier (ex. "Bonjour, ... Cordialement, Jacques"), ne redige JAMAIS ta reponse comme si tu \
etais toi-meme l'auteur de cet echange : pas de formule d'ouverture ("Bonjour Jacques"), pas de \
formule de fermeture ("Cordialement"), et surtout jamais de signature ou de placeholder du type \
"[Votre Nom]". Identifie la question reelle posee dans le texte colle et reponds-y directement, \
dans le meme registre neutre que pour n'importe quelle autre question ("Voici ce que dit la \
documentation : ...") - a charge pour la personne qui utilise l'outil de reformuler la reponse \
en email si elle le souhaite."""

NO_RESULTS_MESSAGE = (
    "Aucun passage du corpus n'est jugé suffisamment pertinent pour répondre "
    "avec certitude à cette question. Reformule ta question, vérifie "
    "manuellement les sources concernées, ou contacte le helpdesk Vanden "
    "Broele (cultes@religiosoft.be, 02 308 29 06)."
)

# Rappel affiche a la fin de chaque reponse - ajoute programmatiquement (pas
# genere par le modele) pour garantir un texte et une mise en forme
# strictement identiques a chaque fois. Voir app.py (st.caption) pour le
# rendu visuel.
DISCLAIMER_TEXT = (
    "Cette reponse est une aide et ne remplace ni une verification comptable "
    "par un professionnel, ni le helpdesk officiel Vanden Broele "
    "(cultes@religiosoft.be, 02 308 29 06) en cas de doute."
)

# Filet de securite contre les citations d'article/section fabriquees (regle
# B2 du SYSTEM_PROMPT) : detecte un numero d'article ou de section cite dans
# la reponse ("art. N" / "article N") qui ne correspond a AUCUN article/
# section officiel present parmi les passages retrouves. Ne verifie pas le
# sens de la citation (un numero present mais cite pour un mauvais sujet ne
# serait pas detecte) - c'est un filet minimal contre l'invention pure d'un
# numero, pas une verification semantique complete.
_CITATION_RE = re.compile(
    r"\bart(?:icle)?s?\.?\s*([A-Z]?[0-9]+(?:[/-][0-9]+)*"
    r"(?:bis|ter|quater|quinquies|sexies|septies|octies)?)",
    re.IGNORECASE,
)


def check_citation_integrity(results, answer_text, query=""):
    """Retourne la liste (triee) des numeros d'article cites dans
    answer_text qui ne correspondent a aucune source officielle (statut_entree
    != "reference_interne") parmi les passages effectivement fournis au
    modele dans `results`. Un numero deja present dans la question de
    l'utilisateur (`query`) est exclu : ce n'est pas une citation inventee
    par le modele mais un element (souvent un article budgetaire comptable,
    ex. "D62A", "R28D" - homonyme du mot "article" au sens legal que ce
    garde-fou visait au depart) simplement repris de ce que l'utilisateur a
    lui-meme indique."""
    cited = {m.upper() for m in _CITATION_RE.findall(answer_text)}
    if not cited:
        return []
    query_upper = query.upper()
    cited = {n for n in cited if n not in query_upper}
    if not cited:
        return []
    available = {
        str(meta["numero"]).strip().upper()
        for _, meta in results
        if meta.get("statut_entree") != "reference_interne" and meta.get("numero")
    }
    return sorted(n for n in cited if n not in available)


# Deuxieme garde-fou (complementaire a check_citation_integrity ci-dessus),
# integre des le depart sur ce projet (cf. CLAUDE.md) suite a un cas reel
# rencontre sur chatbot_etat_civil ou le modele avait cite un article REEL et
# bien present dans le contexte (donc invisible pour check_citation_integrity,
# qui ne verifie que l'EXISTENCE du numero) mais traitant en realite d'un
# sujet voisin sans rapport avec l'affirmation qu'il etait cense soutenir.
# check_citation_integrity ne peut structurellement pas detecter ce cas ;
# celui-ci verifie le CONTENU de chaque citation, pas seulement sa presence.
CITATION_RELEVANCE_SYSTEM_PROMPT = """Tu verifies, APRES la redaction d'une reponse, si chaque \
citation (article/section legale, section de manuel, ou pratique validee) qui y figure soutient \
REELLEMENT l'affirmation a laquelle elle est associee - pas seulement si la reference citee \
existe parmi les sources, mais si son CONTENU dit vraiment ce que la reponse lui fait dire.

Piege frequent a detecter : une source existe reellement et traite d'un sujet VOISIN ou \
SUPERFICIELLEMENT SIMILAIRE (meme theme general, mots-cles partages - ex. meme module du \
logiciel, meme type d'operation comptable) mais concerne en realite un point different (une \
autre etape, une autre condition, un autre exercice budgetaire) de celui evoque par \
l'affirmation citee. Dans ce cas, la citation est incorrecte meme si la reference est \
parfaitement reelle et presente dans les sources.

Pour chaque citation presente dans la reponse, compare son texte integral (fourni ci-dessous \
parmi les sources) a l'affirmation precise qu'elle est censee soutenir. Si le texte de la source \
citee ne soutient PAS reellement cette affirmation precise, signale-le - notamment si un AUTRE \
passage parmi ceux fournis semble plus directement pertinent pour cette affirmation. Ne signale \
PAS une citation simplement parce qu'elle est generale ou incomplete : signale uniquement un vrai \
decalage entre le sujet de la source et l'affirmation qu'elle est censee soutenir.

Reponds UNIQUEMENT avec un objet JSON de la forme :
{"citations_douteuses": [{"citation": "<reference telle que citee dans la reponse>", \
"probleme": "<une phrase courte expliquant pourquoi cette source ne soutient pas l'affirmation>", \
"source_plus_pertinente": "<numero d'une autre source fournie qui semble plus adaptee, ou null>"}]}
Liste vide si toutes les citations sont correctement appliquees."""


def check_citation_relevance(client, query, results, answer_text):
    """Verifie, via un appel LLM dedie, que chaque citation presente dans
    answer_text est bien appliquee a son sujet reel (pas seulement qu'elle
    existe - voir check_citation_integrity pour cette verification
    syntaxique complementaire). Cout : un appel LLM supplementaire par
    reponse - retourne (issues, usage) comme filter_applicable_practices,
    pour que l'appelant puisse inclure ce cout dans sa telemetrie. Robuste
    par construction : toute erreur (reseau, JSON invalide, reponse non
    parsable...) renvoie ([], None) plutot que de bloquer la reponse - un
    faux negatif de cette verification ne doit jamais empecher de repondre
    a l'utilisateur."""
    if not answer_text or not results:
        return [], None

    sources_desc = "\n\n".join(
        f"- reference: {meta.get('numero') or meta.get('chunk_id')}\n"
        f"  titre: {meta.get('titre_contexte') or ''}\n"
        f"  contenu: {meta['text_for_embedding'][:1500]}"
        for _, meta in results
    )
    user_message = (
        f"Question posee : {query}\n\n"
        f"Reponse generee a verifier :\n{answer_text}\n\n"
        f"Sources fournies au moment de la generation :\n\n{sources_desc}"
    )

    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": CITATION_RELEVANCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(completion.choices[0].message.content)
        issues = parsed.get("citations_douteuses", []) if isinstance(parsed, dict) else []
        issues = [i for i in issues if isinstance(i, dict) and i.get("citation")]
        return issues, completion.usage
    except Exception:  # pylint: disable=broad-except
        return [], None


def format_citation_warnings(unverified, relevance_issues):
    """Construit une liste unifiee de messages d'alerte a partir des deux
    garde-fous de citation (check_citation_integrity : reference introuvable ;
    check_citation_relevance : reference reelle mais mal appliquee), pour un
    affichage coherent quel que soit le canal. Retourne une liste vide si
    tout est en ordre."""
    warnings = []
    for numero in unverified or []:
        warnings.append(
            f"La reference '{numero}' citee dans la reponse n'a pas ete retrouvee telle quelle "
            f"parmi les sources disponibles - verifiez qu'elle n'a pas ete inventee."
        )
    for issue in relevance_issues or []:
        msg = (
            f"La source '{issue['citation']}' pourrait ne pas soutenir reellement "
            f"l'affirmation associee : {issue.get('probleme', '')}"
        )
        if issue.get("source_plus_pertinente"):
            msg += f" (une autre source disponible, '{issue['source_plus_pertinente']}', semble plus pertinente)."
        warnings.append(msg)
    return warnings


def embed_query(client, query):
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    return resp.data[0].embedding


def build_user_message(context, query):
    return f"""Contexte documentaire :
{context}

---

Question posee : {query}"""


VERIFICATION_SYSTEM_PROMPT = """Tu verifies, AVANT toute redaction de reponse, si des \
pratiques validees (clarifications de terrain internes, chacune illustrant un cas concret \
anterieur) s'appliquent reellement a une nouvelle question posee sur ReligioSoft ou la \
reglementation des fabriques d'eglise.

Pour chaque pratique proposee, compare ses PREMISSES/conditions de fond decisives (type de \
fabrique, existence ou non d'une convention pluriannuelle avec la commune, module ou version du \
logiciel concerne, exercice budgetaire...) telles qu'elles apparaissent dans son enonce, avec les \
faits decrits dans la question posee. Une pratique n'est "applicable" que si ses premisses \
decisives correspondent aux faits de la question - PAS seulement si le sujet general se \
ressemble (meme type de demarche, meme module du logiciel). En cas de doute reel (la question ne \
precise pas un element decisif), considere la pratique comme applicable plutot que de la rejeter \
a tort.

Reponds UNIQUEMENT avec un objet JSON de la forme :
{"verdicts": [{"code": "<code exact fourni>", "applicable": true ou false, "raison": "<une phrase courte>"}, ...]}
Un verdict par pratique candidate recue, dans le meme ordre, sans en omettre aucune."""


def filter_applicable_practices(client, query, results):
    """Deuxieme passage de verification, dedie : avant la generation, verifie
    que les PREMISSES des pratiques validees retrouvees correspondent
    reellement aux faits de la question, et ecarte celles qui ne
    correspondent pas. Les sources officielles (textes legaux/circulaires,
    manuel utilisateur) ne passent pas par ce filtre : elles s'appliquent de
    maniere generale, elles ne sont pas liees aux faits d'un cas precis
    comme une pratique validee.

    Cout : un appel LLM supplementaire, uniquement s'il y a au moins une
    pratique validee parmi les resultats. Robuste par construction : toute
    erreur (reseau, JSON invalide, code non reconnu...) fait retomber sur les
    resultats non filtres plutot que de bloquer la reponse - un faux negatif
    de la verification ne doit jamais empecher de repondre."""
    practices = [(score, meta) for score, meta in results
                 if meta.get("statut_entree") == "reference_interne" and meta.get("numero")]
    if not practices:
        return results, None

    candidates_desc = "\n\n".join(
        f"- code: {meta['numero']}\n  titre: {meta.get('titre_contexte') or ''}\n"
        f"  contenu: {meta['text_for_embedding'][:1500]}"
        for _, meta in practices
    )
    verification_user_message = (
        f"Question posee : {query}\n\n"
        f"Pratiques candidates a verifier :\n\n{candidates_desc}"
    )

    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": verification_user_message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(completion.choices[0].message.content)
        verdicts = parsed.get("verdicts", []) if isinstance(parsed, dict) else []
        rejected_codes = {
            v["code"] for v in verdicts
            if isinstance(v, dict) and v.get("applicable") is False and v.get("code")
        }
        usage = completion.usage
    except Exception:  # pylint: disable=broad-except
        return results, None

    filtered = [
        (score, meta) for score, meta in results
        if meta.get("statut_entree") != "reference_interne" or meta.get("numero") not in rejected_codes
    ]

    if not filtered:
        # Garde-fou : si la verification rejette 100% des candidats alors
        # qu'il y en avait au depart, c'est plus probablement un exces de
        # prudence de la verification (elle exige une correspondance parfaite
        # au lieu de tolerer les differences mineures) qu'un signal fiable
        # que rien n'est utilisable. Mieux vaut repondre avec les resultats
        # non filtres (le prompt de generation garde de toute facon sa propre
        # consigne de verification des premisses, groupe C) que de perdre
        # totalement la reponse alors que du contenu pertinent existe.
        return results, usage

    return filtered, usage


def answer_question(query, embeddings_path="embeddings.npz", top_k=10, verbose=True,
                     matiere=None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Variable d'environnement OPENAI_API_KEY manquante.")

    client = OpenAI(api_key=api_key)
    retriever = Retriever(embeddings_path)

    query_embedding = embed_query(client, query)
    results = retriever.search(query_embedding, top_k=top_k, exclude_historique=True,
                                matiere=matiere)

    if verbose:
        print(f"[{len(results)} passages retrouves]")
        for score, meta in results:
            print(f"  {score:.2f}  {meta['chunk_id']}")
        print()

    if not results:
        return NO_RESULTS_MESSAGE

    results, verif_usage = filter_applicable_practices(client, query, results)
    if verbose and verif_usage:
        print(f"[verification : {len(results)} passages retenus apres filtre de pertinence]\n")

    if not results:
        return NO_RESULTS_MESSAGE

    context = format_results_for_prompt(results)
    user_message = build_user_message(context, query)

    completion = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,  # faible temperature : priorite a la precision factuelle
    )

    answer = completion.choices[0].message.content
    unverified = check_citation_integrity(results, answer, query)
    relevance_issues, _relevance_usage = check_citation_relevance(client, query, results, answer)
    if verbose:
        warnings = format_citation_warnings(unverified, relevance_issues)
        for w in warnings:
            print(f"[ATTENTION - {w}]\n")

    return answer


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rag_answer.py \"votre question\"")
        sys.exit(1)

    query = sys.argv[1]
    answer = answer_question(query)
    print("=" * 70)
    print(answer)


if __name__ == "__main__":
    main()

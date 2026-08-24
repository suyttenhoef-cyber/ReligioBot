> **Note** : ce document n'est pas la documentation de l'assistant état civil lui-même — c'est un
> brief de démarrage pour un **futur projet séparé** (assistant ReligioSoft), rédigé ici le
> 2026-08-24 et conservé dans ce dossier en attendant la création du dépôt GitHub dédié. Une fois
> ce nouveau dépôt créé, ce fichier est destiné à en devenir le `CLAUDE.md` (copier/coller tel
> quel comme point de départ).

# Contexte projet — Assistant ReligioSoft

## Ce que c'est

Assistant IA (RAG) d'aide sur le logiciel **ReligioSoft** et sur la réglementation comptable/
légale des fabriques d'église en Région wallonne. Deux publics distincts :

- les **utilisateurs de ReligioSoft** (trésoriers de fabriques d'église — souvent des bénévoles,
  pas forcément à l'aise avec l'informatique ni le jargon comptable/juridique) ;
- l'**équipe support/helpdesk Vanden Broele** (`cultes@religiosoft.be`, 02 308 29 06), qui répond
  aux trésoriers et a besoin d'une réponse rapide et sourcée pour le faire efficacement.

C'est le **troisième déploiement** du même socle technique déjà construit et validé sur
`chatbot_cpas` (aide sociale/CPAS) puis sur `chatbot_etat_civil` (état civil des communes) — situés
respectivement dans `c:\dev\chatbot_cpas` et `c:\dev\chatbot_etat_civil` sur ce poste. **Consulter
ces deux projets systématiquement** pour la logique déjà éprouvée (schéma de corpus, chunking,
retrieval, prompt système, garde-fous anti-hallucination) — ne pas la redécouvrir ici.

**Différence majeure avec les deux projets précédents, à ne jamais perdre de vue** : ce projet
reste **volontairement 100% local**, sans aucune infrastructure Azure ni canal Teams. Voir la
section suivante.

## Ce qui est explicitement HORS PÉRIMÈTRE pour ce projet

Ne pas construire, ni même envisager par réflexe de copier depuis les projets précédents :

- Azure AI Search (retrieval cloud) — le retrieval reste sur une base numpy locale
  (`retrieve.py`, à reprendre tel quel depuis `chatbot_etat_civil`), **en permanence**, pas comme
  étape transitoire avant un portage cloud. À l'échelle attendue ici (un corpus réglementaire +
  des manuels logiciel, pas des dizaines de milliers de pages), c'est largement suffisant en
  performance.
- Azure Bot Service, Bot Framework SDK, canal Teams (`bot_teams.py`, `bot_server.py`,
  `bot_config.py`) — aucun de ces fichiers n'a de raison d'exister dans ce projet.
- Azure App Service, déploiement cloud, Application Insights/télémétrie Azure
  (`azure_search_setup.py`, `retrieve_azure_search.py`, `telemetry.py`) — idem, hors périmètre.
- Azure Lighthouse, gestion multi-tenant — sans objet, usage strictement local.

Ce que l'on garde et adapte du socle existant :

- Le schéma de corpus JSON (`documents[]`, `articles[]`, `pratiques_validees[]`,
  `sections_circulaire[]`) et ses conventions — voir `chatbot_etat_civil/README.md`, section
  "Schéma du corpus".
- Le pipeline `chunk_builder.py` → `embed_chunks.py` → `retrieve.py`, réutilisable quasiment tel
  quel.
- La logique de génération et les garde-fous de `rag_answer.py` : `SYSTEM_PROMPT` (à réécrire
  pour ce public et ce domaine, mais en gardant la même structure en groupes de règles),
  `filter_applicable_practices` (vérification de pertinence des pratiques),
  `check_citation_integrity` (citation inventée), `check_citation_relevance` (citation réelle
  mais mal appliquée — ajouté récemment sur `chatbot_etat_civil` suite à un cas réel, à intégrer
  **dès le départ** ici plutôt qu'à ajouter après un incident similaire), et les règles B4/B5 du
  prompt (poser une question de clarification si un élément décisif manque à la question ; dire
  explicitement quand le corpus ne couvre pas le sujet plutôt que deviner).
- L'interface locale : `app.py` (Streamlit) et/ou `chat_loop.py` (terminal) de
  `chatbot_etat_civil`, comme modèles directs.

## Distribution et accès local — décision prise (2026-08-24)

Le code sera hébergé sur un dépôt **GitHub** (même pratique que `chatbot_cpas` et
`chatbot_etat_civil`, tous deux déjà sur GitHub) — pas de packaging en exécutable autonome, pas
de service hébergé. L'accès se fait par clonage du dépôt et exécution locale (`streamlit run
app.py` et/ou `chat_loop.py`), exactement comme les deux projets précédents en usage local/dev.

**Nuance qui reste à clarifier** (le dépôt GitHub règle la distribution du code, pas
l'ergonomie d'accès pour un public non technique) : cloner un dépôt et lancer une commande
Python suppose un minimum d'aisance technique - réaliste pour l'équipe support Vanden Broele,
beaucoup moins pour un trésorier bénévole non technicien. À moins que l'usage prévu pour les
trésoriers passe par un intermédiaire (l'équipe support utilise l'outil pour répondre plus vite,
sans que le trésorier n'installe quoi que ce soit lui-même), il faudra probablement revisiter ce
point avant d'exposer l'outil directement aux utilisateurs finaux du logiciel.

Points pratiques à prévoir pour le dépôt :
- `.gitignore` reprenant celui de `chatbot_etat_civil` (exclusion de `.env`, `venv/`,
  `__pycache__/`, etc. — voir ce fichier pour la liste complète et le raisonnement).
- `README.md` avec les instructions de clonage + lancement local (`pip install -r
  requirements.txt`, `streamlit run app.py`), sur le modèle du README des deux projets
  précédents.
- Décider si le dépôt est privé ou public dès sa création — contenu réglementaire/logiciel d'un
  tiers commercial (ReligioSoft), probablement à garder privé au moins dans un premier temps.

## Contenu à couvrir — deux volets distincts (probablement deux matières du corpus)

### Volet 1 — Usage du logiciel ReligioSoft

Manuels utilisateur du logiciel — **pas encore obtenus à ce stade**, à demander en premier lieu.
Couvre les questions du type "comment encoder une facture", "comment injecter un fichier CODA",
"comment gérer les droits de lecture du conseil de fabrique", etc. Fonctionnalités connues du
logiciel (voir description commerciale ci-dessous) à couvrir a minima : budget/modification
budgétaire/compte annuel, imputations, résultat reporté/présumé, alimentation du module bancaire
en ligne, injection de fichiers CODA, réception de factures électroniques (Mercurius/Peppol),
partage de documents avec le conseil de fabrique et la tutelle, gestion des droits de lecture.

### Volet 2 — Réglementation comptable et légale des fabriques d'église

Textes légaux de base fournis par l'utilisateur (2026-08-24) — **texte intégral à obtenir**
(Moniteur belge / Wallex), ne pas se fier à un résumé pour l'extraction :

1. Décret impérial du 30 décembre 1809 concernant les fabriques d'église (toujours en vigueur en
   Région wallonne, fondateur du régime des fabriques).
2. Loi du 4 mars 1870 sur le temporel des cultes (procédures de tutelle, modifiée par le décret
   du 13 mars 2014).
3. Code de la Démocratie Locale et de la Décentralisation (CDLD), extraits : Partie Ire, Livre
   III, Titre II, Ch. Ier (art. L1321-1 à L1321-2) ; Partie III, Livre Ier, Titre Ier, Ch. Ier à
   VI/I (art. L3111-1 à L3116-1/1) et Titre VI (art. L3161-1 à L3162-3) — c'est ici que l'essentiel
   des dispositions de tutelle a été transféré depuis la loi de 1870 par le décret du 13 mars
   2014.
4. Circulaire du 18 juillet 2014 (convention pluriannuelle communes/provinces - fabriques
   d'église) — outils utilisables par toute fabrique, pas seulement les fabriques pilotes.
5. Circulaire du 12 décembre 2014 relative à la tutelle sur les actes et aux pièces
   justificatives (modifiée en 2019 pour les annexes) — texte de référence pratique pour le
   trésorier, résume les 3 textes précédents.
6. Décret du 18 mai 2017 relatif à la reconnaissance et aux obligations des établissements
   cultuels (fusion, désaffectation, obligations administratives).
7. Arrêté du Gouvernement wallon du 25 janvier 2018 (exécution du décret de 2017, modalités et
   documents modèles).
8. Arrêté du Gouvernement wallon du 25 février 2021 (notification électronique des décisions de
   tutelle, exécution de l'art. L3115-1 CDLD).
9. Circulaire relative aux pièces justificatives du 21 janvier 2019.
10. Circulaire du 20 juin 2024 relative aux opérations patrimoniales des pouvoirs locaux.
11. Circulaire du 30 mai 2013 relative à l'octroi des subventions par les pouvoirs locaux.
12. Circulaires budgétaires communales annuelles (2015 et suivantes) — renouvelées chaque année,
    contiennent aussi des directives pour le suivi des fabriques d'église : vérifier qu'on
    dispose bien de la version la plus récente au moment de l'extraction, et prévoir une veille.

**Point de vigilance propriété intellectuelle** : l'utilisateur mentionne un "Codex" annoté par
Jean-François Husson (ouvrage commercial tiers compilant et commentant ces textes) comme
référence utile. **Ne pas reproduire son contenu texte dans le corpus** sans avoir vérifié les
droits d'auteur/la licence au préalable — il peut servir d'outil de travail pour l'équipe humaine,
mais ne pas l'ingérer verbatim comme source du chatbot sans autorisation explicite. À confirmer
avec l'utilisateur avant toute extraction depuis ce document précis.

### Sources futures possibles (à évoquer plus tard, pas au démarrage)

- FAQ/tickets réels du helpdesk Vanden Broele (`cultes@religiosoft.be`), une fois anonymisés —
  même logique que l'export FAQ Connect de `chatbot_etat_civil`, pour construire des
  `pratiques_validees` à partir de cas réels déjà tranchés par un expert.
- Modules de formation ReligioSoft existants, le cas échéant — même méthodologie que
  l'ingestion e-learning de `chatbot_etat_civil` (filtrer le bruit pédagogique - QCM, feedback -
  et extraire notions/procédures + mises en situation).

## Schéma du corpus (à reprendre tel quel)

Voir `chatbot_etat_civil/README.md`, section "Schéma du corpus", pour le détail complet et les
conventions (`entry_id`, pas d'accents français dans `texte`/`titre_contexte`, `categorie`/
`sous_categorie`, `articles_lies`, format `code` des pratiques). Matières suggérées pour ce
projet (noms à valider/ajuster au démarrage) :

- `reglementation_fabriques` — le volet légal/comptable (décrets, lois, CDLD, circulaires).
- `usage_logiciel` — le volet manuel/fonctionnalités ReligioSoft.

## Prompt système — points d'adaptation par rapport à `chatbot_etat_civil`

Réutiliser la structure en groupes de règles (A. citation des sources, B. face à l'incertitude,
C. ne pas transposer aveuglément une pratique à un cas différent, D. structure/ton, E. format
technique) en l'adaptant :

- Public double (trésorier bénévole non technique + agent support professionnel) : le ton doit
  rester accessible par défaut (comme pour `chatbot_etat_civil`), sans jargon comptable non
  expliqué.
- Le disclaimer de fin de réponse doit rappeler que l'outil ne remplace ni une vérification
  comptable par un professionnel, ni le helpdesk officiel Vanden Broele en cas de doute.
- Attention particulière à la règle "ne jamais transposer aveuglément une pratique" (groupe C) :
  les questions comptables dépendent souvent de faits précis (type de fabrique, montant, exercice
  budgétaire concerné, présence ou non d'une convention pluriannuelle) - le même risque de
  confusion qu'on a rencontré sur `chatbot_etat_civil` (une pratique valable pour un cas ne
  s'applique pas telle quelle a un cas voisin mais different) est à anticiper ici aussi.

## Prochaines étapes concrètes

1. Obtenir les manuels utilisateur ReligioSoft (pas encore en main à ce stade).
2. Obtenir le texte intégral des 12 sources légales listées ci-dessus (Moniteur belge / Wallex),
   pas un résumé.
3. Clarifier avec l'utilisateur le point d'accès local (voir section dédiée ci-dessus) avant de
   coder l'interface finale.
4. Construire le corpus matière par matière, **un document source à la fois** — même discipline
   que pour l'extraction de l'Ancien Code civil et l'ingestion des modules e-learning sur
   `chatbot_etat_civil` : jamais un gros lot d'extraction en parallèle (risque de mixup de
   fichier déjà rencontré et documenté sur ce projet).
5. Rebuild + test local (`chunk_builder.py` → `embed_chunks.py` → interface locale) après chaque
   ajout de contenu, avant de passer au document suivant.

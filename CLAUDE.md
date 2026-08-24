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
reste **volontairement 100% local**, sans aucune infrastructure Azure ni canal Teams.

Brief de démarrage initial : `Doc/brief_demarrage_religiosoft.md` (rédigé le 2026-08-24, avant la
création de la structure du dépôt — conservé comme trace historique, ce fichier `CLAUDE.md` en est
la version vivante).

## Ce qui est explicitement HORS PÉRIMÈTRE pour ce projet

Ne pas construire, ni même envisager par réflexe de copier depuis les projets précédents :

- Azure AI Search (retrieval cloud) — le retrieval reste sur une base numpy locale
  (`retrieve.py`, repris tel quel depuis `chatbot_etat_civil`), **en permanence**, pas comme
  étape transitoire avant un portage cloud. À l'échelle attendue ici (un corpus réglementaire +
  des manuels logiciel, pas des dizaines de milliers de pages), c'est largement suffisant en
  performance.
- Azure Bot Service, Bot Framework SDK, canal Teams (`bot_teams.py`, `bot_server.py`,
  `bot_config.py`) — aucun de ces fichiers n'a de raison d'exister dans ce projet.
- Azure App Service, déploiement cloud, Application Insights/télémétrie Azure
  (`azure_search_setup.py`, `retrieve_azure_search.py`, `telemetry.py`) — idem, hors périmètre.
- Azure Lighthouse, gestion multi-tenant — sans objet, usage strictement local.

## État actuel du projet — mis à jour 2026-08-24

- ✅ **Structure du dépôt créée** (voir `README.md` pour le détail) : pipeline copié tel quel
  depuis `chatbot_etat_civil` (`chunk_builder.py`, `embed_chunks.py`, `retrieve.py`),
  `rag_answer.py`/`app.py`/`chat_loop.py` adaptés (SYSTEM_PROMPT réécrit pour le double public
  ReligioSoft/fabriques, disclaimer renvoyant vers le helpdesk Vanden Broele, garde-fous
  `check_citation_integrity`/`check_citation_relevance`/`filter_applicable_practices` repris
  intégralement dès le départ — pas ajoutés après un incident comme ce fut le cas sur
  `chatbot_etat_civil`).
- ✅ **Dépôt git local initialisé** (pas encore poussé sur GitHub — voir "Prochaines étapes").
- ✅ **Manuels utilisateur ReligioSoft obtenus** : 29 PDF dans
  `Ressources_brutes/manuels_religiosoft/` (budget, imputations, mandats de paiement, module
  bancaire/CODA, factures électroniques Mercurius/Peppol, droits de lecture, modules
  commune/évêché/groupement, etc.). **Pas encore extraits vers le schéma du corpus**
  (`corpus_par_matiere/corpus_usage_logiciel.json` est un squelette avec un seul document
  déclaré).
- ✅ **Point de départ pour l'extraction du volet logiciel** : un prototype antérieur
  (dossier `Old/` à la racine, non versionné) avait déjà extrait la quasi-totalité de ces
  manuels vers une structure JSON intermédiaire riche (résumé, mots-clés, questions
  fréquentes, étapes de processus par section) — copiée dans
  `Ressources_brutes/extraction_manuels_ancienne/` (fichiers
  `manuel_structure_llm_bis_*.json`, un par manuel, plus `chatbot_knowledge_base.json`,
  consolidation de l'ensemble). **Ce n'est pas le schéma cible** (`entry_id`/`texte`/
  `titre_contexte`/`categorie` attendu par `chunk_builder.py`) mais une base de travail
  exploitable pour accélérer la conversion, à faire matière par matière (voir "Prochaines
  étapes"). Vérifier la qualité de cette extraction avant de s'y fier telle quelle (elle date
  de mai 2025, méthodologie non documentée dans ce projet).
- ⏳ **Textes légaux non obtenus** : `corpus_par_matiere/corpus_reglementation_fabriques.json`
  ne contient que les 12 `documents` déclarés (métadonnées + notes), sans aucun `article`
  extrait — le texte intégral reste à obtenir (Moniteur belge / Wallex).
- ⏳ **Point d'accès pour le trésorier bénévole non technique** non tranché (voir section
  dédiée ci-dessous).

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

Points pratiques restants pour le dépôt :
- Décider si le dépôt GitHub est privé ou public dès sa création — contenu réglementaire/
  logiciel d'un tiers commercial (ReligioSoft), probablement à garder privé au moins dans un
  premier temps. **Pas encore créé sur GitHub à ce stade** (dépôt git local uniquement).

## Contenu à couvrir — deux volets distincts (deux matières du corpus)

### Volet 1 — Usage du logiciel ReligioSoft (`usage_logiciel`)

Manuels utilisateur obtenus (voir "État actuel" ci-dessus). Couvre les questions du type
"comment encoder une facture", "comment injecter un fichier CODA", "comment gérer les droits de
lecture du conseil de fabrique", etc. Fonctionnalités connues du logiciel à couvrir a minima :
budget/modification budgétaire/compte annuel, imputations, résultat reporté/présumé,
alimentation du module bancaire en ligne, injection de fichiers CODA, réception de factures
électroniques (Mercurius/Peppol), partage de documents avec le conseil de fabrique et la
tutelle, gestion des droits de lecture.

### Volet 2 — Réglementation comptable et légale des fabriques d'église (`reglementation_fabriques`)

Textes légaux de base fournis par l'utilisateur (2026-08-24) — **texte intégral à obtenir**
(Moniteur belge / Wallex), ne pas se fier à un résumé pour l'extraction. Les 12 sources et leurs
notes sont déjà déclarées comme `documents` dans
`corpus_par_matiere/corpus_reglementation_fabriques.json` :

1. Décret impérial du 30 décembre 1809 concernant les fabriques d'église.
2. Loi du 4 mars 1870 sur le temporel des cultes (modifiée par le décret du 13 mars 2014).
3. Code de la Démocratie Locale et de la Décentralisation (CDLD), extraits : Partie Ire, Livre
   III, Titre II, Ch. Ier (art. L1321-1 à L1321-2) ; Partie III, Livre Ier, Titre Ier, Ch. Ier à
   VI/I (art. L3111-1 à L3116-1/1) et Titre VI (art. L3161-1 à L3162-3).
4. Circulaire du 18 juillet 2014 (convention pluriannuelle communes/provinces - fabriques
   d'église).
5. Circulaire du 12 décembre 2014 relative à la tutelle sur les actes et aux pièces
   justificatives (modifiée en 2019 pour les annexes).
6. Décret du 18 mai 2017 relatif à la reconnaissance et aux obligations des établissements
   cultuels.
7. Arrêté du Gouvernement wallon du 25 janvier 2018.
8. Arrêté du Gouvernement wallon du 25 février 2021 (notification électronique des décisions de
   tutelle).
9. Circulaire relative aux pièces justificatives du 21 janvier 2019.
10. Circulaire du 20 juin 2024 relative aux opérations patrimoniales des pouvoirs locaux.
11. Circulaire du 30 mai 2013 relative à l'octroi des subventions par les pouvoirs locaux.
12. Circulaires budgétaires communales annuelles (2015 et suivantes) — vérifier qu'on dispose de
    la version la plus récente au moment de l'extraction, et prévoir une veille.

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

## Schéma du corpus

Voir `README.md`, section "Schéma du corpus", pour le détail complet. Résumé : chaque fichier
`corpus_par_matiere/corpus_<matiere>.json` porte `_matiere`, `documents[]`, `articles[]`,
`sections_circulaire[]`, `pratiques_validees[]`. Codes de pratiques validées :
`PV-RF-NNN` (`reglementation_fabriques`) / `PV-UL-NNN` (`usage_logiciel`), cités dans les
réponses avec le préfixe `VDB-`.

## Prompt système — points d'adaptation par rapport à `chatbot_etat_civil`

Déjà appliqué dans `rag_answer.py` (voir `SYSTEM_PROMPT`) : structure en groupes de règles
(A. citation des sources, B. face à l'incertitude, C. ne pas transposer aveuglément une pratique
à un cas différent, D. structure/ton, E. format technique), adaptée :

- Public double (trésorier bénévole non technique + agent support professionnel) : ton
  accessible par défaut, sans jargon comptable non expliqué.
- Disclaimer de fin de réponse rappelant que l'outil ne remplace ni une vérification comptable
  par un professionnel, ni le helpdesk officiel Vanden Broele en cas de doute.
- Attention particulière à la règle "ne jamais transposer aveuglément une pratique" (groupe C) :
  les questions comptables dépendent souvent de faits précis (type de fabrique, montant, exercice
  budgétaire concerné, présence ou non d'une convention pluriannuelle) - le même risque de
  confusion qu'on a rencontré sur `chatbot_etat_civil` (une pratique valable pour un cas ne
  s'applique pas telle quelle à un cas voisin mais différent) est à anticiper ici aussi.
- Distinction supplémentaire propre à ce projet (pas dans `chatbot_etat_civil`) : le contexte
  peut mélanger deux natures de sources très différentes (texte légal/circulaire **vs** manuel
  utilisateur du logiciel) — le prompt cite les deux niveaux séparément quand ils sont tous deux
  pertinents pour la même question (ex. une règle comptable qui contraint une procédure
  d'encodage dans le logiciel).

## Prochaines étapes concrètes

1. Obtenir le texte intégral des 12 sources légales listées ci-dessus (Moniteur belge / Wallex),
   pas un résumé — rien n'est encore extrait dans `corpus_reglementation_fabriques.json`.
2. Convertir les manuels ReligioSoft vers le schéma du corpus (`usage_logiciel`), **un document
   source à la fois** — même discipline que pour l'extraction de l'Ancien Code civil et
   l'ingestion des modules e-learning sur `chatbot_etat_civil` : jamais un gros lot d'extraction
   en parallèle (risque de mixup de fichier déjà rencontré et documenté sur ce projet frère).
   Partir de `Ressources_brutes/extraction_manuels_ancienne/` comme base de travail (à valider,
   pas à recopier aveuglément) plutôt que de repartir des PDF bruts pour chaque manuel.
3. Construire le corpus légal matière par matière, un texte source à la fois, une fois le texte
   intégral obtenu (étape 1).
4. Rebuild + test local (`chunk_builder.py` → `embed_chunks.py` → interface locale) après chaque
   ajout de contenu, avant de passer au document suivant.
5. Clarifier avec l'utilisateur le point d'accès local pour le trésorier bénévole (voir section
   dédiée ci-dessus) avant d'exposer l'outil au-delà de l'équipe support.
6. Décider privé/public et créer le dépôt GitHub distant, une fois un premier contenu réel en
   place (le dépôt git local existe déjà).

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
- ✅ **Dépôt distant** : https://github.com/suyttenhoef-cyber/ReligioBot (poussé le 2026-08-24).
- ✅ **Volet `usage_logiciel` construit** pour les 25 vrais manuels ReligioSoft (voir plus bas
  pour les 4 fichiers a part) : 25 `documents`, 58 `articles` dans
  `corpus_par_matiere/corpus_usage_logiciel.json`. Conversion faite par script deterministe
  (`scripts_ponctuels/convert_manuels_usage_logiciel.py`, remapping de champs, PAS une
  nouvelle extraction LLM) a partir de l'extraction JSON deja realisee par le prototype
  anterieur (`Ressources_brutes/extraction_manuels_ancienne/manuel_structure_llm_bis_*.json`,
  qualite verifiee bonne sur echantillon). Ponctuation typographique normalisee en ASCII
  (apostrophes/guillemets courbes, puces et fleches de polices symboliques Wingdings mal
  mappees en Unicode a l'extraction PDF) - voir le script pour le detail des correspondances.
  `chunk_builder.py` corrige au passage (plantait sur un corpus vide, cf commit dedie) et
  valide sur ce corpus : 58 chunks generes, tailles 623-25141 caracteres (le haut de la
  fourchette est proche de la limite de tokens du modele d'embedding - a surveiller au premier
  vrai `embed_chunks.py`).
  - 2 sections sur 60 ont un `contenu_texte` vide dans l'extraction source (manuel 07 "Compte
    annuel", chapitre 2 "Cloturer l'exercice" ; manuel 26 "Releves de creance", chapitre 1
    "Introduction") - trou d'extraction du prototype anterieur, pas re-extrait depuis le PDF a
    ce stade, aucun article correspondant dans le corpus.
  - `embed_chunks.py` PAS encore execute (necessite OPENAI_API_KEY + acces reseau,
    indisponibles depuis l'environnement d'edition) - a lancer par l'utilisateur en local avant
    de tester l'interface sur ce contenu.
- ✅ **4 ouvrages complementaires identifies et autorises** (2026-08-24) : le dossier
  `Religio_manuels` livre au depart contenait aussi 4 ouvrages commerciaux publies (pas des
  manuels logiciel), extraits par le prototype anterieur sous les noms `39_001V_CPDF`,
  `39_004V_CPDF`, `39_005V_CPDF`, `41_039V_CPDF` :
  - *Les fabriques d'eglise en Wallonie - Histoire, evolutions et perspectives d'avenir* (378 p.)
  - *Le guide du tresorier - La gestion comptable des fabriques d'eglise*, ed. 2025 (270 p.)
  - ***Les fabriques d'eglise - Le codex 2025, edition annotee***, Jean-Francois Husson (308 p.)
    - c'est LE "Codex" deja signale plus haut comme point de vigilance IP : il etait deja dans
      le dossier fourni.
  - *Guide pratique pour la tutelle sur les fabriques d'eglise*, Frederic Bourguignon (248 p.)
  Droits confirmes par l'utilisateur (2026-08-24, Vanden Broele editeur/detenteur) - utilisables.
  **Pas encore integres au corpus** : l'extraction anterieure les a traites en UN seul bloc de
  texte par livre (300K-950K caracteres), totalement inutilisable tel quel pour l'embedding
  (largement au-dessus de la limite de tokens) - il faudra un vrai decoupage par
  chapitre/article avant de les chunker, probablement vers `reglementation_fabriques` (le
  Codex en particulier compile deja les textes legaux du volet 2). Voir "Prochaines etapes".
- ⏳ **Textes légaux (Moniteur belge/Wallex) non obtenus séparément** : `corpus_reglementation_
  fabriques.json` ne contient que les 12 `documents` déclarés (métadonnées + notes), sans aucun
  `article` extrait. Le Codex Husson (ci-dessus) pourrait combler une bonne partie de ce besoin
  une fois découpé - à évaluer avant de partir à la recherche des textes bruts un par un.
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

**Point de vigilance propriété intellectuelle — RÉSOLU (2026-08-24)** : le "Codex" annoté par
Jean-François Husson mentionné ici était en fait déjà présent dans `Religio_manuels/` (identifié
le 2026-08-24 sous le nom `39_005V_CPDF`, avec 3 autres ouvrages du même type — voir "État actuel
du projet"). Droits confirmés par l'utilisateur (Vanden Broele éditeur/détenteur) : ces 4 ouvrages
sont utilisables dans le corpus. Reste à faire : découpage par chapitre/article avant ingestion
(l'extraction "un seul bloc" existante est inutilisable pour l'embedding).

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

1. **Lancer le pipeline d'embeddings en local** (nécessite `OPENAI_API_KEY`, impossible depuis
   l'environnement d'édition) sur le corpus `usage_logiciel` actuel (58 articles) et tester
   l'interface (`streamlit run app.py`) avant d'aller plus loin, pour valider la qualité des
   réponses sur du contenu réel avant de continuer à en ajouter.
2. Décider comment traiter les 4 ouvrages (Codex Husson en particulier) : découper chaque livre
   par chapitre/article réel (l'extraction "un seul bloc" existante est inutilisable pour
   l'embedding) — évaluer d'abord si le Codex suffit à couvrir tout ou partie des 12 sources
   légales du volet 2 avant de repartir sur le Moniteur belge/Wallex texte par texte.
3. Pour ce qui manque après l'étape 2, obtenir/extraire le texte intégral des sources légales
   restantes (Moniteur belge / Wallex), un texte à la fois — même discipline que pour
   l'extraction de l'Ancien Code civil sur `chatbot_etat_civil` : jamais un gros lot en
   parallèle (risque de mixup déjà documenté sur ce projet frère).
4. Combler si possible les 2 sections à `contenu_texte` vide identifiées dans le volet logiciel
   (manuel 07 chapitre 2, manuel 26 chapitre 1) en ré-extrayant directement depuis le PDF
   source.
5. Rebuild + test local (`chunk_builder.py` → `embed_chunks.py` → interface locale) après chaque
   ajout de contenu, avant de passer au document suivant.
6. Clarifier avec l'utilisateur le point d'accès local pour le trésorier bénévole (voir section
   dédiée ci-dessus) avant d'exposer l'outil au-delà de l'équipe support.
7. Décider privé/public du dépôt GitHub distant (https://github.com/suyttenhoef-cyber/ReligioBot,
   visibilité actuelle non vérifiée par l'assistant).

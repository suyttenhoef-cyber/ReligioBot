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
- ✅ **233 articles extraits du Codex Husson vers `reglementation_fabriques`** (2026-08-24,
  `scripts_ponctuels/extract_codex_articles.py`) : l'utilisateur a depose 2 des 4 ouvrages
  (`39_004V_CPDF.pdf` guide du tresorier, `39_005V_CPDF.pdf` Codex Husson) dans
  `Ressources_brutes/bases_legales/`. La table des matieres du Codex correspond quasi
  exactement aux 12 sources legales listees plus bas, avec des numeros de page exacts - ca a
  permis un decoupage par plage de pages + regex "Art. N." (pas une extraction LLM) pour les 6
  textes structures en articles numerotes :
  - decret imperial 1809 (112 art.), loi du 4 mars 1870 (36 art.), CDLD extraits (27 art.,
    L1321-1 a L3162-3), decret du 18 mai 2017 (41 art.), AGW 25/01/2018 (11 art., annexes-
    formulaires exclues - numerotation interne parasite), AGW 25/02/2021 (6 art.).
  - Chaque article distingue le texte legal verbatim (`texte`) du commentaire de Jean-Francois
    Husson qui suit souvent ("Annotation :" dans le livre), range a part dans `exemples` avec le
    prefixe explicite "Annotation Husson (doctrine, pas le texte legal) :" - jamais mélangé au
    texte officiel, coherent avec la regle A3 du SYSTEM_PROMPT.
  - Pieges rencontres et corriges pendant l'extraction (cf. le script pour le detail) : le Codex
    encadre de crochets `[...]` le texte insere/modifie par un decret ulterieur, ce qui cassait
    la detection en debut de ligne pour une partie du CDLD (tout le Titre VI, L3161-x/L3162-x,
    manquant avant correction) ; une annotation citait in extenso l'article d'un AUTRE decret
    (2022), cree un faux article "22" dans le CDLD avant garde-fou (numeros CDLD doivent
    commencer par "L") ; le decret de 2017 numerote son premier article "Article 1er" (en toutes
    lettres) contrairement aux suivants ("Art. N").
  - **Pas encore fait** : le guide du tresorier (`39_004V_CPDF.pdf`, deja depose) n'est pas
    encore traite - structure a analyser (probablement plus proche de `usage_logiciel`/pratiques
    comptables que d'articles de loi). Les circulaires du Codex (18/07/2014, 12/12/2014,
    20/06/2024, 30/05/2013, circulaires budgetaires 2015-2024) ne sont PAS structurees en
    "Art. N." mais en sections titrees - extraction separee a construire (voir "Prochaines
    etapes"), tout comme l'essai introductif de Husson et les "Questions parlementaires" (bonus
    hors des 12 sources initiales).
  - Toujours manquants dans le Codex : circulaire du 21 janvier 2019 (pieces justificatives) -
    semble absente de cette edition du Codex (peut-etre absorbee/mentionnee dans le commentaire
    de la circulaire de 2014 sans chapitre dedie) - a verifier avant de considerer ce point
    couvert.
- ✅ **112 sections extraites du "Guide du tresorier" 2025** (2026-08-24,
  `scripts_ponctuels/extract_guide_tresorier.py`, document `guide_tresorier_2025`) : contrairement
  au Codex, ce livre n'est pas structure en "Art. N." mais en chapitres/sous-sections numerotees
  (ex. "4.1.5. Question technique : le calcul du supplement communal") - script de decoupage
  distinct, par plage de pages (chapitres 1 a 5, pages 11-230) puis par numerotation X.Y.Z.
  Stocke dans `sections_circulaire[]` (cle reutilisee, structurellement generique malgre son nom)
  avec `document.type = "guide_pratique"`. Ce n'est PAS un texte officiel mais un guide pratique
  commercial (doctrine Vanden Broele) : regle ajoutee au SYSTEM_PROMPT (groupe A3) pour ne jamais
  le presenter comme la loi elle-meme, meme quand il la cite et l'explique.
  - Piege specifique a ce PDF (absent du Codex) : un artefact d'extraction inserait un espace
    parasite apres certaines premieres lettres capitales de mot ("T out" pour "Tout", "L
    'exercice" pour "L'exercice") - corrige par regex apres verification qu'il ne fallait PAS
    fusionner "A" (legitimement le mot "a"/"à" une fois l'accent retire, ex. "A defaut" = deux
    mots reels) - voir le script pour le detail du raisonnement.
  - Annexes (pages 231-264 : tableau des pieces justificatives, calendrier du tresorier,
    adresses utiles, bibliographie) et index NON extraits a ce stade - a evaluer separement.
- ✅ **94 sections extraites des 5 circulaires du Codex** (2026-08-24,
  `scripts_ponctuels/extract_codex_circulaires.py`) : circulaire du 18/07/2014 (24 sections),
  12/12/2014 (15), 20/06/2024 (39), 30/05/2013 (15), circulaires budgetaires communales
  2015-2024 (1, texte court deja centre sur les fabriques). Structure heterogene d'une
  circulaire a l'autre (voir les commentaires en tete de chaque fonction du script) - traitees
  une a la fois, pas par un regex unique suppose universel :
  - 18/07/2014 : en-tetes nommes ("Preambule", "Definitions") + "Section N." + numerotation X.Y.
  - 12/12/2014 : en-tetes nommes + "N. Titre" + "A./B. Titre" + "a./b. Titre", ATTENTION chaque
    paragraphe y est numerote par l'editeur pour l'index ("9 Deux autorites...") - distingue des
    vrais titres par l'absence de point apres le numero. Seules les pages 157-188 (Dispositions
    generales a Entree en vigueur) sont extraites : la suite (Adresses utiles, Liste des pieces
    justificatives, p.189-219) est un tableau (Article/Acte/Pieces/Adresse/Annotation)
    totalement mis a plat par l'extraction PDF lineaire, non exploitable tel quel.
  - 20/06/2024 : "PARTIE N :" + "N. Titre" + X.Y.Z, la plus reguliere des 5.
  - 30/05/2013 : "Premiere/Deuxieme partie :" + X.Y.Z directement (pas de "Section N."
    intermediaire). La "Troisieme partie" (subventions CPAS, sans rapport avec les fabriques)
    n'est pas reprise dans cet extrait du Codex.
  - Circulaires budgetaires : texte court (3 pages), deja centre sur un seul sujet
    ("IV.3.6. Fabriques d'eglise") - une seule entree, pas de sur-decoupage.
  - Piege transversal corrige : l'heuristique de titre coupe sur 2 lignes (liste de mots-cles)
    remplacee par un signal plus robuste (continuation = ligne suivante commencant en
    minuscule), et une collision d'entry_id corrigee (un meme sous-titre peut apparaitre sous
    2 parents differents, ex. "A. Tutelle generale d'annulation" sous "1." et sous "2." dans la
    12/12/2014).
  - L'essai introductif de Husson (Codex p.11-31) et les "Questions parlementaires" (p.283-294)
    restent non extraits (hors des 12 sources legales initiales, a decider si utile).
- ✅ **Premier cas reel teste, garde-fous renforces** (2026-08-24) : l'utilisateur a soumis un
  vrai ticket helpdesk colle tel quel ("comment supprimer la date de validation d'un budget apres
  avoir supprime une MB"), sujet que le corpus `usage_logiciel` ne couvre pas precisement.
  `check_citation_relevance` a correctement signale la citation utilisee (un chapitre sur les
  imperfections du compte annuel, sans rapport), MAIS le modele avait quand meme invente une
  suite d'etapes plausibles avant ce garde-fou a posteriori, plutot que de dire d'emblee que le
  corpus ne couvre pas ce cas precis (regle B4 du prompt, pas assez explicite pour ce type de
  question "action precise dans le logiciel"). Deuxieme probleme distinct : le modele avait redige
  sa reponse comme s'il repondait lui-meme au tresorier par email, avec formule de politesse et
  signature placeholder "[Votre Nom]" - artefact du format du ticket colle en entree.
  Corrige dans `rag_answer.py` (`SYSTEM_PROMPT`) : nouvelle regle B5 (une action precise dans le
  logiciel exige un passage qui la decrit EXPLICITEMENT, pas seulement le meme ecran/sujet
  general - sinon dire explicitement "non documente" plutot qu'extrapoler) et nouvelle regle E2
  (ne jamais imiter le format email/ticket de la question, meme collee telle quelle - toujours
  repondre en registre neutre, jamais de signature). Choix utilisateur explicite : accepter plus
  de "je ne sais pas" en echange de moins d'inventions, vu que le corpus est encore incomplet.
  A revalider sur ce meme cas une fois `embeddings.npz` regenere avec ces changements de prompt
  (le prompt n'affecte que la generation, pas besoin de re-embedder le corpus).
- ✅ **Deuxieme cas reel teste** (2026-08-24) : format email corrige (regle E2 efficace, plus de
  "Bonjour"/signature), mais meme probleme de fond sur un CAS COMPTABLE compose de plusieurs
  faits precis (correction + remboursement + doublon du a un virement interne) - le modele a
  quand meme conclu "la solution proposee peut etre correcte" alors que 3 des 4 citations ont ete
  jugees non pertinentes par `check_citation_relevance`. La regle B5 (ajoutee pour le cas
  precedent) ne visait que les actions logicielles precises, pas les cas comptables composes -
  **generalisee** pour couvrir les deux. Egalement corrige un faux positif de
  `check_citation_integrity` : un code d'article budgetaire comptable ("D62A") propose par
  l'utilisateur LUI-MEME dans sa question etait signale comme "reference non retrouvee/inventee"
  - le mot "article" designe ici un poste budgetaire comptable, pas un article legal, et le
  garde-fou (concu a l'origine pour `chatbot_etat_civil`, ou "article" ne designe que du texte de
  loi) ne faisait pas la difference entre un code invente par le modele et un code simplement
  repris de la question. `check_citation_integrity` prend maintenant aussi `query` en parametre
  et exclut tout numero deja present dans la question. Point de vigilance a garder en tete pour
  la suite : ce corpus a une ambiguite structurelle sur le mot "article" (legal vs comptable) que
  `chatbot_etat_civil` n'avait pas.
- ✅ **Troisieme cas reel teste : chunks trop gros, echec de retrieval** (2026-08-25) - question
  sur le statut "ferme" d'une dette dans ReligioSoft. Le passage exact existait bel et bien dans
  le manuel de l'encodage des ecritures ("le logiciel fermera la dette/creance automatiquement
  des que celle-ci sera ajoutee au journal financier"), mais n'a PAS ete retrouve : il etait noye
  dans un chunk de 18000+ caracteres (tout le chapitre 3 du manuel, extrait comme un seul bloc
  par `convert_manuels_usage_logiciel.py`), qui dilue le signal d'embedding.
  **`convert_manuels_usage_logiciel.py` remplace par `rechunk_manuels_usage_logiciel.py`**
  (SUPERSEDE, ne plus executer) : nouvelle extraction directe depuis les 25 PDF sources (plus
  l'ancienne extraction JSON du prototype), avec un vrai decoupage par sous-section. 58 -> 167
  articles, chunk le plus gros : 25141 -> 10679 caracteres, moyenne 1931 caracteres.
  - 5 conventions de titres differentes coexistent selon le manuel (parfois plusieurs dans le
    meme document) : "Chapitre N." + "X.Y(.Z)" (la plus frequente) ; chiffres romains "I./II."
    (manuels courts sans "Chapitre") ; etapes ordinales "1re etape :"/"2e etape :" (manuels
    "pas a pas" comme le compte annuel) ; lettres majuscules "A. Titre"/"B. Titre" (les annexes
    du compte annuel). Un manuel sans aucun de ces marqueurs reste un chunk unique (3 manuels
    concernes : 11, 18, 23 - deja de taille raisonnable, pas problematique).
  - Piege corrige : `re.IGNORECASE` sur la regex "Chapitre" faisait prendre une reference en
    milieu de phrase ("... le chapitre 3 explique...", minuscule car pas en debut de phrase)
    pour un vrai titre - retire, "Chapitre" doit toujours avoir un C majuscule dans ces manuels.
  - Piege corrige : le filtre anti-bruit d'en-tete/pied de page (repete sur presque chaque page)
    ne doit reperer que "Vanden Broele" seul, PAS la simple presence d'une URL religio(soft).be -
    un vrai titre ("III. www.religiosoft.be - connexion directe !") la mentionne aussi.
  - `embeddings.npz` a regenerer une derniere fois cote utilisateur (606 chunks au total avec
    `reglementation_fabriques`) pour revalider le cas du "statut ferme" sur ce nouveau decoupage.
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

1. **Régénérer les embeddings en local** (`chunk_builder.py` → `embed_chunks.py`, nécessite
   `OPENAI_API_KEY`) : le corpus `reglementation_fabriques` est maintenant complet pour les 5
   circulaires + le Codex + le guide du trésorier (497 chunks au total avec `usage_logiciel`) —
   tester l'interface sur ce contenu avant de continuer à en ajouter.
2. Traiter la table "Liste des pièces justificatives requises" de la circulaire du 12/12/2014
   (pages 189-219 du Codex) — nécessite une vraie extraction de tableau (pypdf aplatit les
   colonnes), pas juste un découpage par titres comme le reste du texte.
3. Décider si l'essai introductif de Husson et les "Questions parlementaires" du Codex (pages
   11-31 et 283-294) valent la peine d'être intégrés (contexte/doctrine utile mais hors des 12
   sources légales listées initialement).
4. Décider si les annexes du guide du trésorier (pages 231-264 : tableau des pièces
   justificatives, calendrier du trésorier, adresses utiles) valent la peine d'être extraites en
   plus des 5 chapitres déjà faits.
5. Vérifier si la circulaire du 21 janvier 2019 (pièces justificatives) est vraiment absente du
   Codex ou seulement fondue dans le commentaire de la circulaire de 2014 ; sinon, l'obtenir
   séparément (Moniteur belge / Wallex).
6. Combler si possible les 2 sections à `contenu_texte` vide identifiées dans le volet logiciel
   (manuel 07 chapitre 2, manuel 26 chapitre 1) en ré-extrayant directement depuis le PDF
   source.
7. Clarifier avec l'utilisateur le point d'accès local pour le trésorier bénévole (voir section
   dédiée ci-dessus) avant d'exposer l'outil au-delà de l'équipe support.
8. Décider privé/public du dépôt GitHub distant (https://github.com/suyttenhoef-cyber/ReligioBot,
   visibilité actuelle non vérifiée par l'assistant).

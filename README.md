# Assistant ReligioSoft

Assistant IA (RAG, 100% local — pas d'infrastructure Azure ni de canal Teams) d'aide sur le
logiciel **ReligioSoft** et sur la réglementation comptable/légale des fabriques d'église en
Région wallonne. Voir [CLAUDE.md](CLAUDE.md) pour le contexte complet du projet.

Deux publics :
- les **utilisateurs de ReligioSoft** (trésoriers de fabriques d'église, souvent bénévoles) ;
- l'**équipe support/helpdesk Vanden Broele** (`cultes@religiosoft.be`, 02 308 29 06).

## Installation et lancement local

```bash
git clone <url-du-depot>
cd Bot_religio
pip install -r requirements.txt
cp .env.example .env   # puis renseigner OPENAI_API_KEY dans .env
```

Interface web (Streamlit) :

```bash
streamlit run app.py
```

Interface terminal (alternative) :

```bash
python3 chat_loop.py
```

Les deux nécessitent que le pipeline d'embeddings ait déjà tourné une fois (voir section
"Pipeline" ci-dessous) — `embeddings.npz` et `embeddings_meta.jsonl` sont versionnés dans le
dépôt pour que l'interface fonctionne dès le clonage, sans clé API ni appel réseau préalable.

## Structure du dépôt

```
Bot_religio/
├── CLAUDE.md                        # contexte projet (à consulter en premier)
├── app.py / chat_loop.py            # interfaces (Streamlit / terminal)
├── rag_answer.py                    # génération de réponse + garde-fous anti-hallucination
├── retrieve.py                      # recherche par similarité (numpy local)
├── chunk_builder.py                 # corpus → chunks.jsonl
├── embed_chunks.py                  # chunks.jsonl → embeddings.npz
├── corpus_par_matiere/              # corpus JSON, une matière par fichier
├── Ressources_brutes/
│   ├── manuels_religiosoft/         # PDF des manuels utilisateur ReligioSoft
│   ├── bases_legales/               # textes légaux/circulaires (à obtenir, voir CLAUDE.md)
│   └── extraction_manuels_ancienne/ # extraction JSON déjà réalisée sur les manuels (prototype
│                                     # antérieur, à reprendre/convertir vers le schéma du corpus)
└── Doc/
    └── brief_demarrage_religiosoft.md  # brief initial (historique)
```

## Schéma du corpus

Chaque fichier `corpus_par_matiere/corpus_<matiere>.json` suit ce schéma (repris de
`chatbot_etat_civil`) :

```json
{
  "_matiere": "usage_logiciel",
  "documents": [
    {"document_id": "manuel_...", "titre": "...", "type": "manuel_utilisateur", "statut": "en_vigueur"}
  ],
  "articles": [
    {"entry_id": "manuel_...#section_...", "document_id": "manuel_...",
     "numero": "...", "titre_contexte": "...", "texte": "...",
     "categorie": "usage_logiciel", "sous_categorie": "...",
     "articles_lies": [...], "exemples": [...]}
  ],
  "sections_circulaire": [...],
  "pratiques_validees": [
    {"entry_id": "pratique_...", "code": "PV-RF-NNN", "titre": "...", "question_origine": "...",
     "texte": "...", "precise_ou_complete": ["..."], "categorie": "...", "sous_categorie": "..."}
  ]
}
```

Conventions : pas d'accents français dans `texte`/`titre_contexte` (contrainte d'encodage
historique du pipeline), `code` au format `PV-RF-NNN` (matière `reglementation_fabriques`) ou
`PV-UL-NNN` (matière `usage_logiciel`), cité dans les réponses avec le préfixe `VDB-`.
`entry_id` = `pratique_<slug>` ou `<document_id>#art_<numero_slugifie>`.

Matières actuelles :
- `reglementation_fabriques` — décrets, lois, CDLD, circulaires (squelette avec les 12 sources
  à obtenir, voir CLAUDE.md — aucun article n'est encore extrait).
- `usage_logiciel` — manuels ReligioSoft (squelette, un seul document déclaré à ce stade).

## Pipeline

```bash
python3 chunk_builder.py corpus_par_matiere/ chunks.jsonl
python3 embed_chunks.py chunks.jsonl embeddings.npz   # nécessite OPENAI_API_KEY
```

À relancer après chaque ajout de contenu au corpus, avant de tester dans l'interface (voir
CLAUDE.md, section "Prochaines étapes").

## Garde-fous anti-hallucination (`rag_answer.py`)

- `check_citation_integrity` : détecte un numéro d'article/section cité par le modèle qui
  n'existe dans aucune source fournie.
- `check_citation_relevance` : détecte une citation qui existe réellement mais ne soutient pas
  l'affirmation à laquelle elle est associée (sujet voisin, pas le bon point).
- `filter_applicable_practices` : avant génération, écarte les pratiques validées dont les
  prémisses ne correspondent pas aux faits de la question.
- `SYSTEM_PROMPT` : règles groupées A (citation) / B (incertitude — poser une question de
  clarification, dire explicitement quand le corpus ne couvre pas le sujet) / C (ne jamais
  transposer aveuglément une pratique à un cas différent) / D (structure/ton accessible) / E
  (format technique).

## État et limites connues

Voir [CLAUDE.md](CLAUDE.md) — en résumé : corpus encore vide (squelettes de schéma en place),
manuels ReligioSoft disponibles en PDF (non encore extraits vers le schéma du corpus), 12
sources légales encore à obtenir en texte intégral, point d'accès pour le trésorier bénévole non
technique à clarifier.

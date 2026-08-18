# 01 - Bootstrap du depot

## Objectif

Initialiser une base Python propre, portable et testable pour zoeTrading.

## Livrables

- Structure de dossiers : `zoetrading/`, `config/`, `tests/`, `mt5/`, `scripts/`, `docs/`.
- `pyproject.toml` avec dependances de base, formatage et tests.
- `.gitignore` adapte : `.env`, logs, bases locales, caches, exports MT5.
- `.env.example`.
- `README.md` avec demarrage local V1.
- Point d'entree unique : `zoetrading/main.py`.

## Criteres d'acceptation

- `python -m zoetrading.main` demarre en mode neutre sans envoyer d'ordre.
- Les tests de base passent.
- Aucun secret ni fichier runtime n'est versionne.
- Le depot reste compatible avec le repo cible GitHub.


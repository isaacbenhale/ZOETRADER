# 18 - Interface web locale (lancer et suivre)

Statut : IMPLEMENTEE

## Objectif

Fournir une interface graphique pour lancer et suivre le systeme (etat, decisions, rapport de backtest), a la demande explicite de l'utilisateur qui a choisi de lever le non-objectif "pas de dashboard web" documente initialement dans `PRD.md`/`VISION.md`.

## Contexte et decision de portee

`PRD.md` (section "Interface web locale") documente la levee du non-objectif et les contraintes non negociables qui la remplacent : serveur local uniquement (`127.0.0.1` par defaut), lecture et lancement uniquement, aucune autorite d'execution. `VISION.md` a ete mis a jour en consequence. Le document de conception `.docx` (section 2) n'a pas ete modifie automatiquement pour eviter de corrompre sa mise en forme ; l'ecart est documente dans `PRD.md`.

## Livrables

- `zoetrading/ui/app.py` : backend FastAPI exposant des endpoints de lecture (`/api/status`, `/api/decisions`, `/api/events`, `/api/backtest-report`) et de lancement (`/api/actions/bootstrap|healthcheck|scan|backtest`), reutilisant `RuntimeEngine`, `run_library_backtest`, `JournalStore` sans dupliquer de logique metier. `AUTO` est refuse explicitement (400) depuis cette interface.
- `JournalStore.list_recent_decisions` / `list_recent_events` : nouvelles methodes de lecture generiques, reutilisables au-dela de l'UI.
- Commande CLI `python -m zoetrading.main ui` (et `scripts/start-local.ps1 -Action ui`) : sert l'API + le frontend construit, ecoute sur `127.0.0.1:8765` par defaut, avertit si l'hote est change.
- `webui/` : frontend React + Vite (statut en direct, panneau d'actions, tableau des decisions recentes, tableau du rapport de backtest). Le build est commite dans `zoetrading/ui/static/`, servi directement par FastAPI ; Node.js n'est necessaire que pour modifier le frontend.
- Extra pip `ui` (`fastapi`, `uvicorn`) dans `pyproject.toml`, importe uniquement a l'appel de la commande `ui` pour ne pas alourdir la CLI de base.
- Tests (`tests/test_ui_api.py`) avec un client MT5 factice : actions bootstrap/healthcheck/scan/backtest, refus d'AUTO, gestion d'un MT5 indisponible (502), lecture du statut/decisions/rapport.

## Criteres d'acceptation

- Le serveur n'ecoute que sur `127.0.0.1` sauf changement explicite de `--host`, avec avertissement affiche dans ce cas.
- Aucun endpoint ne peut approuver un ordre, modifier une position ou activer AUTO ; `mode=AUTO` est rejete par l'API (`scan` et `bootstrap`).
- Le Risk Engine reste seul autorite finale : les endpoints de lancement passent par les memes `RuntimeEngine`/`DecisionEngine` que la CLI, sans les contourner.
- Une erreur de connexion MT5 renvoie une erreur HTTP explicite (502) sans faire planter le serveur.
- Les tests passent sans terminal MT5 installe (client MT5 factice injectable via `mt5_client_factory`).

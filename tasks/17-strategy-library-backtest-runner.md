# 17 - Outil de mesure de performance de la bibliotheque de strategies

Statut : IMPLEMENTEE

## Objectif

Fournir un outil qui mesure objectivement (win rate, expectancy, profit factor, drawdown, MFE/MAE) chaque combinaison instrument/strategie sur l'historique MT5 reel, plutot que de presumer qu'une strategie est performante. Aucun resultat de backtest n'est une garantie de performance future.

## Contexte

Le document de conception (section 14) exige un backtest historique avant toute progression vers demo, shadow mode ou MANUAL observe. La bibliotheque de strategies etant desormais complete (task 16), il fallait un moyen de la mesurer sans supposer un taux de gain ou un profit garanti, ce qui est explicitement un non-objectif (section 1.2, Annexe B).

## Livrables

- `zoetrading/backtesting/runner.py` : `run_library_backtest` execute `BacktestEngine` pour chaque instrument active x chaque strategie de `default_strategies()`, a partir des bougies MT5 reelles (timeframe de setup configure), et retourne un `StrategyBacktestReport` classe par expectancy.
- Commande CLI `python -m zoetrading.main backtest` (et `scripts/start-local.ps1 -Action backtest`) : se connecte a MT5, lance la mesure, affiche un tableau trie par expectancy, ecrit `data/backtest_report.json` et journalise l'evenement.
- Documentation operationnelle mise a jour (`docs/local-operations.md`, `README.md`) pour situer le backtest comme etape de mesure prealable a demo/shadow/MANUAL.
- Tests unitaires avec un client MT5 factice couvrant : un resultat par strategie, tri par expectancy, et le cas ou l'historique disponible est insuffisant.

## Criteres d'acceptation

- Aucun texte ne presente un resultat de backtest comme une garantie ou une probabilite de gain future.
- Un instrument sans historique suffisant est ignore et journalise, sans arreter la mesure des autres instruments.
- Le rapport ecrit est reconstructible (instrument, strategie, timeframe, hypotheses de cout, metriques completes).
- Aucune connexion au Risk Engine ni a l'execution : l'outil est strictement une mesure hors ligne.

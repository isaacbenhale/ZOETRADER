# Exploitation locale Windows

La V1 fonctionne d'abord sur laptop Windows, sans VPS obligatoire.

## Demarrage

1. Ouvrir MetaTrader 5.
2. Verifier la connexion au compte demo ou reel controle.
3. Lancer `scripts/start-local.ps1 -Action healthcheck`.
4. Lancer `scripts/start-local.ps1 -Action scan -Mode MONITORING -Equity 10000`.
5. Verifier `data/trading.db` et `data/zoetrading_status.csv`.
6. Passer a `MANUAL` uniquement lorsque les signaux sont observables et journalises.

## Arret

Lorsque le moteur Python ou le laptop est arrete, aucune nouvelle logique locale ne tourne. Les SL/TP deja transmis au broker peuvent rester actifs cote broker, mais trailing, sorties dynamiques et nouvelles entrees cessent.

## Mesure de performance (avant toute decision d'exploitation)

`scripts/start-local.ps1 -Action backtest` (ou `python -m zoetrading.main backtest`) execute chaque strategie de la bibliotheque sur l'historique MT5 reel de chaque instrument configure et calcule win rate, expectancy, profit factor, drawdown, MFE/MAE. Le rapport est ecrit dans `data/backtest_report.json` et journalise.

Ces chiffres ne sont **jamais** une garantie de resultat futur : ce sont des mesures historiques utilisees pour decider objectivement quelles combinaisons instrument/strategie meritent de continuer vers demo puis shadow mode. Une strategie avec `expectancy <= 0` ou `profit_factor <= 1` ne doit pas progresser.

## Phases

- Backtest : mesure historique, aucune exposition, sert a filtrer les strategies.
- Demo : aucune exposition reelle.
- Shadow mode : decisions temps reel sans execution.
- MANUAL : approbation humaine requise.
- Micro-exposition : uniquement apres criteres de validation.

## Sauvegarde

Utiliser `scripts/backup-local.ps1` pour copier la base SQLite et les configs.

## Interface web locale (suivi visuel)

`python -m zoetrading.main ui` sert une interface web sur `http://127.0.0.1:8765` (jamais expose reseau par defaut) qui affiche l'etat courant, les decisions journalisees et le dernier rapport de backtest, et permet de lancer bootstrap/healthcheck/scan/backtest depuis le navigateur. Elle ne remplace pas MT5 : l'approbation MANUAL (APPROVE/REJECT) et le kill switch restent exclusivement dans le panneau EA. Voir `PRD.md` section "Interface web locale" pour les contraintes.

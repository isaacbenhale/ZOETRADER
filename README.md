# zoeTrading

zoeTrading est un systeme local d'aide, de decision et d'execution algorithmique pour MetaTrader 5. La V1 vise un fonctionnement sur laptop Windows avec Python, MT5, un EA MQL5 compagnon et SQLite, avant une migration eventuelle vers VPS Windows.

Depot cible : https://github.com/isaacbenhale/ZOETRADER.git

## Etat actuel

Tasks implementees :

- Task 01 : bootstrap du depot.
- Task 02 : configuration et modeles domaine.
- Task 03 : couche market data MT5, cache de bougies et controle de fraicheur.
- Task 04 : journal SQLite, logs structures, identifiants uniques et traces de decisions.
- Task 05 : indicateurs techniques, swings, structure, niveaux, breakout/retest et volatilite.
- Task 06 : classification de regime, biais multi-timeframe et filtrage strategie/regime.
- Task 07 : moteur de strategies deterministes avec Trend Pullback, Breakout Retest et Range Reversal.
- Tasks 08-12 : Risk Engine, Decision Engine, Execution Engine, Position Monitor et EA MT5 compagnon.
- Tasks 13-15 : backtesting/validation, exploitation locale Windows, gate AUTO et readiness VPS.
- Task 16 : completion de la bibliotheque de strategies (Structure Continuation, Momentum Breakout, Mean Reversion, Reversal).

Le projet contient pour l'instant un point d'entree neutre qui demarre sans connexion MT5 et sans possibilite d'envoyer un ordre. Les modules reels de donnees, analyse, risque et execution seront ajoutes progressivement via les taches dans `tasks/`.
La couche MT5 est encapsulee et testable sans terminal installe; l'installation Windows avec le package `MetaTrader5` sera requise pour lire les donnees reelles.

## Demarrage local

Depuis la racine du depot :

```bash
python -m zoetrading.main bootstrap
```

Sortie attendue :

```text
zoeTrading bootstrap OK
mode=MONITORING
orders_enabled=false
config_loaded=true
```

Le mode par defaut est `MONITORING`. A ce stade, aucun ordre ne peut etre envoye.

## Test operationnel Windows + MT5

Avec MT5 ouvert et connecte :

```powershell
python -m zoetrading.main healthcheck
python -m zoetrading.main scan-once --mode MONITORING --equity 10000
```

Ou via le script Windows :

```powershell
.\scripts\start-local.ps1 -Action healthcheck
.\scripts\start-local.ps1 -Action scan -Mode MONITORING -Equity 10000
```

Le scan lit les instruments configures, analyse les timeframes, produit des decisions, journalise dans `data/trading.db` et ecrit `data/zoetrading_status.csv` pour l'EA compagnon. `scan-once` n'autorise pas `AUTO`.

## Tests

Sans dependances externes :

```bash
python -m unittest discover -s tests
```

Avec les dependances de developpement installees :

```bash
pytest
```

## Structure

```text
AGENTS.md
CLAUDE.md
VISION.md
PRD.md
Document/
docs/
config/
mt5/
scripts/
tasks/
tests/
zoetrading/
```

## Workflow Git

Le projet travaille directement sur `main`. Les pushes se font directement sur `main` lorsque demande, sans branches ni PR sauf instruction explicite.

## Regles de securite

- Pas de secrets dans le depot.
- Pas de martingale.
- Pas d'ordre sans Stop Loss ou invalidation.
- Le Risk Engine aura toujours autorite finale.
- Le mode AUTO reel est interdit sans validation quantitative documentee.

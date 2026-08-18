# zoeTrading

zoeTrading est un systeme local d'aide, de decision et d'execution algorithmique pour MetaTrader 5. La V1 vise un fonctionnement sur laptop Windows avec Python, MT5, un EA MQL5 compagnon et SQLite, avant une migration eventuelle vers VPS Windows.

Depot cible : https://github.com/isaacbenhale/ZOETRADER.git

## Etat actuel

Tasks implementees :

- Task 01 : bootstrap du depot.
- Task 02 : configuration et modeles domaine.
- Task 03 : couche market data MT5, cache de bougies et controle de fraicheur.

Le projet contient pour l'instant un point d'entree neutre qui demarre sans connexion MT5 et sans possibilite d'envoyer un ordre. Les modules reels de donnees, analyse, risque et execution seront ajoutes progressivement via les taches dans `tasks/`.
La couche MT5 est encapsulee et testable sans terminal installe; l'installation Windows avec le package `MetaTrader5` sera requise pour lire les donnees reelles.

## Demarrage local

Depuis la racine du depot :

```bash
python -m zoetrading.main
```

Sortie attendue :

```text
zoeTrading bootstrap OK
mode=MONITORING
orders_enabled=false
config_loaded=true
```

Le mode par defaut est `MONITORING`. A ce stade, aucun ordre ne peut etre envoye.

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

# AGENTS.md

## Projet

zoeTrading est un systeme local d'aide, de decision et d'execution algorithmique pour Forex et indices synthetiques via MetaTrader 5. La V1 doit fonctionner d'abord sur un laptop Windows avec Python, MT5, un EA MQL5 compagnon et SQLite. La migration vers un VPS Windows doit rester une operation d'exploitation, pas une reecriture metier.

Depot cible : https://github.com/isaacbenhale/ZOETRADER.git

## Workflow Git

- Le projet travaille simplement sur `main`.
- Les changements peuvent etre commits et pushes directement sur `main` lorsque l'utilisateur le demande.
- Ne pas creer de branches, PR ou workflow complexe sauf demande explicite.
- Apres chaque task implementee, ajouter le statut en debut du fichier de task concerne.
- Apres chaque implementation de task, commit puis push directement sur `main`.
- Avant un push, verifier rapidement l'etat Git, les fichiers modifies et les tests pertinents.

## Principe directeur

Construire un systeme rapide, mesurable, auditable et prudent. Aucun rendement n'est garanti. Le mode AUTO reel n'est autorise qu'apres validation robuste : tests unitaires, backtests realistes, hors-echantillon, demo, shadow mode, observation MANUAL et criteres quantitatifs documentes.

## Regles non negociables

- Le Risk Engine a toujours autorite finale sur toute strategie, IA ou signal.
- `NO TRADE` est une decision valide.
- Aucun ordre ne part sans Stop Loss ou invalidation definie.
- La martingale et l'augmentation automatique du risque pour recuperer une perte sont interdites.
- Le passage `MANUAL` vers `AUTO` doit etre explicite, journalise et reversible.
- Les secrets, identifiants MT5 et tokens ne doivent jamais etre commits.
- Toute decision doit pouvoir etre reconstruite a partir des donnees, de la configuration et des journaux.
- Une strategie modifiee doit repasser par le processus de validation avant AUTO.

## Architecture attendue

Respecter une separation stricte entre :

- `market` : connexion MT5, ticks, OHLC, cache, fraicheur des donnees.
- `analysis` : structure, tendance, momentum, volatilite, support/resistance, liquidite, regime, multi-timeframe.
- `strategies` : strategies independantes et testables, separees par familles d'instruments si necessaire.
- `intelligence` : scoring, decision, modeles eventuels, sans autorite d'execution directe.
- `risk` : sizing, limites, SL/TP, controles portefeuille, blocages.
- `execution` : ordres, idempotence, erreurs broker, reconciliation MT5.
- `monitoring` : suivi de positions, trailing, sorties dynamiques, kill switch.
- `journal` : SQLite, logs structures, analytics, metriques de validation.
- `mt5` : EA MQL5 compagnon, panneau, boutons, annotations graphiques.

## Standards de developpement

- Python 3.x, typage explicite quand utile, fonctions pures pour les calculs critiques.
- Configurations en fichiers versionnes d'exemple, valeurs sensibles hors depot.
- Tests unitaires pour les calculs, regles de risque, transitions d'etat et strategies.
- Journalisation structuree avec identifiants uniques de signal, decision, ordre et position.
- Mesurer la performance et la latence avant toute optimisation complexe.
- Preferer des modules simples et composables a une abstraction prematuree.

## Definition of Done

Une tache est terminee lorsque :

- Le comportement demande est implemente et documente si necessaire.
- Les tests pertinents existent et passent localement.
- Les erreurs previsibles sont gerees sans arreter tout le scanner.
- Les decisions et refus importants sont journalises.
- Les garde-fous de risque restent non contournables.
- La tache ne cree pas de dependance au VPS pour la V1 locale.

## Ordre de priorite

1. Securite du capital et prevention des ordres dangereux.
2. Auditabilite et reproductibilite.
3. Robustesse de fonctionnement local.
4. Qualite statistique des strategies.
5. Performance et confort d'exploitation.

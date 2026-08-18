# 10 - Execution Engine

## Objectif

Envoyer des ordres MT5 uniquement apres validation complete.

## Livrables

- Validation immediate : connexion, prix, spread, volume, symbole, doublon.
- Construction `OrderRequest`.
- Envoi ordre avec SL initial.
- Idempotence par identifiant decision/ordre.
- Reconciliation serveur et journalisation.

## Criteres d'acceptation

- Un doublon de decision ne cree pas deux ordres.
- Une erreur broker est journalisee et n'arrete pas le systeme.
- Le mode `MONITORING` ne peut jamais envoyer d'ordre.


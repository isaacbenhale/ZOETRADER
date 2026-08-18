# 09 - Decision Engine et scoring

Statut : IMPLEMENTEE

## Objectif

Assembler analyse, regime, strategies et risque en decisions explicables.

## Livrables

- Pipeline `BUY` / `SELL` / `NO_TRADE`.
- Score de setup documente comme conformite, pas probabilite.
- Raisons, blockers et preuves attachees a chaque decision.
- Anti-double-comptage pour strategies correlees.

## Criteres d'acceptation

- Une decision contient tous les champs du PRD.
- `NO_TRADE` est journalise avec justification.
- Le Risk Engine reste appele apres le scoring et avant toute execution.

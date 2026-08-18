# 04 - Journal SQLite et logs structures

Statut : IMPLEMENTEE

## Objectif

Rendre le systeme auditable des le debut.

## Livrables

- Schema SQLite pour signaux, decisions, refus, ordres, positions, evenements et metriques.
- Logger structure JSON ou equivalent.
- Identifiants uniques pour signal, decision, ordre et position.
- Fonctions de lecture pour analytics de base.

## Criteres d'acceptation

- Un signal refuse est journalise avec raison.
- Une decision peut etre reliee a sa configuration.
- Les logs permettent de reconstruire le chemin decisionnel.

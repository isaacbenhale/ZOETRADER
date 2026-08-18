# 11 - Monitoring et sorties dynamiques

Statut : IMPLEMENTEE

## Objectif

Gerer les positions apres entree selon des regles testees.

## Livrables

- Lecture/reconciliation des positions MT5 ouvertes.
- Reevaluation de l'invalidation et du regime.
- Trailing fixe, ATR ou structurel selon strategie.
- Break-even, prises partielles et sorties anticipees configurables.
- Kill switch pour nouvelles entrees et comportement sur positions existantes.

## Criteres d'acceptation

- Le monitoring est prioritaire sur la recherche de nouvelles opportunites.
- Les modifications SL/TP et sorties sont journalisees.
- Les politiques de sortie sont testees avec donnees historiques ou fixtures.

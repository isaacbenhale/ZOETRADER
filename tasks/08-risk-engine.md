# 08 - Risk Engine

## Objectif

Construire la couche non contournable qui decide si une opportunite peut etre tradable.

## Livrables

- Calcul de taille de position selon capital, SL et risque.
- Limites : risque par trade, perte journaliere, perte hebdomadaire, positions simultanees.
- RR minimal par strategie.
- Cooldown apres pertes consecutives.
- Refus martingale et SL manquant.

## Criteres d'acceptation

- Le Risk Engine peut refuser n'importe quelle proposition.
- Aucune execution n'est possible sans decision risque positive.
- Les tests couvrent les cas limites et refus critiques.


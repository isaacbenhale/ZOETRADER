# 05 - Moteur d'analyse technique

Statut : IMPLEMENTEE

## Objectif

Implementer les briques d'analyse communes aux strategies.

## Livrables

- Swings hauts/bas.
- Structure HH/HL, LH/LL.
- Break of Structure, range, breakout, retest.
- Supports/resistances et invalidations.
- Momentum et volatilite : RSI, MACD, ROC, ATR lorsque disponibles.

## Criteres d'acceptation

- Chaque calcul critique possede des tests unitaires.
- Les sorties d'analyse sont deterministes sur un jeu de donnees fixe.
- Les indicateurs ne sont pas dupliques inutilement entre strategies.

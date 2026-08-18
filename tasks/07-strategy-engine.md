# 07 - Moteur de strategies

## Objectif

Ajouter les premieres strategies deterministes sous forme de modules independants.

## Livrables

- Interface commune de strategie.
- Strategies initiales : Trend Pullback, Breakout Retest, Range Reversal.
- Separation des parametres Forex et indices synthetiques.
- Statistiques individuelles par strategie.

## Criteres d'acceptation

- Chaque strategie retourne une proposition normalisee ou un refus motive.
- Une strategie inactive pour un regime ne produit pas de faux signal.
- Les strategies sont testables sans MT5.


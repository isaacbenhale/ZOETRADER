# 06 - Regime de marche et multi-timeframe

Statut : IMPLEMENTEE

## Objectif

Determiner le contexte exploitable avant d'autoriser une strategie.

## Livrables

- Classification des regimes : tendance, range, breakout, haute/basse volatilite, chaotique.
- Biais par timeframe.
- Alignement context/setup/timing.
- Blocage ou penalisation des conflits majeurs.

## Criteres d'acceptation

- Une strategie de tendance est bloquee en range non compatible.
- Un contexte chaotique produit `NO_TRADE`.
- Les decisions exposent le regime et le biais utilise.

# 15 - Gate AUTO et readiness VPS

Statut : IMPLEMENTEE

## Objectif

Formaliser les conditions de passage en AUTO puis preparer la migration VPS sans modifier la logique metier.

## Livrables

- Checklist AUTO : backtest, hors-echantillon, demo, shadow, MANUAL, limites drawdown.
- Parametres d'exposition minimale.
- Procedure de rollback vers MANUAL/MONITORING.
- Documentation migration VPS Windows.
- Separation chemins, secrets et demarrage automatique.

## Criteres d'acceptation

- AUTO reel est bloque sans validation quantitative documentee.
- Le passage VPS ne change pas strategies, Risk Engine ni Decision Engine.
- Les differences laptop/VPS sont limitees a environnement, chemins, secrets et supervision.

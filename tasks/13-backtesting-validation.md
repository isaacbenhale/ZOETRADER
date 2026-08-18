# 13 - Backtesting et validation

Statut : IMPLEMENTEE

## Objectif

Prouver ou rejeter les strategies avant toute automatisation reelle.

## Livrables

- Harness de backtest avec couts, spread et slippage.
- Jeux train/validation/hors-echantillon si modele ML.
- Walk-forward testing.
- Stress tests et Monte-Carlo sur sequences de trades.
- Rapports par instrument, strategie, timeframe et regime.

## Criteres d'acceptation

- Une strategie sans expectancy positive hors-echantillon reste interdite en AUTO.
- Les metriques incluent profit factor, drawdown, win rate, gain/perte moyen, MFE, MAE.
- Les hypotheses de couts sont explicites.

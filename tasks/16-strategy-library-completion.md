# 16 - Completion de la bibliotheque de strategies

Statut : IMPLEMENTEE

## Objectif

Completer la bibliotheque de strategies deterministes prevue par le document de conception (section 8.2) : Structure Continuation, Momentum Breakout, Mean Reversion et Reversal, en complement de Trend Pullback, Breakout Retest et Range Reversal deja livrees en task 07.

## Livrables

- `StructureContinuationStrategy` : BOS confirme puis reprise de structure apres retracement (regimes TRENDING_UP/TRENDING_DOWN).
- `MomentumBreakoutStrategy` : cassure confirmee par momentum (ROC) et expansion de volatilite (ATR), sans exigence de retest (regime BREAKOUT).
- `MeanReversionStrategy` : extension statistique (RSI + deviation ATR par rapport a une moyenne mobile) avec objectif de retour a la moyenne (regime RANGING).
- `ReversalStrategy` : changement de structure (higher low / lower high) confirme par une divergence de momentum RSI (regimes TRENDING_UP/TRENDING_DOWN).
- Integration au `StrategyEngine` par defaut via `default_strategies()`.
- Ajout des seuils de RR minimal par strategie dans `config/risk.yaml`.
- Tests unitaires pour chaque nouvelle strategie, cas trade et cas NO_TRADE motive.

## Criteres d'acceptation

- Chaque strategie retourne une proposition normalisee ou un refus motive.
- Une strategie inactive pour un regime ne produit pas de faux signal.
- Les strategies sont testables sans MT5.
- Le Risk Engine reste seul autorite finale ; aucune strategie ne peut envoyer d'ordre.
- Le Decision Engine reste generique et n'a pas besoin de connaitre les noms de strategies pour selectionner le meilleur signal.

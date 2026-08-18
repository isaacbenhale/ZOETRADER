# 02 - Configuration et modeles domaine

Statut : IMPLEMENTEE

## Objectif

Definir les configurations et schemas internes qui stabilisent tout le systeme.

## Livrables

- `settings.yaml`, `risk.yaml`, `instruments.yaml` d'exemple.
- Modeles pour `MarketSnapshot`, `Signal`, `Decision`, `RiskDecision`, `OrderRequest`, `PositionState`.
- Enumerations : actions, regimes, modes, etats systeme, raisons de refus.
- Chargement de config avec validation.

## Criteres d'acceptation

- Une configuration invalide echoue explicitement au demarrage.
- Les modeles empechent les decisions incompletes.
- `NO_TRADE`, `REJECT` et `KILL_SWITCH` sont modelises comme etats normaux.

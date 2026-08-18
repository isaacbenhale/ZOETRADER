# 12 - EA MQL5 compagnon

Statut : IMPLEMENTEE

## Objectif

Fournir l'interface MT5 de la V1 sans y deplacer la logique metier principale.

## Livrables

- `mt5/ZoeTradingEA.mq5`.
- Panneau etat : RUNNING, PAUSED, ERROR.
- Mode : MANUAL, AUTO.
- Dernier signal : instrument, strategie, regime, score, entree, SL, TP, risque.
- Boutons APPROVE, REJECT, PAUSE, KILL SWITCH.
- Annotations Entry/SL/TP et BUY/SELL sur graphique.

## Criteres d'acceptation

- En MANUAL, l'utilisateur peut approuver ou rejeter un signal.
- Le kill switch est visible et actif.
- L'EA n'embarque pas le coeur de decision ni le Risk Engine.

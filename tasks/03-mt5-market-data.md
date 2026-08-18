# 03 - Connexion MT5 et donnees marche

## Objectif

Connecter le moteur Python au terminal MT5 local et produire des donnees fiables.

## Livrables

- Client MT5 encapsule dans `market/mt5_client.py`.
- Recuperation ticks, OHLC, spread, symbol info et positions ouvertes.
- Cache de bougies par instrument/timeframe.
- Controle de fraicheur des donnees.
- Gestion des erreurs de connexion et symboles indisponibles.

## Criteres d'acceptation

- Le moteur detecte clairement MT5 absent ou deconnecte.
- Une erreur sur un symbole ne stoppe pas tout le scanner.
- Aucune decision n'est produite avec donnees obsoletes.


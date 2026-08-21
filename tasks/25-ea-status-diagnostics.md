# 25 - Diagnostics visibles quand le panneau MT5 ne recoit rien

Statut : IMPLEMENTEE

## Objectif

Le panneau MT5 restait bloque sur ses valeurs par defaut ("Status: PAUSED | Signal: NO SIGNAL") sans jamais dire pourquoi -- meme apres avoir confirme que le fichier de statut existait, etait a jour et correspondait exactement au symbole du graphique ouvert (capture utilisateur : graphique `Volatility 100 Index,H1`, proposition en cours pour ce meme instrument, panneau toujours a "PAUSED / NO SIGNAL"). `LoadStatus()` retournait silencieusement des que `FileOpen` echouait, sans aucune trace nulle part -- impossible a diagnostiquer a distance.

## Cause

`FileOpen(Zoe_StatusFile, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON)` peut echouer pour plusieurs raisons distinctes (chemin different en mode portable, permissions, fichier absent) et **aucune** n'etait visible : ni dans les logs, ni sur le graphique. Le symptome ("rien ne s'affiche") etait donc identique que la cause soit un vrai probleme ou simplement l'absence normale de nouvelle donnee.

## Livrables

- `mt5/ZoeTradingEA.mq5` (version 0.4 -> 0.5) :
  - `LoadStatus()` journalise desormais dans l'onglet **Experts** le code d'erreur reel (`GetLastError()`) a chaque echec de `FileOpen`, une seule fois par code d'erreur (pas de spam a chaque tick de 1s).
  - Chaque lecture reussie horodate `g_last_read_ok`.
  - `DrawPanel()` : la ligne "Status:" passe en rouge/orange avec `AUCUNE DONNEE RECUE (erreur N, voir Experts)` si aucune lecture n'a jamais reussi, ou `(perime depuis Ns)` si plus de 10s se sont ecoulees depuis la derniere lecture reussie -- ce dernier cas ne se declenche jamais pendant une attente d'approbation normale (jusqu'a 120s), puisque l'ouverture/lecture du fichier reussit a chaque tick meme quand son contenu n'a pas change entre deux scans.
- `docs/usage-guide.md` : reflexe de diagnostic ajoute a l'etape 5 (regarder la ligne Status + l'onglet Experts en premier).

## Ce qui reste hors scope

- Ne detecte pas le cas ou le processus Python s'est arrete completement mais laisse un fichier valide sur disque (l'EA continuerait a le lire avec succes indefiniment, donc `g_last_read_ok` resterait "frais"). Corriger ce cas necessiterait un champ d'horodatage explicite ecrit par Python dans le fichier de statut et une logique de seuil dependante de `refresh_interval_seconds`/`approval_timeout` -- non demande ici, a envisager separement si besoin.
- Aucun changement cote Python -- purement diagnostic MT5.

## Criteres d'acceptation

- Un `FileOpen` qui echoue produit une trace exploitable dans l'onglet Experts avec le vrai code d'erreur Windows/MT5.
- Le panneau distingue visuellement "jamais recu de donnees" de "donnees perimees" de "fonctionne normalement", sans faux positif pendant une attente d'approbation normale.

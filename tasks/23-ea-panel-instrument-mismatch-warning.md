# 23 - Avertissement visuel quand le signal affiche concerne un autre graphique

Statut : IMPLEMENTEE

## Objectif

L'utilisateur a demande, apres avoir compris que le panneau MT5 affiche la meilleure proposition parmi **tous** les instruments surveilles (pas seulement le symbole du graphique ouvert), un moyen d'eviter de confondre un signal pour un autre instrument avec le graphique courant.

## Contexte

Voir l'echange precedent : le panneau `zoeTrading` affiche toujours le meme texte (`Signal: BUY EURUSD | Strategy: ...`) quel que soit le graphique sur lequel l'EA est attache, puisque `zoetrading_status.csv` ne contient que la meilleure decision globale (`select_display_decision`). Les lignes Entry/SL/TP et la fleche BUY/SELL etaient deja filtrees par symbole (task 19), mais rien n'attirait l'oeil sur le texte du panneau quand l'instrument affiche differe du graphique courant -- un operateur pressé pouvait lire "Entry/SL/TP" en pensant qu'ils concernent son graphique alors qu'ils concernent un autre symbole.

## Livrables

- `mt5/ZoeTradingEA.mq5` (version 0.3 -> 0.4) :
  - `HasTradeSignal()` / `SignalMatchesChart()` : deux fonctions helper qui devient la seule source de verite pour savoir si le signal affiche concerne le symbole du graphique courant, utilisees a la fois par `DrawPanel()` et `UpdateChartAnnotations()` (qui utilisait deja cette logique en interne, maintenant factorisee).
  - `DrawPanel()` : si un signal de trade reel existe pour un autre instrument, la ligne "Signal:" passe en couleur **orange** et affiche `<<< AUTRE GRAPHIQUE (SYMBOLE)` a la fin du texte. Aucun changement pour `NO SIGNAL`/`NO_TRADE` (rien a signaler) ni quand le signal correspond deja au graphique courant.
- `docs/usage-guide.md` : note ajoutee a l'etape 5 (installation du panneau) expliquant ce comportement.

## Ce qui reste hors scope

- Aucun changement cote Python : le fichier de statut continue de porter une seule decision globale, comme avant (task 12/19). Ce ticket est purement une amelioration de lisibilite du panneau MT5, pas un changement de logique de scan/decision/risque.
- Non teste automatiquement (fichier `.mq5`, pas de suite de tests MQL5 dans ce depot) -- a verifier visuellement dans MetaEditor/MT5 apres recompilation.

## Criteres d'acceptation

- Quand le signal affiche concerne un instrument different du graphique courant, la ligne "Signal:" du panneau est visuellement distincte (couleur + texte explicite) sans ambiguite possible.
- Aucun changement de comportement quand le signal correspond au graphique courant, ou quand il n'y a aucun signal de trade (`NO SIGNAL`/`NO_TRADE`).
- Les lignes Entry/SL/TP et la fleche BUY/SELL restent filtrees par symbole exactement comme avant (aucune regression sur `UpdateChartAnnotations`).

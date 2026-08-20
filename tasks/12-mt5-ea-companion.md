# 12 - EA MQL5 compagnon

Statut : IMPLEMENTEE

## Correction (2026-08-20)

Bug signale par l'utilisateur : aucun suivi ni proposition visible dans MT5. Cause trouvee : `FileOpen()` cote EA n'utilisait pas `FILE_COMMON`, donc il lisait/ecrivait dans le dossier sandbox propre au terminal (`MQL5/Files/`) au lieu du dossier partage attendu par le cote Python. Corrige en ajoutant `FILE_COMMON` aux deux appels `FileOpen` ; voir `docs/usage-guide.md` etape 5 pour le chemin exact a utiliser cote Python (`--status-file` doit pointer vers `%APPDATA%\MetaQuotes\Terminal\Common\Files\`).

Deux ecarts avaient ete releves par rapport aux criteres d'acceptation ci-dessous, tous deux fermes par la task 19 :

- Le clic APPROVE/REJECT ecrivait `zoetrading_command.csv` mais rien ne le lisait cote Python. Ferme par `ManualApprovalLoop` (`zoetrading/runtime/approval_loop.py`) et la commande `approve-loop`.
- Les lignes Entry/SL/TP et annotations BUY/SELL sur le graphique n'etaient pas implementees. Ajoutees dans l'EA (`UpdateChartAnnotations`), limitees au symbole du graphique courant pour eviter d'afficher un niveau d'un autre instrument.

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

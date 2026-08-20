# 20 - Approbation MANUAL depuis l'interface web + RESUME apres KILL

Statut : IMPLEMENTEE

## Objectif

A la demande explicite de l'utilisateur (apres explication du compromis : un bouton web est plus expose qu'un clic physique sur la machine connectee au broker), rendre APPROVE/REJECT/PAUSE/KILL utilisables depuis l'interface web en plus du panneau MT5, sans ajouter de nouveau chemin d'execution. Ajouter aussi un bouton RESUME (MT5 et web) pour lever un KILL sans redemarrer le processus.

## Contexte

Voir `PRD.md`, amendement "Approbation MANUAL depuis l'interface web (2026-08-20)". `AUTO` reste hors de portee de l'interface web, sans exception -- seule l'approbation MANUAL est concernee par cet amendement.

## Livrables

- `zoetrading/operations/mt5_status.py` : `write_command_file` (le pendant Python du `WriteCommand` de l'EA) -- l'interface web ecrit dans le meme fichier que l'EA, lu par le meme `ManualApprovalLoop`.
- `zoetrading/runtime/approval_loop.py` : nouvelle commande `RESUME` (remet `kill_switch` a `False`). `KILL_SWITCH` ne fait plus sortir la boucle : elle continue de tourner mais chaque cycle retourne immediatement (`scanned=0`) tant que `RESUME` n'est pas recu. Seul `PAUSE` termine la boucle.
- `zoetrading/main.py` (`approve-loop`) et `zoetrading/ui/approval_runner.py` (`ApprovalRunner`) : mis a jour pour ce nouveau comportement (ne plus quitter sur kill, uniquement sur pause).
- `mt5/ZoeTradingEA.mq5` : bouton RESUME, echo dans `OnChartEvent`.
- `zoetrading/ui/approval_runner.py` (`ApprovalRunner`) : fait tourner `ManualApprovalLoop` dans un thread daemon dedie au sein du process FastAPI (une connexion MT5 et un JournalStore par thread, jamais partages entre threads).
- Endpoints `zoetrading/ui/app.py` : `POST /api/approval/start|stop`, `GET /api/approval/status`, `POST /api/approval/approve|reject|pause|kill|resume`. Les quatre derniers ecrivent juste dans le fichier de commande (`write_command_file`) avec le `decision_id` actuellement en attente ; ils n'appellent jamais `ExecutionEngine` directement.
- `webui/src/components/ApprovalPanel.jsx` : demarrage/arret de la boucle, affichage de la proposition en attente en direct (poll toutes les 1,5s), les 5 boutons.
- Tests : `tests/test_approval_loop.py` (RESUME leve le kill switch et la boucle re-scanne) et `tests/test_ui_approval.py` (cycle complet start -> proposition affichee -> approve -> ordre execute, 409 si pas de proposition en attente pour approve/reject, 502 si MT5 indisponible, 409 si demarrage en double).

## Ce qui reste hors scope, sans exception

- `AUTO` : aucun endpoint web ne peut l'activer ; `ManualApprovalLoop` n'appelle jamais que `RuntimeMode.MANUAL`.
- Le Risk Engine n'est jamais contourne : les boutons web ne font que relayer un clic vers la meme decision deja validee, exactement comme le panneau MT5.

## Criteres d'acceptation

- Cliquer APPROVE dans le navigateur execute reellement l'ordre (meme verification stricte du `decision_id` que pour un clic MT5).
- KILL depuis n'importe quelle interface gele la boucle sans la terminer ; RESUME depuis n'importe quelle interface la relance, sans redemarrage de processus necessaire.
- Le panneau MT5 continue de fonctionner independamment ; les deux interfaces restent symetriques (aucune n'a priorite sur l'autre).
- Aucun test ne necessite MT5 reel ; le client MT5 est injectable dans `create_app`.

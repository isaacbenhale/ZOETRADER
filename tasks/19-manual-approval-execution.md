# 19 - Boucle d'approbation MANUAL -> execution reelle

Statut : IMPLEMENTEE

## Objectif

Fermer les deux ecarts trouves en diagnostiquant le bug "aucun suivi ni proposition dans MT5" (task 12) : le clic APPROVE/REJECT dans MT5 n'avait aucun effet sur l'execution, et les niveaux Entry/SL/TP/BUY/SELL n'etaient jamais dessines sur le graphique.

## Contexte

L'utilisateur a explicitement demande d'envoyer des ordres et d'activer AUTO depuis l'interface web ; refuse (voir echange precedent et `PRD.md` section "Interface web locale"). En echange, la vraie faille identifiee a ete corrigee : le flux MANUAL prevu par le PRD (proposition -> clic MT5 -> execution) qui n'etait, dans les faits, jamais cable jusqu'au bout.

## Livrables

- `zoetrading/operations/mt5_status.py` : `write_status_file` inclut desormais `decision_id` ; `read_command_file`/`consume_command_file`/`MT5Command` pour lire et purger le fichier de commande EA.
- `mt5/ZoeTradingEA.mq5` : echo du `decision_id` affiche dans chaque commande ecrite (`WriteCommand`), pour que Python puisse verifier qu'un clic correspond exactement a la proposition affichee. Ajout de `UpdateChartAnnotations` : lignes Entry/SL/TP et fleche BUY/SELL, dessinees uniquement si le signal concerne le symbole du graphique courant.
- `zoetrading/runtime/approval_loop.py` (`ManualApprovalLoop`) : boucle MANUAL qui scanne, journalise, attend un clic pendant une fenetre configurable, puis :
  - `APPROVE` avec `decision_id` correspondant -> appelle `ExecutionEngine.execute()` (seul point d'envoi d'ordre reel).
  - `REJECT` -> journalise, aucun ordre.
  - `decision_id` different -> clic ignore et journalise comme `stale_command_ignored`, la boucle continue d'attendre.
  - `KILL_SWITCH` -> bloque toute nouvelle proposition pour le reste de la session (redemarrage requis pour reprendre).
  - `PAUSE` -> arrete proprement la boucle.
  - Timeout -> aucun ordre, journalise `approval_timeout`.
  - Le fichier de commande est purge au debut de chaque cycle et apres traitement, pour qu'un clic ne soit jamais rejoue sur une decision differente.
- Commande CLI `python -m zoetrading.main approve-loop` (et alias `-Action approve-loop` a ajouter au script si besoin).
- Tests (`tests/test_approval_loop.py`) : approbation execute un ordre, rejet n'en envoie pas, `decision_id` errone ignore, kill switch bloque les cycles suivants, fichier de commande perime purge au debut d'un cycle.

## Ce qui reste hors scope, volontairement

- `AUTO` reste inatteignable depuis cette boucle : elle appelle toujours `RuntimeMode.MANUAL`, jamais `AUTO`.
- L'interface web ne declenche pas `approve-loop` et ne peut toujours pas approuver un ordre : l'approbation reste dans MT5, cote Python execute uniquement ce que ce fichier de commande valide.

## Criteres d'acceptation

- Un clic APPROVE sur la decision affichee declenche un appel reel a `ExecutionEngine.execute()` et journalise `manual_approved` + le resultat de l'ordre.
- Un clic sur une decision perimee (decision_id different) n'execute jamais d'ordre.
- Le kill switch coupe immediatement toute nouvelle proposition, conformement a la regle non negociable.
- Le Risk Engine reste seul autorite finale : `ManualApprovalLoop` ne fait qu'executer une decision deja approuvee par `RiskEngine`, jamais autre chose.

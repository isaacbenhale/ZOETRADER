# 21 - Mode AUTO reel (execution automatique gardee par le gate)

Statut : IMPLEMENTEE

## Objectif

Ajouter le mode `AUTO` reel demande explicitement par l'utilisateur : une fois active, le systeme detecte et place les ordres automatiquement, sans clic, tout en respectant TP, SL, risque et lots -- sans jamais contourner le Risk Engine ni le gate de validation deja documente dans `docs/auto-gate.md` et `zoetrading/validation/auto_gate.py`.

## Contexte

`VISION.md`, `PRD.md`, `AGENTS.md` et `CLAUDE.md` posent une regle non negociable : "Pas de passage AUTO reel sans criteres quantitatifs documentes." `AutoValidationGate` existait deja (task 15) mais rien ne l'utilisait pour reellement executer un ordre en AUTO -- `RuntimeEngine.scan_once` refuse deliberement `RuntimeMode.AUTO` et aucune boucle n'appelait jamais `ExecutionEngine.execute(..., RuntimeMode.AUTO)`. Ce ticket ferme cet ecart, sur le meme modele que la task 19 (MANUAL) : une boucle dediee, jamais un raccourci dans le scanner ou l'UI web.

## Livrables

- `zoetrading/validation/auto_gate.py` : `load_auto_gate_evidence(path)` charge `AutoGateEvidence` depuis un fichier JSON documente sur disque (`AutoGateEvidenceError` si fichier absent, invalide ou incomplet). C'est la seule facon supportee de construire les preuves pour un run reel -- pas de raccourci en ligne de commande avec des chiffres improvises.
- `zoetrading/runtime/auto_loop.py` (`AutoTradingLoop`) : boucle qui scanne via le meme pipeline que MANUAL (`RuntimeEngine.scan_once(mode=RuntimeMode.MANUAL, ...)`, qui continue de refuser `AUTO` en interne comme garde-fou), puis execute automatiquement toute decision approuvee par le Risk Engine (`ExecutionEngine.execute(decision, RuntimeMode.AUTO)`), sans attendre de clic.
  - Construction refusee (`AutoModeBlockedError`) si `AutoGateDecision.verdict` n'est pas `ALLOW` -- impossible d'instancier la boucle sans gate valide.
  - `KILL_SWITCH` / `PAUSE` / `RESUME` restent lus depuis le meme fichier de commande que l'EA MT5 et l'interface web (task 20) : `KILL_SWITCH` gele la boucle, `PAUSE` l'arrete, `RESUME` la relance -- aucune priorite entre EA et web.
  - `REJECT` agit comme un veto humain par decision : verifie une fois avant le scan et une fois juste avant l'envoi de l'ordre (fenetre ou un humain peut annuler une proposition pendant qu'un scan MT5 est en cours), sans jamais introduire d'attente bloquante -- AUTO n'attend personne par defaut.
- `zoetrading/main.py` : nouvelle commande `python -m zoetrading.main auto-loop --gate-evidence <fichier.json> --equity ...`. Le gate est evalue et, s'il bloque, le processus s'arrete avec les raisons affichees avant meme de se connecter a MT5 -- aucune connexion broker n'est tentee si les preuves sont insuffisantes.
- Tests : `tests/test_auto_loop.py` (construction refusee sans gate ALLOW, execution automatique sans clic, kill switch gele les cycles suivants, resume relance, pause arrete la boucle, reject entre le scan et l'execution annule uniquement cette decision) et ajouts a `tests/test_backtesting_validation_operations.py` pour `load_auto_gate_evidence` (fichier valide, fichier absent, champs manquants).

## Ce qui reste hors scope, volontairement

- L'interface web ne peut toujours pas activer AUTO -- aucun endpoint web n'est ajoute ou modifie par ce ticket. Elle garde uniquement le pouvoir d'ecrire KILL_SWITCH/PAUSE/RESUME/REJECT dans le fichier de commande partage, exactement comme pour MANUAL.
- Pas de suivi P&L en direct (equity/pertes journalieres/hebdomadaires mises a jour en continu) : `auto-loop` recoit `--equity` en parametre au demarrage, au meme niveau de fidelite que `approve-loop` aujourd'hui. Une boucle qui recalcule l'equity et les pertes courantes depuis MT5 a chaque cycle reste a faire si le mode AUTO est utilise en argent reel sur une longue duree.
- Aucune modification du contenu requis par le gate lui-meme (`AutoValidationGate.evaluate`) : les criteres (backtest positif, hors-echantillon positif, drawdown sous limite, phases demo/shadow/manual avec des trades, preuves documentees) restent ceux deja definis dans `docs/auto-gate.md`.

## Criteres d'acceptation

- `AutoTradingLoop` ne peut pas etre instanciee si le gate ne vaut pas `ALLOW`.
- Une decision approuvee par le Risk Engine declenche un ordre reel via `ExecutionEngine.execute(..., RuntimeMode.AUTO)` sans intervention humaine.
- Le kill switch et pause fonctionnent exactement comme en MANUAL, depuis MT5 ou le web.
- La commande `auto-loop` refuse de demarrer -- sans se connecter a MT5 -- si `--gate-evidence` ne prouve pas que toutes les conditions du gate sont remplies.
- Aucun ordre ne part jamais sans SL, sans validation du Risk Engine, ni en dehors du sizing calcule (`RiskDecision.position_size`) : `AutoTradingLoop` ne fait que declencher l'execution d'une decision deja entierement validee, jamais autre chose.

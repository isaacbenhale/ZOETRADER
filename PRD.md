# PRD.md

## Resume

zoeTrading V1 est un systeme local de trading algorithmique pour MetaTrader 5. Il surveille Forex et indices synthetiques Deriv/MT5, analyse plusieurs timeframes, produit des decisions `BUY`, `SELL` ou `NO TRADE`, applique un Risk Engine non contournable, execute en mode MANUAL ou AUTO controle, suit les positions et journalise toutes les decisions.

## Objectifs V1

- Connecter le moteur Python a MT5 sur la meme machine Windows.
- Recuperer ticks, OHLC, spread, volume/tick disponible et etat des symboles.
- Analyser structure, tendance, momentum, volatilite, regimes et multi-timeframe.
- Implementer des strategies deterministes initiales et testables.
- Produire une proposition normalisee avec score, raisons, blockers, entree, invalidation, SL, TP et RR.
- Calculer sizing, limites et validation finale dans un Risk Engine independant.
- Supporter les modes `OFF`, `MONITORING`, `MANUAL` et `AUTO`.
- Fournir un EA MQL5 compagnon pour etat, approbation, rejet, kill switch et annotations.
- Journaliser signaux, refus, ordres, positions, modifications, slippage, spread et resultats dans SQLite.
- Valider le systeme par tests, backtests, demo, shadow mode et criteres quantitatifs.

## Non-objectifs V1

- Garantir un profit ou une absence de pertes.
- Migrer immediatement vers AWS ou une architecture cloud.
- Dependendre d'un LLM distant pour les calculs critiques.
- Utiliser martingale ou recovery automatique.
- Activer AUTO reel sans validation formelle, quelle que soit l'interface utilisee.
- Exposer une interface web sur le reseau, ou lui permettre de contourner le Risk Engine.

## Interface web locale (decision de portee, 2026-08-20)

Le non-objectif initial "construire un dashboard web" est leve a la demande explicite de l'utilisateur. Une interface web est ajoutee a la V1, sous conditions non negociables :

- Strictement locale : le serveur ecoute par defaut sur `127.0.0.1`, jamais expose sur le reseau sans action explicite et documentee.
- Lecture et lancement : elle peut afficher l'etat, les decisions journalisees et les rapports de backtest, et declencher `bootstrap` / `healthcheck` / `scan-once` / `backtest`.
- Aucune autorite d'execution AUTO : elle ne peut jamais activer AUTO ni contourner le Risk Engine. Voir l'amendement ci-dessous pour l'approbation MANUAL.
- Le document de conception (`Document/zoeTrading_Document_Final_Conception.docx`, section 2) liste encore le dashboard web comme non inclus en V1 : cette section est desormais obsolete et remplacee par la presente decision. Le fichier .docx n'a pas ete modifie automatiquement pour eviter de corrompre sa mise en forme (tableaux) lors d'une conversion automatisee ; une mise a jour manuelle du document source est recommandee si besoin d'un support figé a jour.

## Amendement : approbation MANUAL depuis l'interface web (2026-08-20)

A la demande explicite de l'utilisateur, apres explication du compromis (un bouton web est plus expose qu'un clic physique sur la machine connectee au broker), l'interface web peut desormais approuver, rejeter, mettre en pause et declencher le kill switch pour le mode MANUAL. Conditions qui restent non negociables :

- Le bouton web n'ajoute aucune nouvelle logique d'execution : il ecrit dans le meme fichier de commande que l'EA MT5 (`zoetrading_command.csv`), lu par le meme `ManualApprovalLoop` deja teste, avec la meme verification stricte que le clic correspond au `decision_id` actuellement affiche.
- Le Risk Engine a deja approuve la decision avant qu'elle soit affichee ; le bouton APPROVE ne fait que declencher l'envoi de l'ordre deja valide, jamais un contournement.
- `AUTO` reste totalement inatteignable depuis l'interface web : aucun endpoint ne peut l'activer, `ManualApprovalLoop` n'appelle jamais que `RuntimeMode.MANUAL`.
- Le panneau MT5 (EA compagnon) reste fonctionnel et peut toujours etre utilise en parallele ou a la place de l'interface web ; les deux ecrivent dans le meme fichier, aucune des deux n'a priorite architecturale sur l'autre.

## Utilisateurs et modes

### MONITORING

Le systeme analyse les marches et journalise les signaux, mais ne peut envoyer aucun ordre.

### MANUAL

Le systeme propose des signaux valides par le Risk Engine. L'utilisateur approuve ou rejette depuis MT5. Les decisions sont journalisees.

### AUTO

Le systeme execute automatiquement les signaux qui passent les controles. Le Risk Engine, le kill switch, les limites de perte et les controles d'idempotence restent actifs.

## Exigences fonctionnelles

### Market Data

- Connexion au terminal MT5 local.
- Cache de bougies par instrument et timeframe.
- Fraicheur obligatoire avant decision ou execution.
- Detection des interruptions de connexion, symboles indisponibles et donnees anormales.

### Analyse

- Swings, HH/HL, LH/LL, BOS, ranges, breakouts, retests.
- Supports, resistances et zones d'invalidation.
- Biais multi-timeframe avec context/setup/timing configurables.
- Momentum et volatilite : RSI, MACD, ROC, moyennes, ATR lorsque pertinents.
- Regimes : `TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `BREAKOUT`, `HIGH_VOLATILITY`, `LOW_VOLATILITY`, `CHAOTIC`.

### Strategies et decision

- Strategies modulaires par famille d'instrument.
- Filtrage par regime avant scoring.
- Decision normalisee incluant action, strategie, score, raisons, blockers, entree, invalidation, SL, TP, RR et configuration associee.
- Anti-double-comptage lorsque plusieurs strategies reposent sur les memes facteurs.

### Risk Engine

- Risque par trade parametre initialement autour de 0,25 % a 0,50 %.
- Limites de perte journaliere et hebdomadaire.
- Limite de positions simultanees.
- RR minimal par strategie.
- Cooldown apres pertes consecutives.
- SL obligatoire.
- Martingale interdite.

### Execution

- Validation connexion, spread, prix, volume, symbole, doublon et limites.
- Envoi ordre MT5 avec SL initial lorsque possible.
- Idempotence par identifiant unique de decision/ordre.
- Reconciliation du resultat serveur et journalisation.

### Monitoring de position

- Reevaluation continue du scenario.
- Trailing fixe, ATR ou structurel selon strategie.
- Break-even et prises partielles uniquement selon regles testees.
- Sortie anticipee si invalidation, retournement ou degradation validee.

### Interface MT5

- Etat `RUNNING`, `PAUSED`, `ERROR`.
- Mode `MANUAL` ou `AUTO`.
- Dernier signal, strategie, regime, score, entree, SL, TP, risque.
- Boutons `APPROVE`, `REJECT`, `PAUSE`, `KILL SWITCH`.
- Lignes Entry/SL/TP et annotations graphiques.
- P&L journalier, exposition et positions ouvertes.

### Journalisation et analytics

- Signaux executes et refuses.
- Etat des indicateurs et de la structure au moment de la decision.
- Entrees, sorties, modifications SL/TP, slippage, spread, resultat.
- R-multiple, MFE, MAE, duree et raison de sortie.
- Statistiques par instrument, strategie, timeframe, heure et regime.

## Exigences non fonctionnelles

- Performance mesuree sur les timeframes vises.
- Erreur instrument isolee sans arret global du scanner.
- Decisions reconstructibles.
- Strategies et regles de risque testables independamment.
- Parametres modifiables sans changer le code.
- Logs structures, heartbeat et etat visible dans MT5.
- Secrets hors depot.

## Criteres d'acceptation V1

- Le systeme demarre depuis un point d'entree unique.
- La connexion MT5 locale fonctionne.
- Plusieurs instruments sont surveilles sans bloquer le monitoring des positions.
- Chaque signal contient action, strategie, score, justification, entree, invalidation, SL, objectif et risque.
- Le Risk Engine peut refuser toute proposition.
- Le mode MANUAL permet `APPROVE` / `REJECT` depuis MT5.
- Le mode AUTO execute seulement les signaux valides.
- Le kill switch empeche immediatement les nouvelles entrees.
- Toutes les decisions et operations sont journalisees.
- Le systeme fonctionne en demo et shadow mode avant toute utilisation reelle.
- Le passage VPS ne modifie pas la logique metier.


# CLAUDE.md

## Role attendu

Tu contribues au projet zoeTrading comme assistant de conception et de developpement. Ton objectif est de produire un systeme de trading algorithmique local, prudent, testable et auditable, conforme au document de conception situe dans `Document/zoeTrading_Document_Final_Conception.docx`.

## Contexte produit

zoeTrading surveille plusieurs instruments, analyse plusieurs timeframes, detecte des configurations de marche, calcule le risque, propose ou execute des positions, puis gere activement les sorties. MetaTrader 5 reste l'interface operationnelle principale. La V1 fonctionne localement sur laptop Windows avant toute migration VPS.

## Comportement attendu

- Lire `AGENTS.md`, `VISION.md`, `PRD.md` et les taches `.md` pertinentes avant de modifier le code.
- Travailler directement sur `main` et pousser sur `main` lorsque l'utilisateur le demande.
- Ne pas introduire de workflow branches/PR sauf demande explicite.
- Pour chaque task implementee, ajouter `Statut : IMPLEMENTEE` en debut du fichier de task.
- Apres chaque implementation de task, commit et push directement sur `main`.
- Respecter la separation analyse / decision / risque / execution / monitoring / journal.
- Refuser toute implementation qui contourne le Risk Engine.
- Ne jamais presenter un score de setup comme une probabilite de gain.
- Conserver `NO TRADE` comme issue normale et mesurable.
- Prioriser le mode `MONITORING` puis `MANUAL`; `AUTO` arrive seulement apres validation.
- Documenter toute hypothese qui affecte le trading reel.

## Contraintes de securite

- Pas de secrets dans le depot.
- Pas de martingale.
- Pas d'ordre sans SL ou invalidation.
- Pas de dependance a un LLM distant pour les decisions rapides ou critiques.
- Pas de passage AUTO reel sans criteres quantitatifs documentes.
- Pas de logique metier differente entre laptop local et VPS.

## Style de contribution

- Faire des changements petits, coherents et testables.
- Ajouter des tests avant ou avec les modules critiques.
- Preferer des schemas de donnees explicites pour les signaux, decisions, ordres et journaux.
- Journaliser les signaux executes et refuses.
- Toujours penser aux cas d'erreur MT5 : connexion perdue, symbole indisponible, spread anormal, doublon, volume invalide, ordre rejete.

## Questions a clarifier si bloque

- Broker et symboles exacts exposes dans MT5.
- Timeframes actifs pour la premiere strategie.
- Capital de reference et limites de risque initiales.
- Mode de communication entre Python et l'EA MQL5 si l'API Python MT5 ne suffit pas.
- Criteres quantitatifs minimaux pour autoriser le mode AUTO.

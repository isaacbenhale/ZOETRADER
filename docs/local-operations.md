# Exploitation locale Windows

La V1 fonctionne d'abord sur laptop Windows, sans VPS obligatoire.

## Demarrage

1. Ouvrir MetaTrader 5.
2. Verifier la connexion au compte demo ou reel controle.
3. Lancer `scripts/start-local.ps1 -Mode MONITORING`.
4. Passer a `MANUAL` uniquement lorsque les signaux sont observables et journalises.

## Arret

Lorsque le moteur Python ou le laptop est arrete, aucune nouvelle logique locale ne tourne. Les SL/TP deja transmis au broker peuvent rester actifs cote broker, mais trailing, sorties dynamiques et nouvelles entrees cessent.

## Phases

- Demo : aucune exposition reelle.
- Shadow mode : decisions temps reel sans execution.
- MANUAL : approbation humaine requise.
- Micro-exposition : uniquement apres criteres de validation.

## Sauvegarde

Utiliser `scripts/backup-local.ps1` pour copier la base SQLite et les configs.


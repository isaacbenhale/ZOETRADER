# Planning zoeTrading

Ce dossier decoupe la construction de zoeTrading en taches progressives. Les taches sont ordonnees pour produire d'abord un noyau local testable, puis les strategies, le risque, l'execution, le monitoring, l'interface MT5 et enfin la validation vers AUTO.

Workflow Git : travailler directement sur `main` et pousser sur `main` apres chaque implementation de task. Pas de branches ni PR sauf demande explicite. Chaque task implementee doit indiquer son statut en debut de fichier.

## Ordre recommande

1. `01-bootstrap-repo.md`
2. `02-config-domain-models.md`
3. `03-mt5-market-data.md`
4. `04-journal-sqlite.md`
5. `05-analysis-engine.md`
6. `06-regime-mtf.md`
7. `07-strategy-engine.md`
8. `08-risk-engine.md`
9. `09-decision-engine.md`
10. `10-execution-engine.md`
11. `11-position-monitor.md`
12. `12-mt5-ea-companion.md`
13. `13-backtesting-validation.md`
14. `14-local-operations.md`
15. `15-auto-gate-vps-readiness.md`
16. `16-strategy-library-completion.md`
17. `17-strategy-library-backtest-runner.md`
18. `18-local-web-ui.md`
19. `19-manual-approval-execution.md`
20. `20-web-manual-approval-and-resume.md`
21. `21-auto-mode-execution.md`

## Gates

- Gate A : fondation locale testable apres tache 4.
- Gate B : signaux explicables sans execution apres tache 9.
- Gate C : MANUAL exploitable apres tache 12.
- Gate D : AUTO local controle apres tache 14 et validation.
- Gate E : readiness VPS apres tache 15.

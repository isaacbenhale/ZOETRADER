# Gate AUTO

AUTO reel reste bloque tant que les preuves ne sont pas documentees.

Conditions minimales :

- backtest positif apres couts;
- validation hors-echantillon positive;
- drawdown sous limite documentee;
- phase demo realisee;
- shadow mode realise;
- phase MANUAL realisee;
- rollback vers MANUAL/MONITORING documente;
- aucun changement de strategie sans nouvelle validation.

Le Risk Engine reste obligatoire en AUTO.

## Fichier de preuves (`--gate-evidence`)

`python -m zoetrading.main auto-loop --gate-evidence <fichier.json> --equity <equity>` charge les preuves depuis un fichier JSON documente (`load_auto_gate_evidence`) et refuse de demarrer -- avant meme de se connecter a MT5 -- si `AutoValidationGate.evaluate(...)` ne vaut pas `ALLOW`. Format attendu :

```json
{
  "backtest": {
    "trades": 30, "win_rate": 0.55, "expectancy": 0.2, "profit_factor": 1.4,
    "max_drawdown": 2.0, "average_win": 1.0, "average_loss": -0.7, "mfe": 1.3, "mae": -0.6
  },
  "out_of_sample": { "...": "meme structure que backtest" },
  "demo_trades": 10,
  "shadow_trades": 10,
  "manual_trades": 10,
  "max_allowed_drawdown": 3.0,
  "documented": true
}
```

`backtest` et `out_of_sample` viennent typiquement du `report_file` produit par `python -m zoetrading.main backtest`. `demo_trades`, `shadow_trades` et `manual_trades` doivent refleter des phases reellement executees (pas des estimations). `documented: true` est une declaration explicite que l'operateur atteste que ces preuves sont reelles et tracables -- ce n'est pas une simple case a cocher technique.

Une fois `AUTO` demarre, `python -m zoetrading.main auto-loop` execute automatiquement chaque decision approuvee par le Risk Engine, sans clic. `KILL_SWITCH`, `PAUSE`, `RESUME` et `REJECT` (veto d'une decision precise) restent disponibles depuis le panneau MT5 ou l'interface web, exactement comme en MANUAL -- voir `zoetrading/runtime/auto_loop.py` et `tasks/21-auto-mode-execution.md`.


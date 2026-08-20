# Guide d'utilisation complet

Ce guide couvre toutes les etapes, de l'installation jusqu'a l'usage quotidien, pour faire tourner zoeTrading sur un laptop Windows avec MetaTrader 5.

Ordre logique a respecter : `bootstrap` -> `healthcheck` -> `backtest` (mesurer) -> `scan MONITORING` (observer, plusieurs jours) -> `scan MANUAL` (approuver a la main) -> seulement ensuite penser a `AUTO`. Ne saute pas d'etape.

## 0. Prerequis

- Laptop Windows avec MetaTrader 5 installe et un compte (demo pour commencer) deja connecte.
- Python 3.11+ installe sur cette meme machine (le moteur doit tourner sur la machine ou MT5 est ouvert).
- Le depot clone sur ce laptop Windows (pas seulement sur une autre machine : MT5 et le package `MetaTrader5` sont Windows-only).
- Optionnel : Node.js si tu veux modifier le frontend de l'interface web (le build est deja commite, donc pas obligatoire pour l'utiliser).

## 1. Installation

Si le depot est deja clone sur ce laptop, recupere d'abord les derniers changements :

```powershell
cd chemin\vers\ZOETRADER
git pull origin main
```

Puis, dans un terminal PowerShell, a la racine du depot :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[mt5,ui]"
```

`mt5` installe le package `MetaTrader5`. `ui` installe `fastapi`/`uvicorn` pour l'interface web locale. Ajoute `.[dev]` en plus si tu veux `pytest`/`ruff`.

## 2. Configuration des secrets

```powershell
copy .env.example .env
```

Edite `.env` et renseigne :

```
MT5_LOGIN=ton_numero_de_compte
MT5_PASSWORD=ton_mot_de_passe
MT5_SERVER=nom_du_serveur_broker
MT5_PATH=   (optionnel, chemin vers terminal64.exe si besoin)
```

`.env` est dans `.gitignore` : il ne sera jamais commite. **Commence avec un compte demo.**

## 3. Configuration du trading

Trois fichiers dans `config/` a ajuster selon ton besoin (deja pre-remplis avec des valeurs raisonnables) :

- `config/instruments.yaml` : les symboles surveilles (adapte les noms exacts a ton broker, ex. `Volatility 75 Index` peut varier).
- `config/risk.yaml` : risque par trade (0,50 %), limites de perte, RR minimal par strategie.
- `config/settings.yaml` : mode par defaut (`MONITORING`), timeframes.

Ne touche pas `martingale: false` ni `stop_loss_required: true` : le systeme refuse de demarrer sinon.

## 4. Verification de base (sans MT5)

```powershell
python -m zoetrading.main bootstrap
```

Doit afficher `mode=MONITORING`, `orders_enabled=false`, `config_loaded=true`. Si ca echoue, c'est un probleme de config avant meme de toucher MT5.

## 5. Installer le panneau MT5 (EA compagnon)

1. Ouvre MT5 -> **Fichier > Ouvrir le dossier des donnees**.
2. Copie `mt5/ZoeTradingEA.mq5` dans `MQL5/Experts/`.
3. Dans MetaEditor, ouvre le fichier et compile (F7).
4. Dans MT5, glisse `ZoeTradingEA` sur un graphique (n'importe quel symbole surveille). Le panneau affiche l'etat, le dernier signal, et les boutons **APPROVE / REJECT / KILL**.
5. **Verifie que le bouton "Algo Trading" (ou "AutoTrading") est active dans MT5** -- sans ca, l'EA ne s'execute pas du tout (pas de timer, pas de lecture de fichier).

### Important : ou se trouve le fichier de statut

L'EA lit/ecrit via le dossier **partage** MT5 (`FILE_COMMON`), commun a tous les terminaux installes sur la machine :

```
%APPDATA%\MetaQuotes\Terminal\Common\Files\
```

C'est un chemin fixe, independant du terminal precis. Python (non sandboxe) doit ecrire son fichier de statut **exactement a cet endroit** pour que l'EA le trouve. Passe donc `--status-file` en pointant vers ce dossier a chaque scan, par exemple :

```powershell
python -m zoetrading.main scan-once --mode MONITORING --equity 10000 --status-file "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_status.csv"
```

Si tu ne passes pas ce chemin (ou si tu utilises l'ancien defaut `data/zoetrading_status.csv`), le fichier existe bien cote Python mais **l'EA ne le voit jamais** -- le panneau reste bloque sur "NO SIGNAL / PAUSED" sans erreur visible. C'est le probleme le plus courant si "rien ne s'affiche dans MT5".

Passe de meme `--command-file` vers ce dossier pour tout ce qui touche l'approbation (etape 9).

## 6. Healthcheck MT5

Avec MT5 ouvert et connecte :

```powershell
python -m zoetrading.main healthcheck
```

Verifie la connexion et que les symboles de `instruments.yaml` sont disponibles chez ton broker. Corrige les noms de symboles si erreur.

## 7. Mesurer les strategies (backtest) -- avant tout le reste

```powershell
.\scripts\start-local.ps1 -Action backtest
```

Telecharge l'historique reel de chaque instrument, teste les 7 strategies dessus, et affiche un tableau trie par expectancy. Le detail complet est ecrit dans `data/backtest_report.json`.

**Lecture des resultats** :

- `expectancy > 0` et `profit_factor > 1` = la combinaison a un edge historique mesure.
- `expectancy <= 0` = ne pas faire progresser cette combinaison vers la suite. Ce ne sont que des chiffres passes, jamais une promesse de resultat futur.
- Regarde aussi `trades` : moins de ~30 trades, la mesure est peu fiable statistiquement.

## 8. Mode MONITORING (observer sans risque)

```powershell
.\scripts\start-local.ps1 -Action scan -Mode MONITORING -Equity 10000 -StatusFile "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_status.csv"
```

Lance un scan unique : analyse, genere des decisions, journalise dans `data/trading.db`, mais **ne peut envoyer aucun ordre**. Le `-StatusFile` pointant vers `Common\Files` (voir etape 5) est ce qui permet au panneau MT5 de voir le resultat. Repete ce scan regulierement (manuellement ou via une tache planifiee Windows) pendant plusieurs jours/semaines pour observer les signaux avant de faire confiance au systeme.

## 9. Mode MANUAL (approbation humaine, avec execution reelle)

Une fois que MONITORING tourne proprement, utilise `approve-loop` (pas `scan -Mode MANUAL`) : c'est la seule commande qui attend ton clic MT5 et envoie reellement l'ordre si tu approuves.

```powershell
.\scripts\start-local.ps1 -Action approve-loop -Equity 10000 -StatusFile "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_status.csv" -CommandFile "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_command.csv"
```

Ce que ca fait, en boucle jusqu'a Ctrl+C :

1. Lance un scan MANUAL. S'il y a une proposition de trade, le panneau MT5 l'affiche (entree, SL, TP, score, regime) avec les lignes de prix et la fleche BUY/SELL sur le graphique.
2. Attend jusqu'a 120 secondes (`-ApprovalTimeout` pour changer) que tu cliques **APPROVE** ou **REJECT** dans MT5.
3. **APPROVE** -> envoie reellement l'ordre via le Risk Engine deja valide, journalise le resultat. **REJECT** -> rien n'est envoye. Pas de clic -> timeout, rien n'est envoye.
4. **KILL** -> arrete immediatement toute nouvelle proposition pour le reste de la session (relance le processus pour reprendre). **PAUSE** -> arrete proprement la boucle.
5. Recommence apres le delai configure (`market.refresh_interval_seconds` dans `settings.yaml`).

Un clic ne peut jamais s'appliquer a une proposition perimee : chaque commande porte l'identifiant exact de la decision affichee, et un identifiant different est ignore plutot qu'execute.

## 10. Interface web locale (suivi visuel)

```powershell
python -m zoetrading.main ui --status-file "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_status.csv"
```

ou via le script :

```powershell
.\scripts\start-local.ps1 -Action ui -StatusFile "$env:APPDATA\MetaQuotes\Terminal\Common\Files\zoetrading_status.csv"
```

Ouvre `http://127.0.0.1:8765` dans le navigateur. Le serveur n'ecoute que sur `127.0.0.1` par defaut, jamais expose reseau. Tu y trouves :

- L'etat courant (mode, dernier signal, compteurs journal), rafraichi automatiquement.
- Des boutons pour lancer Bootstrap / Healthcheck / Scan / Backtest depuis le navigateur.
- Le tableau des decisions recentes et le dernier rapport de backtest.

Cette interface est strictement **lecture et lancement** : elle ne peut ni approuver un ordre, ni activer AUTO, ni contourner le Risk Engine. L'approbation MANUAL et le kill switch restent exclusivement dans le panneau MT5 (etape 9). Voir `PRD.md`, section "Interface web locale", pour le detail des contraintes.

## 11. Consulter le journal

Toutes les decisions (executees et refusees) sont dans `data/trading.db` (SQLite). Pour l'inspecter :

```powershell
sqlite3 data/trading.db "select * from decisions order by created_at desc limit 20;"
```

(ou ouvre le fichier avec DB Browser for SQLite si tu preferes une interface graphique). L'onglet decisions de l'interface web (etape 10) fait la meme chose visuellement.

## 12. Sauvegarde

```powershell
.\scripts\backup-local.ps1
```

Copie `data/trading.db` et `config/` vers un dossier de backup. A faire regulierement, surtout avant de changer de config.

## 13. La suite (ne pas bruler les etapes)

Le passage a `AUTO` reel est **bloque par construction** (`AutoValidationGate`, voir `docs/auto-gate.md`) tant que tu n'as pas documente : backtest positif, validation hors-echantillon positive, phase demo faite, shadow mode fait, phase MANUAL faite. Pas de raccourci possible sans modifier le code, et ce garde-fou est volontaire.

## Tests (sur n'importe quelle machine, sans MT5)

```bash
python -m unittest discover -s tests
```

ou, avec les dependances de developpement installees :

```bash
pytest
```

Ces tests utilisent un client MT5 factice : ils valident toute la logique (strategies, risque, decision, journal, backtest, API web) sans terminal MT5 installe. Ils ne remplacent pas un vrai test sur compte demo (etapes 6 a 10).

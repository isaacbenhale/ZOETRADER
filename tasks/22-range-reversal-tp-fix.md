# 22 - Correction range_reversal : TP invalide quand la structure de range est degeneree

Statut : IMPLEMENTEE

## Objectif

Corriger un bug reel decouvert en observant une vraie proposition MANUAL sur compte demo Deriv : `range_reversal` a produit un signal BUY EURUSD avec `SL == TP`, et TP en dessous du prix d'entree -- un take profit qui garantit une perte, pas un gain.

## Contexte

Capture d'ecran de l'utilisateur (approve-loop reel, EURUSD, score 80) : `entry=1.16847, sl=1.16834, tp=1.16834`. Racine du probleme dans `zoetrading/strategies/range_reversal.py` : la resistance utilisee pour plafonner le take profit d'un BUY (`resistance = min(resistances, key=lambda level: abs(entry - level.price))`) etait choisie par proximite, sans verifier qu'elle se trouve bien au-dessus de l'entree. Meme defaut symetrique cote SELL avec le support. Quand le range detecte est degenere (ex. une ancienne resistance d'un niveau de prix plus bas encore presente dans la fenetre de swings), le TP peut se retrouver plafonne en dessous de l'entree, voire en dessous du SL. Ce n'est pas rattrape par le Risk Engine : `expected_rr` vient du parametre configure de la strategie, pas d'un recalcul a partir des prix reels.

## Livrables

- `zoetrading/strategies/range_reversal.py` :
  - Le niveau utilise pour plafonner le take profit doit desormais se trouver du bon cote de l'entree (resistance strictement au-dessus pour un BUY, support strictement en dessous pour un SELL) ; si aucun niveau confirme n'existe de ce cote, la strategie retourne `NO_TRADE` (`"no confirmed range resistance/support above/below entry to target"`) plutot que d'inventer un objectif.
  - Garde-fou final avant d'emettre un signal : `stop_loss < entry < take_profit` pour un BUY, `stop_loss > entry > take_profit` pour un SELL. Si l'invariant echoue pour n'importe quelle raison, `NO_TRADE` (`"range reversal setup failed sl/tp sanity check"`). Ce filet de securite proprement dit protege contre toute autre cause future du meme symptome, pas seulement celle identifiee ici.
- Tests (`tests/test_strategies.py`) :
  - `test_range_reversal_returns_trade_near_range_edge` verifie desormais explicitement `sl < entry < tp`, pas seulement l'action.
  - `test_range_reversal_refuses_a_target_below_entry` (nouveau fixture `RANGE_NO_TARGET_ABOVE_ENTRY_CANDLES`) reproduit le cas degenere -- confirme qu'avant la correction ce fixture produisait `BUY sl=13.74 tp=10.4` (TP sous le SL) et qu'apres la correction il produit `NO_TRADE`.

## Criteres d'acceptation

- `range_reversal` ne peut plus emettre de signal BUY/SELL dont le TP est du mauvais cote de l'entree ou du SL, quelle que soit la cause.
- Aucune regression sur le comportement existant (`RANGE_CANDLES`, range bien forme, continue de produire BUY avec un TP au-dessus de l'entree).
- Le reste de la suite de tests (106 tests) passe sans modification ailleurs -- le Risk Engine, `ExecutionEngine` et `AutoTradingLoop` restent inchanges ; c'est bien la strategie qui ne doit jamais proposer un signal invalide, pas une couche en aval qui doit le rattraper.

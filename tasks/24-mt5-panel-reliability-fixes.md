# 24 - Fiabilite du panneau MT5 : ecriture atomique, boutons, fleches

Statut : IMPLEMENTEE

## Objectif

L'utilisateur a demande une verification approfondie du code EA/panneau pour tout ce qui pourrait "empecher que ca marche proprement sur le graphique". Revue systematique de `mt5/ZoeTradingEA.mq5` et du code Python qui alimente le fichier de statut/commande partage. Trois problemes reels trouves et corriges.

## Problemes trouves et corriges

1. **Ecriture non atomique du fichier de statut/commande (race condition reelle, reproduite).** `write_status_file`/`write_command_file` (`zoetrading/operations/mt5_status.py`) ecrivaient directement sur le fichier final. L'EA lit ce fichier toutes les 1s (timer) pendant que Python le reecrit a chaque cycle de scan -- un lecteur peut observer un fichier partiellement ecrit (ex. coupe juste apres `entry,`), ce qui desynchronise le parsing cle/valeur de l'EA et affiche des donnees incoherentes sur tout le panneau. **Reproduit** avec un test avant/apres (voir Livrables) : sur l'ancien code, un snapshot tronque a 7 champs au lieu de 11 apparaissait de facon deterministe sous lecture/ecriture concurrente. Corrige avec une ecriture atomique (fichier temporaire dans le meme dossier + `os.replace()`, atomique sur POSIX et Windows) : un lecteur ne voit jamais qu'un fichier complet, ancien ou nouveau.
2. **Boutons MT5 qui restent visuellement enfonces apres un clic.** `OBJ_BUTTON` ne reinitialise pas seul sa propriete `OBJPROP_STATE` apres un clic -- sans reset explicite dans `OnChartEvent`, un bouton peut rester affiche "enfonce" et ne plus declencher fiablement `CHARTEVENT_OBJECT_CLICK` a un clic suivant. Ajout du reset (`ObjectSetInteger(0, sparam, OBJPROP_STATE, false)`) apres traitement de chaque clic.
3. **Fleches BUY/SELL qui s'accumulent indefiniment sur le graphique.** Chaque nouvelle decision creait un objet fleche nomme par son `decision_id`, jamais supprime pendant le fonctionnement normal (`OnDeinit` ne nettoie qu'a la suppression complete de l'EA). Sur une session longue avec de nombreuses propositions, le graphique accumule une fleche par decision, sans fin. Corrige : les anciennes fleches sont supprimees (`ObjectsDeleteAll(0, PREFIX + "ARROW_")`) avant de dessiner la nouvelle.
4. **Comparaison de symbole par sous-chaine plutot qu'egalite exacte.** `SignalMatchesChart()` (task 23) utilisait `StringFind` sur tout le texte `"<action> <instrument>"`, un risque theorique de faux positif si un nom de symbole etait un jour un sous-ensemble d'un autre. Remplace par une comparaison exacte de l'instrument seul (`SignalInstrument()`, tout ce qui suit le premier espace dans `last_signal`).

## Livrables

- `zoetrading/operations/mt5_status.py` : `_write_atomic()` (fichier temp + `os.replace`), utilise par `write_status_file` et `write_command_file`.
- `mt5/ZoeTradingEA.mq5` (version 0.4 -> reste 0.4, correctifs internes) : reset d'etat des boutons, nettoyage des fleches, `SignalInstrument()`/comparaison exacte.
- `tests/test_mt5_status.py` (nouveau) : couverture de `write_status_file`, `write_command_file`/`read_command_file`/`consume_command_file`, et surtout `test_write_status_file_never_leaves_a_partially_written_file_under_concurrent_reads` -- un test multi-thread qui reproduisait de façon fiable la corruption sur l'ancien code (verifie manuellement) et passe sur le nouveau.

## Ce qui reste hors scope

- Le fichier de commande ecrit par l'EA (`WriteCommand`, cote MQL5) n'a pas d'ecriture atomique equivalente -- risque symetrique mais bien plus faible (ecrit uniquement sur un clic humain, rare, 3 lignes). Pas de mecanisme d'ecriture atomique natif simple en MQL5 sans complexite disproportionnee pour ce risque residuel.
- Aucun changement de logique de decision/risque/execution -- purement fiabilite du canal de communication Python <-> MT5 et de l'affichage du panneau.

## Criteres d'acceptation

- Le fichier de statut n'est jamais observe incomplet par un lecteur concurrent (verifie par test multi-thread).
- Les boutons du panneau restent cliquables de facon fiable a repetition.
- Le graphique ne conserve qu'une seule fleche de signal a la fois, jamais d'accumulation.
- La correspondance signal/graphique reste correcte pour tous les instruments configures (`config/instruments.yaml`), y compris ceux dont le nom contient des espaces.

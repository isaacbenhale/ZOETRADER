# VISION.md

## Vision

zoeTrading doit devenir un assistant de trading algorithmique modulaire capable d'observer les marches via MT5, de prendre des decisions explicables, de proteger le capital par un Risk Engine prioritaire et de mesurer objectivement la qualite de chaque strategie.

La premiere version vise un usage local sur laptop Windows : l'utilisateur lance MT5, lance le moteur Python, observe les signaux, valide manuellement les entrees, puis passe progressivement a une automatisation controlee si les resultats le justifient.

## Ambition

Produire un systeme qui ne cherche pas a "deviner" le marche, mais a executer une discipline mesurable :

- analyser plusieurs instruments rapidement;
- separer contexte, setup et timing;
- detecter les regimes de marche;
- activer uniquement les strategies compatibles;
- refuser les opportunites faibles ou mal cadrees;
- dimensionner le risque automatiquement;
- suivre les positions jusqu'a invalidation, sortie dynamique, TP ou SL;
- apprendre des journaux plutot que des impressions.

## Public cible

Le premier utilisateur est le proprietaire du projet, avec un usage local et controle. Le systeme doit rester comprehensible et inspectable. MT5 reste l'interface d'exploitation de reference (approbation MANUAL, kill switch) ; une interface web strictement locale (127.0.0.1, lecture et lancement uniquement, sans autorite d'execution) complete le suivi.

## Differenciation

zoeTrading se distingue par la combinaison de quatre exigences :

- Prudence : le risque decide en dernier.
- Auditabilite : chaque decision est reconstruisible.
- Progressivite : MONITORING puis MANUAL puis AUTO controle.
- Portabilite : meme logique metier entre laptop local et VPS Windows.

## Ce que la V1 n'est pas

- Ce n'est pas une promesse de profit.
- Ce n'est pas un robot martingale.
- Ce n'est pas un systeme opaque pilote par IA.
- Ce n'est pas un dashboard expose au reseau ou avec autorite d'execution.
- Ce n'est pas une architecture cloud complexe.

## Etoile polaire

Un mode AUTO n'a de valeur que s'il execute une strategie deja prouvee, avec un risque limite, des conditions d'arret claires et une trace complete de chaque choix.


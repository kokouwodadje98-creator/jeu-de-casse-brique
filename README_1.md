# Brise-Briques

Projet de session, 420-LAP-OS Langage de programmation II, automne 2026

## Équipe

| Membre | Compte GitHub |
|---|---|
| Seydouba Camara  | https://github.com/seydouba-camara |
| Ndeye Sokhna Diaw |https://github.com/diawndeyesokhna1-code|
| Kokou Yohanes Mesmin |https://github.com/kokouwodadje98-creator|

## Comment lancer le jeu

```
python main.py
```

Aucune bibliothèque à installer : le jeu utilise seulement tkinter, json, math, random et os, qui viennent avec Python.

## Règles du jeu

Brise-Briques est un casse-briques. On déplace la raquette avec les flèches ← et → et on lance la balle avec la barre d'espace. La balle rebondit sur les murs et sur la raquette (elle repart plus à gauche ou plus à droite selon l'endroit touché) et casse les briques :

- **rouge** (normale) : 1 coup, 10 points ;
- **grise** (solide) : 3 coups, 30 points, elle pâlit à chaque coup ;
- **jaune** (bonus) : 1 coup, 20 points, et donne une vie de plus ou une raquette plus large jusqu'à la fin du niveau.

Quand toutes les briques sont cassées, on passe au niveau suivant : une rangée de plus, plus de briques solides et une balle plus rapide. On commence avec 3 vies et on en perd une chaque fois que la balle passe sous la raquette. On gagne en terminant le niveau 3 ; on perd à 0 vie.

| Touche | Action |
|---|---|
| ← → | Déplacer la raquette |
| Espace | Lancer la balle, puis pause / reprise |
| Échap | Sauvegarder la partie et revenir au menu |

Les 5 meilleurs scores sont gardés dans `scores.json`. La partie en cours est gardée dans `partie.json` quand on appuie sur Échap ou qu'on ferme la fenêtre ; le bouton Continuer du menu la reprend.

## Qui a fait quoi

| Membre | Classes et fichiers | Partie de l'interface |
|---|---|---|
| Ndeye Sokhna Diaw / Seydouba Camara| `Balle`, `Raquette` (objets.py) ; `Brique`, `BriqueSolide`, `BriqueBonus` (briques.py) | Zone de jeu : Canvas, `dessiner()`, boucle `after()`, touches ← → Espace |
| Kokou Yohanes / Seydouba Camara| `Partie` (partie.py) ; `TableauScores` et sauvegarde JSON (scores.py) ; main.py | Écran d'accueil, barre score/vies/niveau, écran de fin avec le top 5, sauvegarde à la fermeture |

## Changements depuis le diagramme UML

- **Raquette** : ajout de `hauteur : int` et de `centre()`, utiles pour les collisions et pour placer la balle.
- **Partie** : ajout de `replacer_balle()`, `perdre_vie()`, `touche_brique(brique)` et `rebondir_sur(brique)`, pour garder `avancer()` et `verifier_collisions()` courtes.
- **Sauvegarde** : comme au cours 9, les fonctions hors classe `partie_depuis_dict()`, `sauvegarder_partie()`, `charger_partie()`, `effacer_partie()` (partie.py) et `brique_depuis_dict()` (briques.py) refont les objets à partir du JSON. `BriqueSolide` et `BriqueBonus` redéfinissent aussi `vers_dict()` pour noter leur type.
- **Fenetre** : ajout de `ecran` et `id_boucle` (pour ne jamais avoir deux boucles en même temps), et des méthodes `creer_menu()`, `creer_jeu()`, `creer_fin()`, `creer_scores()`, `montrer()`, `afficher_scores()`, `echap()`, `valider_nom()`, `rafraichir_barre()`, `arreter_boucle()`, `lancer()`.
- **Balle** : la vitesse dépend du niveau dans `Partie.lancer_balle()` ; `accelerer()` existe mais n'est pas utilisée pour l'instant.

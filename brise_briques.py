"""Brise-Briques, en un seul fichier.

Lancer avec :  python brise_briques.py

Les sections suivent les classes du diagramme UML :
objets (Balle, Raquette), briques (Brique, BriqueSolide, BriqueBonus),
partie (Partie et sauvegarde), scores (TableauScores) et fenetre (Fenetre,
la seule partie qui utilise tkinter).
"""

import json
import math
import os
import random
import tkinter as tk

# ======================================================================
# OBJETS : la balle et la raquette
# ======================================================================
class Raquette:
    def __init__(self, x, y, largeur=100, vitesse=25):
        self.x = x              # coin gauche, en pixels
        self.y = y              # haut de la raquette
        self.largeur = largeur
        self.hauteur = 12
        self.vitesse = vitesse  # pixels par appui sur une flèche

    def deplacer(self, dx, largeur_ecran):
        """Déplace la raquette sans la faire sortir de l'écran."""
        nouveau_x = self.x + dx
        if nouveau_x < 0:
            nouveau_x = 0
        if nouveau_x + self.largeur > largeur_ecran:
            nouveau_x = largeur_ecran - self.largeur
        self.x = nouveau_x

    def centre(self):
        return self.x + self.largeur / 2

    def touche(self, balle):
        """Vrai si la balle descend et touche le dessus de la raquette."""
        if balle.dy <= 0:
            return False
        bas_balle = balle.y + balle.rayon
        dans_la_hauteur = self.y <= bas_balle <= self.y + self.hauteur + balle.rayon
        dans_la_largeur = self.x - balle.rayon <= balle.x <= self.x + self.largeur + balle.rayon
        return dans_la_hauteur and dans_la_largeur

    def elargir(self):
        """Effet de la brique bonus : 40 pixels de plus, 180 au maximum."""
        self.largeur = min(180, self.largeur + 40)

    def vers_dict(self):
        return {"x": self.x, "largeur": self.largeur}


class Balle:
    def __init__(self, x, y, rayon=8):
        self.x = x
        self.y = y
        self.rayon = rayon
        self.dx = 0.0
        self.dy = 0.0

    def avancer(self):
        self.x = self.x + self.dx
        self.y = self.y + self.dy

    def rebondir_x(self):
        self.dx = -self.dx

    def rebondir_y(self):
        self.dy = -self.dy

    def accelerer(self, facteur=1.1):
        self.dx = self.dx * facteur
        self.dy = self.dy * facteur


# ======================================================================
# BRIQUES : une classe parent et deux classes enfants
# ======================================================================
class Brique:
    """Brique normale (rouge) : 1 coup, 10 points."""

    def __init__(self, x, y, largeur, hauteur, resistance=1, points=10):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.resistance = resistance  # nombre de coups qu'il reste à donner
        self.points = points

    def recevoir_coup(self):
        """Enlève un coup. Retourne les points gagnés (0 si la brique tient encore)."""
        self.resistance = self.resistance - 1
        if self.est_detruite():
            return self.points
        return 0

    def est_detruite(self):
        return self.resistance <= 0

    def couleur(self):
        return "#E74C3C"

    def vers_dict(self):
        return {
            "type": "normale",
            "x": self.x,
            "y": self.y,
            "largeur": self.largeur,
            "hauteur": self.hauteur,
            "resistance": self.resistance,
        }


class BriqueSolide(Brique):
    """Brique grise : 3 coups, 30 points. Elle pâlit à chaque coup."""

    def __init__(self, x, y, largeur, hauteur):
        super().__init__(x, y, largeur, hauteur, 3, 30)
        self.resistance_max = 3

    def couleur(self):
        if self.resistance >= 3:
            return "#566573"
        if self.resistance == 2:
            return "#839192"
        return "#BFC9CA"

    def vers_dict(self):
        d = super().vers_dict()
        d["type"] = "solide"
        return d


class BriqueBonus(Brique):
    """Brique jaune : 1 coup, 20 points, et un effet ("vie" ou "large")."""

    def __init__(self, x, y, largeur, hauteur, effet):
        super().__init__(x, y, largeur, hauteur, 1, 20)
        self.effet = effet

    def couleur(self):
        return "#F1C40F"

    def appliquer_effet(self, partie):
        if self.effet == "vie":
            partie.vies = partie.vies + 1
        else:
            partie.raquette.elargir()

    def vers_dict(self):
        d = super().vers_dict()
        d["type"] = "bonus"
        d["effet"] = self.effet
        return d


def brique_depuis_dict(d):
    """Refait le bon type de brique à partir d'un dictionnaire lu dans le JSON."""
    if d["type"] == "solide":
        b = BriqueSolide(d["x"], d["y"], d["largeur"], d["hauteur"])
    elif d["type"] == "bonus":
        b = BriqueBonus(d["x"], d["y"], d["largeur"], d["hauteur"], d["effet"])
    else:
        b = Brique(d["x"], d["y"], d["largeur"], d["hauteur"])
    b.resistance = d["resistance"]
    return b


# ======================================================================
# PARTIE : la logique du jeu, sans tkinter
# ======================================================================
LARGEUR = 600         # taille de la zone de jeu, en pixels
HAUTEUR = 500
NIVEAU_MAX = 3
VIES_DEPART = 3
COLONNES = 8
LARGEUR_BRIQUE = 66
HAUTEUR_BRIQUE = 22
ESPACE = 6
HAUT_BRIQUES = 50     # y de la première rangée


class Partie:
    def __init__(self):
        self.raquette = Raquette(LARGEUR / 2 - 50, HAUTEUR - 40)
        self.balle = Balle(0, 0)
        self.briques = []
        self.score = 0
        self.vies = VIES_DEPART
        self.niveau = 1
        self.balle_lancee = False
        self.terminee = False
        self.nouveau_niveau()

    # ---------- les niveaux ----------

    def nouveau_niveau(self):
        """Construit les briques du niveau courant et remet la balle sur la raquette."""
        self.briques = []
        rangees = 3 + self.niveau                 # 4, 5 puis 6 rangées
        chance_solide = 0.10 * self.niveau        # plus de briques solides à chaque niveau
        marge = (LARGEUR - (COLONNES * LARGEUR_BRIQUE + (COLONNES - 1) * ESPACE)) / 2
        for rangee in range(rangees):
            for colonne in range(COLONNES):
                x = marge + colonne * (LARGEUR_BRIQUE + ESPACE)
                y = HAUT_BRIQUES + rangee * (HAUTEUR_BRIQUE + ESPACE)
                tirage = random.random()
                if tirage < 0.08:
                    effet = random.choice(["vie", "large"])
                    b = BriqueBonus(x, y, LARGEUR_BRIQUE, HAUTEUR_BRIQUE, effet)
                elif tirage < 0.08 + chance_solide:
                    b = BriqueSolide(x, y, LARGEUR_BRIQUE, HAUTEUR_BRIQUE)
                else:
                    b = Brique(x, y, LARGEUR_BRIQUE, HAUTEUR_BRIQUE)
                self.briques.append(b)
        self.raquette.largeur = 100
        self.raquette.x = LARGEUR / 2 - 50
        self.balle_lancee = False
        self.replacer_balle()

    def niveau_fini(self):
        return len(self.briques) == 0

    def est_gagnee(self):
        return self.terminee and self.vies > 0

    # ---------- les actions du joueur ----------

    def deplacer_raquette(self, dx):
        if self.terminee:
            return
        self.raquette.deplacer(dx, LARGEUR)
        if not self.balle_lancee:
            self.replacer_balle()

    def replacer_balle(self):
        """Pose la balle au milieu de la raquette, immobile."""
        self.balle.x = self.raquette.centre()
        self.balle.y = self.raquette.y - self.balle.rayon - 1
        self.balle.dx = 0.0
        self.balle.dy = 0.0

    def lancer_balle(self):
        if self.balle_lancee or self.terminee:
            return
        self.balle_lancee = True
        vitesse = 4 + self.niveau                 # la balle va plus vite à chaque niveau
        self.balle.dx = random.choice([-1, 1]) * vitesse * 0.5
        self.balle.dy = -vitesse

    # ---------- un pas de jeu (appelé toutes les 20 ms par la fenêtre) ----------

    def avancer(self):
        if self.terminee or not self.balle_lancee:
            return
        self.balle.avancer()
        self.verifier_collisions()

        if self.balle.y - self.balle.rayon > HAUTEUR:
            self.perdre_vie()
        elif self.niveau_fini():
            if self.niveau == NIVEAU_MAX:
                self.terminee = True             # victoire
            else:
                self.niveau = self.niveau + 1
                self.nouveau_niveau()

    def perdre_vie(self):
        self.vies = self.vies - 1
        if self.vies <= 0:
            self.terminee = True                 # défaite
        else:
            self.balle_lancee = False
            self.replacer_balle()

    def verifier_collisions(self):
        b = self.balle
        r = b.rayon

        # les murs et le plafond
        if b.x - r <= 0:
            b.x = r
            b.dx = abs(b.dx)
        elif b.x + r >= LARGEUR:
            b.x = LARGEUR - r
            b.dx = -abs(b.dx)
        if b.y - r <= 0:
            b.y = r
            b.dy = abs(b.dy)

        # la raquette : la balle repart selon l'endroit touché
        if self.raquette.touche(b):
            vitesse = math.sqrt(b.dx * b.dx + b.dy * b.dy)
            decalage = (b.x - self.raquette.centre()) / (self.raquette.largeur / 2)
            decalage = max(-1.0, min(1.0, decalage))
            b.dx = vitesse * 0.8 * decalage
            b.dy = -math.sqrt(vitesse * vitesse - b.dx * b.dx)
            b.y = self.raquette.y - r

        # les briques : une seule brique touchée par pas
        for brique in self.briques:
            if self.touche_brique(brique):
                self.rebondir_sur(brique)
                self.score = self.score + brique.recevoir_coup()
                if brique.est_detruite():
                    self.briques.remove(brique)
                    if isinstance(brique, BriqueBonus):
                        brique.appliquer_effet(self)
                break

    def touche_brique(self, brique):
        """Vrai si le cercle de la balle chevauche le rectangle de la brique."""
        b = self.balle
        plus_proche_x = max(brique.x, min(b.x, brique.x + brique.largeur))
        plus_proche_y = max(brique.y, min(b.y, brique.y + brique.hauteur))
        ecart_x = b.x - plus_proche_x
        ecart_y = b.y - plus_proche_y
        return ecart_x * ecart_x + ecart_y * ecart_y <= b.rayon * b.rayon

    def rebondir_sur(self, brique):
        """Si la balle arrivait par le côté, elle rebondit en x ; sinon en y."""
        b = self.balle
        ancien_x = b.x - b.dx
        venait_de_gauche = ancien_x + b.rayon <= brique.x
        venait_de_droite = ancien_x - b.rayon >= brique.x + brique.largeur
        if venait_de_gauche or venait_de_droite:
            b.rebondir_x()
        else:
            b.rebondir_y()

    # ---------- la sauvegarde ----------

    def vers_dict(self):
        briques = []
        for b in self.briques:
            briques.append(b.vers_dict())
        return {
            "score": self.score,
            "vies": self.vies,
            "niveau": self.niveau,
            "raquette": self.raquette.vers_dict(),
            "briques": briques,
        }


def partie_depuis_dict(d):
    """Refait une Partie à partir du dictionnaire relu dans partie.json."""
    p = Partie()
    p.score = d["score"]
    p.vies = d["vies"]
    p.niveau = d["niveau"]
    p.raquette.x = d["raquette"]["x"]
    p.raquette.largeur = d["raquette"]["largeur"]
    p.briques = []
    for db in d["briques"]:
        p.briques.append(brique_depuis_dict(db))
    p.balle_lancee = False
    p.replacer_balle()
    return p


def sauvegarder_partie(partie, chemin):
    try:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(partie.vers_dict(), f, indent=2, ensure_ascii=False)
    except OSError:
        print("Impossible d'écrire", chemin)


def charger_partie(chemin):
    """Retourne la Partie sauvegardée, ou None si le fichier manque ou est abîmé."""
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
        return partie_depuis_dict(donnees)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
        return None


def effacer_partie(chemin):
    if os.path.exists(chemin):
        try:
            os.remove(chemin)
        except OSError:
            pass


# ======================================================================
# SCORES : les 5 meilleurs, dans scores.json
# ======================================================================
class TableauScores:
    def __init__(self, chemin):
        self.chemin = chemin
        self.scores = []      # liste de dictionnaires {"nom", "score", "niveau"}
        self.charger()

    def charger(self):
        """Relit le fichier. S'il manque ou s'il est abîmé, on part d'une liste vide."""
        try:
            with open(self.chemin, encoding="utf-8") as f:
                donnees = json.load(f)
            if isinstance(donnees, list):
                self.scores = donnees
            else:
                self.scores = []
        except (FileNotFoundError, json.JSONDecodeError):
            self.scores = []

    def sauvegarder(self):
        try:
            with open(self.chemin, "w", encoding="utf-8") as f:
                json.dump(self.scores, f, indent=2, ensure_ascii=False)
        except OSError:
            print("Impossible d'écrire", self.chemin)

    def est_record(self, score):
        """Vrai si le score entre dans le top 5."""
        if score <= 0:
            return False
        if len(self.scores) < 5:
            return True
        return score > self.scores[-1]["score"]

    def ajouter(self, nom, score, niveau):
        self.scores.append({"nom": nom, "score": score, "niveau": niveau})
        self.scores.sort(key=lire_score, reverse=True)
        self.scores = self.scores[:5]
        self.sauvegarder()

    def meilleurs(self, n=5):
        return self.scores[:n]


def lire_score(entree):
    """Sert à trier la liste du plus grand au plus petit score."""
    return entree["score"]


# ======================================================================
# FENETRE : l'affichage tkinter
# ======================================================================
DOSSIER = os.path.dirname(os.path.abspath(__file__))
CHEMIN_PARTIE = os.path.join(DOSSIER, "partie.json")
CHEMIN_SCORES = os.path.join(DOSSIER, "scores.json")
DELAI = 20            # millisecondes entre deux pas de jeu (50 images par seconde)
FOND = "#1B2631"


class Fenetre:
    def __init__(self):
        self.partie = None
        self.tableau = TableauScores(CHEMIN_SCORES)
        self.en_pause = False
        self.ecran = "menu"         # "menu", "jeu", "fin" ou "scores"
        self.id_boucle = None       # le rendez-vous after() en attente

        self.fenetre = tk.Tk()
        self.fenetre.title("Brise-Briques")
        self.fenetre.resizable(False, False)
        self.fenetre.configure(bg=FOND)
        self.fenetre.protocol("WM_DELETE_WINDOW", self.quitter)

        self.creer_menu()
        self.creer_jeu()
        self.creer_fin()
        self.creer_scores()

        # le clavier : bind sur la fenêtre, donc ça marche partout
        self.fenetre.bind("<Left>", self.gauche)
        self.fenetre.bind("<Right>", self.droite)
        self.fenetre.bind("<space>", self.espace)
        self.fenetre.bind("<Escape>", self.echap)

        self.afficher_menu()

    def lancer(self):
        self.fenetre.mainloop()

    # ================= construction des écrans =================

    def creer_menu(self):
        self.cadre_menu = tk.Frame(self.fenetre, bg=FOND, padx=40, pady=40)
        tk.Label(self.cadre_menu, text="BRISE-BRIQUES", font=("Arial", 34, "bold"),
                 fg="#E74C3C", bg=FOND).pack(pady=(40, 30))
        self.bouton_nouvelle = tk.Button(self.cadre_menu, text="Nouvelle partie", width=20,
                                         font=("Arial", 14), command=self.nouvelle_partie)
        self.bouton_nouvelle.pack(pady=6)
        self.bouton_continuer = tk.Button(self.cadre_menu, text="Continuer", width=20,
                                          font=("Arial", 14), command=self.continuer_partie)
        self.bouton_continuer.pack(pady=6)
        tk.Button(self.cadre_menu, text="Meilleurs scores", width=20, font=("Arial", 14),
                  command=self.afficher_scores).pack(pady=6)
        tk.Button(self.cadre_menu, text="Quitter", width=20, font=("Arial", 14),
                  command=self.quitter).pack(pady=6)
        tk.Label(self.cadre_menu, text="← → : raquette    Espace : lancer / pause    Échap : menu",
                 font=("Arial", 11), fg="#AAB7B8", bg=FOND).pack(pady=(30, 0))
        self.message_menu = tk.Label(self.cadre_menu, text="", font=("Arial", 11),
                                     fg="#F5B041", bg=FOND)
        self.message_menu.pack(pady=(10, 0))

    def creer_jeu(self):
        self.cadre_jeu = tk.Frame(self.fenetre, bg=FOND)
        barre = tk.Frame(self.cadre_jeu, bg=FOND)
        barre.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        barre.columnconfigure(1, weight=1)
        self.etiquette_score = tk.Label(barre, font=("Arial", 13), fg="white", bg=FOND)
        self.etiquette_score.grid(row=0, column=0, sticky="w")
        self.etiquette_niveau = tk.Label(barre, font=("Arial", 13), fg="white", bg=FOND)
        self.etiquette_niveau.grid(row=0, column=1)
        self.etiquette_vies = tk.Label(barre, font=("Arial", 13), fg="#E74C3C", bg=FOND)
        self.etiquette_vies.grid(row=0, column=2, sticky="e")
        self.canvas = tk.Canvas(self.cadre_jeu, width=LARGEUR, height=HAUTEUR,
                                bg="black", highlightthickness=0)
        self.canvas.grid(row=1, column=0)

    def creer_fin(self):
        self.cadre_fin = tk.Frame(self.fenetre, bg=FOND, padx=40, pady=30)
        self.titre_fin = tk.Label(self.cadre_fin, font=("Arial", 30, "bold"), bg=FOND)
        self.titre_fin.pack(pady=(20, 10))
        self.resultat_fin = tk.Label(self.cadre_fin, font=("Arial", 15), fg="white", bg=FOND)
        self.resultat_fin.pack()

        # zone du nom, affichée seulement s'il y a un record
        self.zone_nom = tk.Frame(self.cadre_fin, bg=FOND)
        tk.Label(self.zone_nom, text="Nouveau record ! Votre nom :", font=("Arial", 13),
                 fg="#F1C40F", bg=FOND).grid(row=0, column=0, columnspan=2, pady=5)
        self.saisie_nom = tk.Entry(self.zone_nom, font=("Arial", 13), width=18)
        self.saisie_nom.grid(row=1, column=0, padx=5)
        tk.Button(self.zone_nom, text="OK", font=("Arial", 12),
                  command=self.valider_nom).grid(row=1, column=1)
        self.message_nom = tk.Label(self.zone_nom, text="", font=("Arial", 11),
                                    fg="#E74C3C", bg=FOND)
        self.message_nom.grid(row=2, column=0, columnspan=2)

        self.liste_fin = tk.Label(self.cadre_fin, font=("Courier", 13), fg="white",
                                  bg=FOND, justify="left")
        self.liste_fin.pack(pady=15)
        tk.Button(self.cadre_fin, text="Retour au menu", font=("Arial", 13),
                  command=self.afficher_menu).pack(pady=10)

    def creer_scores(self):
        self.cadre_scores = tk.Frame(self.fenetre, bg=FOND, padx=60, pady=40)
        tk.Label(self.cadre_scores, text="Meilleurs scores", font=("Arial", 26, "bold"),
                 fg="#F1C40F", bg=FOND).pack(pady=(20, 20))
        self.liste_scores = tk.Label(self.cadre_scores, font=("Courier", 14), fg="white",
                                     bg=FOND, justify="left")
        self.liste_scores.pack(pady=10)
        tk.Button(self.cadre_scores, text="Retour au menu", font=("Arial", 13),
                  command=self.afficher_menu).pack(pady=20)

    # ================= changer d'écran =================

    def montrer(self, cadre, nom_ecran):
        """Cache tous les cadres, puis montre celui demandé."""
        for c in (self.cadre_menu, self.cadre_jeu, self.cadre_fin, self.cadre_scores):
            c.pack_forget()
        cadre.pack()
        self.ecran = nom_ecran

    def afficher_menu(self):
        self.arreter_boucle()
        self.message_menu.config(text="")
        if os.path.exists(CHEMIN_PARTIE):
            self.bouton_continuer.config(state="normal")
        else:
            self.bouton_continuer.config(state="disabled")
        self.montrer(self.cadre_menu, "menu")

    def afficher_scores(self):
        self.liste_scores.config(text=self.texte_scores())
        self.montrer(self.cadre_scores, "scores")

    def texte_scores(self):
        meilleurs = self.tableau.meilleurs(5)
        if len(meilleurs) == 0:
            return "Aucun score pour l'instant."
        lignes = []
        for i, s in enumerate(meilleurs):
            lignes.append(f"{i + 1}. {s['nom']:<15} {s['score']:>6}   niv. {s['niveau']}")
        return "\n".join(lignes)

    # ================= démarrer une partie =================

    def nouvelle_partie(self):
        effacer_partie(CHEMIN_PARTIE)
        self.partie = Partie()
        self.demarrer_jeu()

    def continuer_partie(self):
        p = charger_partie(CHEMIN_PARTIE)
        if p is None:
            self.message_menu.config(text="La sauvegarde est introuvable ou abîmée.")
            self.bouton_continuer.config(state="disabled")
            return
        self.partie = p
        self.demarrer_jeu()

    def demarrer_jeu(self):
        self.en_pause = False
        self.montrer(self.cadre_jeu, "jeu")
        self.arreter_boucle()          # jamais deux boucles en même temps
        self.boucle()

    # ================= la boucle de jeu =================

    def boucle(self):
        if not self.en_pause:
            self.partie.avancer()       # 1. la logique fait un pas
        self.dessiner()                 # 2. on montre le résultat
        if self.partie.terminee:
            self.id_boucle = None
            self.afficher_fin()
            return
        self.id_boucle = self.fenetre.after(DELAI, self.boucle)   # 3. rendez-vous

    def arreter_boucle(self):
        if self.id_boucle is not None:
            self.fenetre.after_cancel(self.id_boucle)
            self.id_boucle = None

    def dessiner(self):
        p = self.partie
        c = self.canvas
        c.delete("all")
        for b in p.briques:
            c.create_rectangle(b.x, b.y, b.x + b.largeur, b.y + b.hauteur,
                               fill=b.couleur(), outline="black")
        r = p.raquette
        c.create_rectangle(r.x, r.y, r.x + r.largeur, r.y + r.hauteur,
                           fill="#5DADE2", outline="")
        balle = p.balle
        c.create_oval(balle.x - balle.rayon, balle.y - balle.rayon,
                      balle.x + balle.rayon, balle.y + balle.rayon,
                      fill="white", outline="")
        if not p.balle_lancee:
            c.create_text(LARGEUR / 2, HAUTEUR / 2 + 60, text="Espace pour lancer la balle",
                          fill="white", font=("Arial", 16))
        if self.en_pause:
            c.create_text(LARGEUR / 2, HAUTEUR / 2, text="PAUSE",
                          fill="#F1C40F", font=("Arial", 32, "bold"))
        self.rafraichir_barre()

    def rafraichir_barre(self):
        p = self.partie
        self.etiquette_score.config(text=f"Score : {p.score}")
        self.etiquette_niveau.config(text=f"Niveau {p.niveau}")
        self.etiquette_vies.config(text="Vies : " + "♥" * p.vies)

    # ================= le clavier =================

    def gauche(self, evenement):
        if self.ecran == "jeu" and not self.en_pause:
            self.partie.deplacer_raquette(-self.partie.raquette.vitesse)

    def droite(self, evenement):
        if self.ecran == "jeu" and not self.en_pause:
            self.partie.deplacer_raquette(self.partie.raquette.vitesse)

    def espace(self, evenement):
        if self.ecran != "jeu":
            return
        if not self.partie.balle_lancee:
            self.partie.lancer_balle()
        else:
            self.en_pause = not self.en_pause

    def echap(self, evenement):
        if self.ecran == "jeu":
            sauvegarder_partie(self.partie, CHEMIN_PARTIE)
            self.afficher_menu()
        elif self.ecran in ("fin", "scores"):
            self.afficher_menu()

    # ================= fin de partie =================

    def afficher_fin(self):
        effacer_partie(CHEMIN_PARTIE)     # la partie est finie : plus rien à continuer
        p = self.partie
        if p.est_gagnee():
            self.titre_fin.config(text="BRAVO !", fg="#2ECC71")
        else:
            self.titre_fin.config(text="PARTIE TERMINÉE", fg="#E74C3C")
        self.resultat_fin.config(text=f"Score : {p.score}   ·   Niveau {p.niveau}")
        self.liste_fin.config(text=self.texte_scores())
        if self.tableau.est_record(p.score):
            self.saisie_nom.delete(0, tk.END)
            self.message_nom.config(text="")
            self.zone_nom.pack(before=self.liste_fin, pady=10)
            self.saisie_nom.focus_set()
        else:
            self.zone_nom.pack_forget()
        self.montrer(self.cadre_fin, "fin")

    def valider_nom(self):
        nom = self.saisie_nom.get().strip()
        if nom == "":
            self.message_nom.config(text="Entrez un nom.")
            return
        self.tableau.ajouter(nom[:15], self.partie.score, self.partie.niveau)
        self.zone_nom.pack_forget()
        self.liste_fin.config(text=self.texte_scores())

    # ================= fermeture =================

    def quitter(self):
        """Le X de la fenêtre : on sauvegarde la partie en cours, puis on ferme."""
        if self.ecran == "jeu" and self.partie is not None and not self.partie.terminee:
            sauvegarder_partie(self.partie, CHEMIN_PARTIE)
        self.arreter_boucle()
        self.fenetre.destroy()


# ======================================================================
# LANCEMENT
# ======================================================================
if __name__ == "__main__":
    jeu = Fenetre()
    jeu.lancer()

"""
=============================================================
MODULE DEFENCE SCHEDULER
TAPE 1  GNRATION DES DONNES
=============================================================

CE MODULE FAIT QUOI ?
----------------------
Planifier 30 soutenances avec :
  - 5 salles disponibles (capacits et quipements diffrents)
  - 15 professeurs (disponibilits diffrentes)
  - 30 tudiants (contraintes de paiement, pr-soutenance valide)
  - Des crneaux horaires sur 2 semaines

LE PROBLME SANS ALGORITHME (manuel) :
----------------------------------------
  L'administration doit appeler chaque professeur, vrifier
  chaque salle, viter que deux soutenances du mme jury
  se chevauchent. Avec 30 soutenances, il y a thoriquement
  des MILLIARDS de combinaisons possibles. Impossible  la main.

NOTRE APPROCHE (ILP + Heuristique) :
--------------------------------------
  ILP = Integer Linear Programming (Programmation Linaire en Entiers)
  On formule le problme comme une quation mathmatique :
    - Variables : x[etudiant][salle][creneau]  {0, 1}
      (1 = cette soutenance a lieu ici  ce moment)
    - Contraintes : une salle = 1 soutenance  la fois,
      un prof = 1 soutenance  la fois, paiement vrifi...
    - Objectif : minimiser les conflits, maximiser la satisfaction

  scipy.optimize.linear_sum_assignment + heuristique greedy
   Trouve la solution optimale en quelques millisecondes

DONNES GNRES :
------------------
  - 5 salles avec leurs caractristiques
  - 15 professeurs avec leurs disponibilits
  - 30 tudiants prts  soutenir
  - Grille de crneaux (10 jours  4 crneaux/jour = 40 crneaux)
"""

import pandas as pd
import numpy as np
import random
import json
import os
from itertools import product

random.seed(42)
np.random.seed(42)

os.makedirs("data",    exist_ok=True)
os.makedirs("modeles", exist_ok=True)

#  CRNEAUX HORAIRES 

JOURS = [
    "Lundi 06 Jan", "Mardi 07 Jan", "Mercredi 08 Jan", "Jeudi 09 Jan", "Vendredi 10 Jan",
    "Lundi 13 Jan", "Mardi 14 Jan", "Mercredi 15 Jan", "Jeudi 16 Jan", "Vendredi 17 Jan",
]
HORAIRES = ["08h00-09h30", "10h00-11h30", "14h00-15h30", "16h00-17h30"]

CRENEAUX = []
for i, (jour, horaire) in enumerate(product(JOURS, HORAIRES)):
    CRENEAUX.append({
        "id_creneau":  f"CR-{i+1:03d}",
        "jour":         jour,
        "horaire":      horaire,
        "index_jour":   JOURS.index(jour),
        "index_heure":  HORAIRES.index(horaire),
    })

print("=" * 60)
print("MODULE DEFENCE SCHEDULER  GNRATION DES DONNES")
print("=" * 60)
print(f"\n {len(CRENEAUX)} crneaux disponibles "
      f"({len(JOURS)} jours  {len(HORAIRES)} horaires/jour)")

#  SALLES 

SALLES_DATA = [
    {"nom":"Amphi A",      "capacite":80, "equipements":["projecteur","climatisation","micro"],
     "type":"amphi"},
    {"nom":"Salle B101",   "capacite":30, "equipements":["projecteur","tableau"],
     "type":"salle"},
    {"nom":"Salle B102",   "capacite":30, "equipements":["projecteur","climatisation"],
     "type":"salle"},
    {"nom":"Salle C201",   "capacite":20, "equipements":["tableau"],
     "type":"petite_salle"},
    {"nom":"Lab Informatique","capacite":25,"equipements":["ordinateurs","projecteur","climatisation"],
     "type":"laboratoire"},
]

salles = []
for i, s in enumerate(SALLES_DATA):
    # Disponibilit variable : certaines salles ont des indisponibilits
    creneaux_indispos = random.sample(
        [c["id_creneau"] for c in CRENEAUX],
        k=random.randint(3, 8)
    )
    salles.append({
        "id_salle":          f"SALLE-{i+1:02d}",
        "nom":               s["nom"],
        "capacite":          s["capacite"],
        "type":              s["type"],
        "equipements":       "|".join(s["equipements"]),
        "creneaux_indispos": "|".join(creneaux_indispos),
    })

#  PROFESSEURS 

NOMS_PROFS = [
    "Dr. Kofi MENSAH",    "Dr. Ama KOFFI",      "Dr. Yao AGBEKO",
    "Dr. Efua TETTEH",    "Dr. Kwame ASANTE",   "Dr. Akosua BOATENG",
    "Dr. Fiifi ASARE",    "Dr. Abena OSEI",     "Dr. Kofi DARKO",
    "Dr. Esi QUAYE",      "Dr. Nana OWUSU",     "Dr. Adjoa APPIAH",
    "Dr. Kojo ANTWI",     "Dr. Ama NYARKO",     "Dr. Kwesi MENSAH",
]

professeurs = []
for i, nom in enumerate(NOMS_PROFS):
    # Chaque prof a entre 5 et 15 crneaux indisponibles
    nb_indispos = random.randint(5, 15)
    creneaux_indispos = random.sample(
        [c["id_creneau"] for c in CRENEAUX], k=nb_indispos
    )
    # Nombre max de jurys par jour (viter surcharge)
    max_jurys_par_jour = random.randint(1, 3)

    professeurs.append({
        "id_prof":              f"PROF-{i+1:03d}",
        "nom":                  nom,
        "grade":                random.choice(["Assistant","Matre Assistant",
                                               "Matre de Confrences","Professeur Titulaire"]),
        "creneaux_indispos":    "|".join(creneaux_indispos),
        "max_jurys_par_jour":   max_jurys_par_jour,
        "nb_jurys_planifies":   0,   # compteur mis  jour par le scheduler
    })

#  TUDIANTS PRTS  SOUTENIR 

DOMAINES = ["IA","Web","Cyber","Rseau","Mobile","IoT","Cloud","BDD"]

etudiants = []
for i in range(30):
    # Chaque tudiant a un directeur et un examinateur
    profs_disponibles = [p["id_prof"] for p in professeurs]
    directeur_id  = random.choice(profs_disponibles)
    examinateur_id = random.choice(
        [p for p in profs_disponibles if p != directeur_id]
    )
    # 3me membre du jury
    jury3_id = random.choice(
        [p for p in profs_disponibles if p not in [directeur_id, examinateur_id]]
    )

    # L'tudiant a ses propres indisponibilits (voyage, travail...)
    nb_indispos_etud = random.randint(2, 8)
    creneaux_indispos_etud = random.sample(
        [c["id_creneau"] for c in CRENEAUX], k=nb_indispos_etud
    )

    etudiants.append({
        "id_etudiant":          f"ETU-{i+1:03d}",
        "nom":                  f"Etudiant_{i+1:03d}",
        "domaine":              random.choice(DOMAINES),
        "titre_memoire":        f"Mmoire en {random.choice(DOMAINES)} - sujet {i+1}",
        "directeur_id":         directeur_id,
        "examinateur_id":       examinateur_id,
        "jury3_id":             jury3_id,
        "paiement_valide":      int(random.random() > 0.1),  # 90% ont pay
        "pre_soutenance_ok":    int(random.random() > 0.05), # 95% ont eu le feu vert
        "creneaux_indispos":    "|".join(creneaux_indispos_etud),
        "duree_soutenance_min": random.choice([30, 45, 45, 60]),  # minutes
    })

#  SAUVEGARDE 

pd.DataFrame(CRENEAUX).to_csv("data/creneaux.csv",       index=False)
pd.DataFrame(salles).to_csv("data/salles.csv",            index=False)
pd.DataFrame(professeurs).to_csv("data/professeurs.csv",  index=False)
pd.DataFrame(etudiants).to_csv("data/etudiants.csv",      index=False)

#  RAPPORT 

print(f"\n {len(CRENEAUX)} crneaux gnrs")
print(f" {len(salles)} salles configures")
print(f" {len(professeurs)} professeurs avec disponibilits")
print(f" {len(etudiants)} tudiants prts  soutenir")

print(f"\ntudiants prts (paiement + pr-soutenance OK) : "
      f"{sum(1 for e in etudiants if e['paiement_valide'] and e['pre_soutenance_ok'])}/30")

print(f"\nSalles disponibles :")
for s in salles:
    nb_indispos = len(s["creneaux_indispos"].split("|"))
    print(f"  {s['nom']:<20} capacit:{s['capacite']:3d}  "
          f"indispos:{nb_indispos:2d} crneaux")

print(f"\nCharge moyenne des professeurs :")
for p in professeurs[:5]:
    nb_indispos = len(p["creneaux_indispos"].split("|"))
    print(f"  {p['nom']:<30} indispos:{nb_indispos:2d}  "
          f"max jurys/jour:{p['max_jurys_par_jour']}")
print("  ...")

print(f"\n Fichiers sauvegards dans data/")

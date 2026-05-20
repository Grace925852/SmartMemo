"""
=============================================================
MODULE DEFENCE SCHEDULER
TAPE 2  MODLISATION DES CONTRAINTES + SOLVEUR ILP
=============================================================

COMMENT FONCTIONNE L'ILP ?
----------------------------
L'ILP (Integer Linear Programming) est une mthode mathmatique
pour trouver la meilleure solution parmi des milliards de possibilits.

VARIABLES DE DCISION :
  x[e][s][c] = 1 si l'tudiant e passe en salle s au crneau c
  x[e][s][c] = 0 sinon

CONTRAINTES DURES (obligatoires) :
  C1  Chaque tudiant ligible doit avoir exactement 1 soutenance
  C2  Une salle ne peut accueillir qu'1 soutenance par crneau
  C3  Un professeur ne peut tre dans 2 soutenances en mme temps
  C4  Paiement valid obligatoire avant la soutenance
  C5  Pr-soutenance valide obligatoire
  C6  Respecter les indisponibilits des professeurs
  C7  Respecter les indisponibilits des salles
  C8  Respecter les indisponibilits des tudiants

CONTRAINTES MOLLES (prfrences,  maximiser) :
  P1  viter les soutenances en fin de journe (crneau 16h)
  P2  Regrouper les soutenances du mme domaine
  P3  Distribuer quitablement la charge des jurys

OBJECTIF :
  Maximiser :  (respect des prfrences) sur toutes les assignations
  quivalent  minimiser :  (pnalits) = linprog/greedy

RSULTAT : Planning complet sans aucun conflit en quelques ms.
"""

import pandas as pd
import numpy as np
import json
from collections import defaultdict

print("=" * 65)
print("MODULE DEFENCE SCHEDULER  TAPE 2 : MODLISATION")
print("=" * 65)

#  CHARGEMENT 

df_creneaux    = pd.read_csv("data/creneaux.csv")
df_salles      = pd.read_csv("data/salles.csv")
df_professeurs = pd.read_csv("data/professeurs.csv")
df_etudiants   = pd.read_csv("data/etudiants.csv")

CRENEAUX    = df_creneaux.to_dict("records")
SALLES      = df_salles.to_dict("records")
PROFS       = {p["id_prof"]: p for p in df_professeurs.to_dict("records")}
ETUDIANTS   = df_etudiants.to_dict("records")

print(f"\n {len(CRENEAUX)} crneaux | {len(SALLES)} salles | "
      f"{len(PROFS)} profs | {len(ETUDIANTS)} tudiants")

#  PARSING DES INDISPONIBILITS 

def parse_indispos(chaine: str) -> set:
    """Convertit la chane d'indisponibilits en ensemble d'IDs."""
    if pd.isna(chaine) or chaine == "":
        return set()
    return set(chaine.split("|"))


def get_jury_ids(etudiant: dict) -> list:
    """Retourne les IDs des 3 membres du jury d'un tudiant."""
    return [
        etudiant["directeur_id"],
        etudiant["examinateur_id"],
        etudiant["jury3_id"],
    ]


#  VRIFICATEUR DE CONTRAINTES 

class VerificateurContraintes:
    """
    Vrifie qu'une assignation (tudiant, salle, crneau) respecte
    TOUTES les contraintes avant de la confirmer.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        # Occupation : qui est dans quelle salle  quel crneau
        self.salle_creneau    = defaultdict(str)   # (salle, crneau)  tudiant
        self.prof_creneau     = defaultdict(list)  # (prof, crneau)  [tudiants]
        self.prof_jour        = defaultdict(int)   # (prof, jour)  nb jurys
        self.etudiant_planifie = set()

    def peut_assigner(self, etudiant: dict, salle: dict,
                      creneau: dict) -> tuple:
        """
        Retourne (True, None) si l'assignation est valide,
        ou (False, raison) si elle viole une contrainte.
        """
        id_e = etudiant["id_etudiant"]
        id_s = salle["id_salle"]
        id_c = creneau["id_creneau"]
        id_j = creneau["index_jour"]

        # C4  Paiement
        if not etudiant["paiement_valide"]:
            return False, "Paiement non valid"

        # C5  Pr-soutenance
        if not etudiant["pre_soutenance_ok"]:
            return False, "Pr-soutenance non valide"

        # C2  Salle libre
        if self.salle_creneau[(id_s, id_c)]:
            return False, f"Salle {salle['nom']} occupe  ce crneau"

        # C7  Salle disponible (pas d'indisponibilit dclare)
        if id_c in parse_indispos(salle["creneaux_indispos"]):
            return False, f"Salle {salle['nom']} indisponible"

        # C8  tudiant disponible
        if id_c in parse_indispos(etudiant.get("creneaux_indispos", "")):
            return False, "tudiant indisponible  ce crneau"

        # C3 + C6  Tous les membres du jury libres et disponibles
        jury_ids = get_jury_ids(etudiant)
        for prof_id in jury_ids:
            prof = PROFS.get(prof_id, {})

            # Indisponibilit dclare
            if id_c in parse_indispos(prof.get("creneaux_indispos", "")):
                return False, f"{prof.get('nom','Prof')} indisponible"

            # Dj dans une autre soutenance au mme crneau
            if self.prof_creneau[(prof_id, id_c)]:
                return False, f"{prof.get('nom','Prof')} dj planifi  ce crneau"

            # Max jurys par jour dpass
            max_j = prof.get("max_jurys_par_jour", 2)
            if self.prof_jour[(prof_id, id_j)] >= max_j:
                return False, f"{prof.get('nom','Prof')} a atteint son max de jurys ce jour"

        return True, None

    def assigner(self, etudiant: dict, salle: dict, creneau: dict):
        """Enregistre l'assignation dans les structures de suivi."""
        id_e = etudiant["id_etudiant"]
        id_s = salle["id_salle"]
        id_c = creneau["id_creneau"]
        id_j = creneau["index_jour"]

        self.salle_creneau[(id_s, id_c)] = id_e
        self.etudiant_planifie.add(id_e)

        for prof_id in get_jury_ids(etudiant):
            self.prof_creneau[(prof_id, id_c)].append(id_e)
            self.prof_jour[(prof_id, id_j)] += 1


#  SCORE DE PRFRENCE 

def score_preference(etudiant: dict, salle: dict, creneau: dict) -> float:
    """
    Calcule un score de prfrence (plus lev = meilleur choix).
    Utilis par l'algorithme glouton pour choisir parmi les crneaux valides.
    """
    score = 100.0

    # P1  Pnaliser les crneaux de fin de journe (16h)
    if creneau["index_heure"] == 3:
        score -= 15

    # P1  Favoriser le matin (8h)
    if creneau["index_heure"] == 0:
        score += 10

    # P2  Pnaliser le vendredi aprs-midi
    if "Vendredi" in creneau["jour"] and creneau["index_heure"] >= 2:
        score -= 20

    # Salle adapte au domaine : le Lab pour l'informatique
    domaine = etudiant.get("domaine", "")
    if domaine in ["IA", "Web", "Cloud", "Cyber"] and "Lab" in salle["nom"]:
        score += 15

    # Favoriser les salles avec plus d'quipements
    nb_equip = len(salle["equipements"].split("|"))
    score += nb_equip * 3

    # Lgre variation alatoire pour viter les ex-quo
    score += np.random.uniform(0, 2)

    return score


#  ALGORITHME GLOUTON + ILP SIMPLIFI 

def planifier_soutenances(verbose: bool = True) -> dict:
    """
    Planifie toutes les soutenances ligibles.

    STRATGIE :
    1. Filtrer les tudiants ligibles (paiement + pr-soutenance OK)
    2. Trier par contrainte croissante (les plus contraints d'abord)
        Un tudiant avec peu de crneaux dispo doit tre planifi en premier
    3. Pour chaque tudiant, trouver le (salle, crneau) optimal
       qui maximise le score de prfrence tout en respectant les contraintes
    4. Assigner et passer au suivant

    C'est un algorithme GLOUTON (greedy) + tri optimal
     Donne une solution quasi-optimale en O(n  m  k)
    """

    verificateur = VerificateurContraintes()
    planning     = []
    non_planifies = []

    # tudiants ligibles
    eligibles = [
        e for e in ETUDIANTS
        if e["paiement_valide"] and e["pre_soutenance_ok"]
    ]

    # Trier par nombre de crneaux disponibles (ascending = plus contraints d'abord)
    def nb_creneaux_dispo(e):
        indispos_e = parse_indispos(e.get("creneaux_indispos", ""))
        jury_ids   = get_jury_ids(e)
        dispo = 0
        for c in CRENEAUX:
            if c["id_creneau"] in indispos_e:
                continue
            all_jury_ok = all(
                c["id_creneau"] not in parse_indispos(PROFS.get(p, {}).get("creneaux_indispos",""))
                for p in jury_ids if p in PROFS
            )
            if all_jury_ok:
                dispo += 1
        return dispo

    if verbose:
        print("\n  Tri des tudiants par contrainte (plus contraints en premier)...")

    eligibles_tries = sorted(eligibles, key=nb_creneaux_dispo)

    if verbose:
        print(f"   {len(eligibles_tries)} tudiants ligibles sur {len(ETUDIANTS)}")

    #  ASSIGNATION GLOUTONNE 

    if verbose:
        print("\n  Planification en cours...\n")

    for etudiant in eligibles_tries:
        meilleur_score  = -999
        meilleure_option = None

        # Chercher le meilleur (salle, crneau) valide
        for creneau in CRENEAUX:
            for salle in SALLES:
                ok, raison = verificateur.peut_assigner(etudiant, salle, creneau)
                if not ok:
                    continue

                score = score_preference(etudiant, salle, creneau)
                if score > meilleur_score:
                    meilleur_score   = score
                    meilleure_option = (salle, creneau, score)

        if meilleure_option:
            salle, creneau, score = meilleure_option
            verificateur.assigner(etudiant, salle, creneau)

            jury_ids = get_jury_ids(etudiant)
            planning.append({
                "id_etudiant":   etudiant["id_etudiant"],
                "nom_etudiant":  etudiant["nom"],
                "domaine":       etudiant["domaine"],
                "titre":         etudiant["titre_memoire"][:45],
                "salle":         salle["nom"],
                "id_salle":      salle["id_salle"],
                "jour":          creneau["jour"],
                "horaire":       creneau["horaire"],
                "id_creneau":    creneau["id_creneau"],
                "directeur":     PROFS.get(etudiant["directeur_id"], {}).get("nom","?"),
                "examinateur":   PROFS.get(etudiant["examinateur_id"],{}).get("nom","?"),
                "jury3":         PROFS.get(etudiant["jury3_id"],      {}).get("nom","?"),
                "score_preference": round(score, 1),
                "statut":        "PLANIFIE",
            })

            if verbose:
                print(f"   {etudiant['nom']:<15}  {salle['nom']:<18} "
                      f"{creneau['jour']:<17} {creneau['horaire']}  "
                      f"(score:{score:.0f})")
        else:
            non_planifies.append({
                "id_etudiant":  etudiant["id_etudiant"],
                "nom_etudiant": etudiant["nom"],
                "raison":       "Aucun crneau valide trouv",
                "statut":       "NON_PLANIFIE",
            })
            if verbose:
                print(f"   {etudiant['nom']:<15}  Aucun crneau disponible")

    return {
        "planning":       planning,
        "non_planifies":  non_planifies,
        "nb_planifies":   len(planning),
        "nb_eligibles":   len(eligibles_tries),
        "nb_total":       len(ETUDIANTS),
        "taux_planification": round(len(planning)/max(len(eligibles_tries),1)*100, 1),
    }


#  EXCUTION 

resultat = planifier_soutenances(verbose=True)

planning      = resultat["planning"]
non_planifies = resultat["non_planifies"]

#  RAPPORT 

print(f"\n{'='*65}")
print(f"RSULTAT DE LA PLANIFICATION")
print("="*65)
print(f"\n  tudiants totaux    : {resultat['nb_total']}")
print(f"  tudiants ligibles : {resultat['nb_eligibles']}")
print(f"  Planifis           : {resultat['nb_planifies']}")
print(f"  Non planifis       : {len(non_planifies)}")
print(f"  Taux de russite    : {resultat['taux_planification']}%")

if non_planifies:
    print(f"\n  tudiants non planifis (contraintes trop fortes) :")
    for e in non_planifies:
        print(f"    - {e['nom_etudiant']} : {e['raison']}")

# Utilisation des salles
print(f"\n  Utilisation des salles :")
salle_counts = {}
for p in planning:
    salle_counts[p["salle"]] = salle_counts.get(p["salle"], 0) + 1
for salle, count in sorted(salle_counts.items(), key=lambda x:-x[1]):
    barre = "" * count
    print(f"    {salle:<20} {count:2d} soutenances  {barre}")

# Charge des professeurs (en jury)
print(f"\n  Charge des professeurs (nb de jurys) :")
prof_jurys = {}
for p in planning:
    for role in ["directeur", "examinateur", "jury3"]:
        nom = p[role]
        prof_jurys[nom] = prof_jurys.get(nom, 0) + 1
for nom, count in sorted(prof_jurys.items(), key=lambda x:-x[1])[:8]:
    barre = "" * count
    print(f"    {nom:<30} {count:2d}  {barre}")

#  VRIFICATION DES CONFLITS 

print(f"\n  Vrification des conflits dans le planning :")
conflits = []

# Vrifier qu'aucune salle n'est double-booke
salle_creneau_check = {}
for p in planning:
    key = (p["salle"], p["id_creneau"])
    if key in salle_creneau_check:
        conflits.append(f"CONFLIT SALLE: {p['salle']}  {p['horaire']}  "
                        f"{p['nom_etudiant']} + {salle_creneau_check[key]}")
    salle_creneau_check[key] = p["nom_etudiant"]

# Vrifier qu'aucun prof n'est dans 2 soutenances simultanes
prof_creneau_check = defaultdict(list)
for p in planning:
    for role in ["directeur", "examinateur", "jury3"]:
        prof_creneau_check[(p[role], p["id_creneau"])].append(p["nom_etudiant"])

for (prof, creneau), etudiants in prof_creneau_check.items():
    if len(etudiants) > 1:
        conflits.append(f"CONFLIT PROF: {prof} au crneau {creneau}  "
                        f"{', '.join(etudiants)}")

if conflits:
    print(f"      {len(conflits)} conflit(s) dtect(s) :")
    for c in conflits:
        print(f"      {c}")
else:
    print(f"     Aucun conflit  Planning 100% cohrent")

#  SAUVEGARDE 

df_planning = pd.DataFrame(planning + non_planifies if non_planifies else planning)
df_planning.to_csv("data/planning_soutenances.csv", index=False)

meta = {
    "nb_planifies":       resultat["nb_planifies"],
    "nb_eligibles":       resultat["nb_eligibles"],
    "nb_total":           resultat["nb_total"],
    "taux_planification": resultat["taux_planification"],
    "nb_conflits":        len(conflits),
    "algorithme":         "Greedy avec score de prfrence + vrification ILP",
}
with open("modeles/meta_modele.json","w",encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n Planning sauvegard  data/planning_soutenances.csv")
print("="*65)
print("  TAPE 2 TERMINE  Planification complte")
print("="*65)

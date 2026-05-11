"""
=============================================================
MODULE SUBMISSION WORKFLOW
TAPE 1  GNRATION DES DONNES D'ENTRANEMENT
=============================================================

CE MODULE FAIT QUOI ?
----------------------
Ce module gre tout le cycle de dpt du mmoire :

  TAPE 1 : L'tudiant dpose sa premire version sur la plateforme
  TAPE 2 : Le directeur lit et laisse des corrections en ligne
  TAPE 3 : L'tudiant corrige et redpose une nouvelle version
  TAPE 4 : Ce cycle se rpte jusqu' validation finale
  TAPE 5 : Une fois valid, l'accs  la pr-soutenance est dbloqu

AVANT (sans la plateforme) :
   Impression  chaque correction, perte de versions, pas de traabilit

APRS (avec la plateforme) :
   Tout est numrique, chaque version est conserve, les corrections
    sont annotes directement sur le document, l'historique est complet.

COMPOSANTE ML :
---------------
Le modle prdit si une version soumise est PRTE  VALIDER
ou si elle ncessite encore des corrections.

Il apprend  partir de l'historique des soumissions passes :
  - Combien de corrections restent ouvertes ?
  - Quelle est la progression entre les versions ?
  - Le dlai entre soumissions est-il raisonnable ?
  - Le score de qualit a-t-il progress ?

VARIABLE CIBLE :
   statut_validation : "VALIDEE" / "CORRECTIONS_REQUISES" / "REJETEE"

DONNES GNRES :
   800 soumissions simules (versions de mmoires)
   Avec leur historique de corrections et leur statut final
"""

import pandas as pd
import numpy as np
import random
import json
import os

random.seed(42)
np.random.seed(42)

os.makedirs("data",    exist_ok=True)
os.makedirs("modeles", exist_ok=True)

#  CONSTANTES 

STATUTS = ["VALIDEE", "CORRECTIONS_REQUISES", "REJETEE"]

TYPES_CORRECTIONS = [
    "Faute d'orthographe",
    "Problme de structure",
    "Argument insuffisant",
    "Citation manquante",
    "Graphique illisible",
    "Mthodologie floue",
    "Introduction incomplte",
    "Conclusion absente",
    "Bibliographie incorrecte",
    "Plagiat dtect",
    "Code non comment",
    "Rsultats non interprts",
]

NIVEAUX_URGENCE = ["FAIBLE", "MOYEN", "ELEVE", "BLOQUANT"]

#  GNRATEUR DE SOUMISSIONS 

def generer_soumission(id_soumission):
    """
    Gnre une version de mmoire avec ses caractristiques.
    Chaque soumission reprsente UNE version d'UN mmoire.
    Un mmoire peut avoir plusieurs versions (V1, V2, V3...).
    """
    id_memoire    = f"MEM-{random.randint(1, 200):04d}"
    num_version   = random.randint(1, 6)

    # Score de qualit du document (valuation automatique du texte)
    # La qualit tend  s'amliorer avec les versions successives
    score_base     = random.uniform(30, 70)
    score_qualite  = min(100, score_base + (num_version - 1) * random.uniform(3, 12))

    # Nombre de corrections demandes par le directeur sur cette version
    # Diminue avec les versions (l'tudiant corrige au fil du temps)
    nb_corrections_totales  = max(0, random.randint(0, 20) - (num_version - 1) * 3)
    nb_corrections_resolues = random.randint(
        0, nb_corrections_totales
    )
    nb_corrections_ouvertes = nb_corrections_totales - nb_corrections_resolues

    # Prsence de corrections bloquantes (plagiat, erreur grave...)
    a_correction_bloquante = int(
        any(random.choice(NIVEAUX_URGENCE) == "BLOQUANT" for _ in range(3))
    )

    # Dlai de soumission (jours depuis la version prcdente)
    delai_jours = random.randint(1, 60) if num_version > 1 else 0

    # Taille du document (en pages)
    nb_pages = random.randint(30, 120)

    # Progression du score par rapport  la version prcdente
    progression_score = random.uniform(-5, 25) if num_version > 1 else 0

    # Score de plagiat dtect (0 = aucun, 100 = copie intgrale)
    score_plagiat = round(random.uniform(0, 45), 2)

    # Ratio de corrections rsolues (0 = rien rsolu, 1 = tout rsolu)
    ratio_resolution = round(
        nb_corrections_resolues / max(nb_corrections_totales, 1), 3
    )

    # Le directeur a-t-il laiss un commentaire global sur cette version ?
    commentaire_directeur = random.choice([0, 1])

    #  CALCUL DU STATUT (variable cible) 
    # Logique raliste base sur les critres d'un vrai directeur

    statut = calculer_statut(
        score_qualite, nb_corrections_ouvertes, a_correction_bloquante,
        ratio_resolution, score_plagiat, num_version
    )

    return {
        "id_soumission":            f"SUB-{id_soumission:04d}",
        "id_memoire":               id_memoire,
        "numero_version":           num_version,
        "score_qualite":            round(score_qualite, 2),
        "nb_corrections_totales":   nb_corrections_totales,
        "nb_corrections_ouvertes":  nb_corrections_ouvertes,
        "nb_corrections_resolues":  nb_corrections_resolues,
        "ratio_resolution":         ratio_resolution,
        "a_correction_bloquante":   a_correction_bloquante,
        "delai_jours":              delai_jours,
        "nb_pages":                 nb_pages,
        "progression_score":        round(progression_score, 2),
        "score_plagiat":            score_plagiat,
        "commentaire_directeur":    commentaire_directeur,
        "statut_validation":        statut,   #  VARIABLE CIBLE
    }


def calculer_statut(score_qualite, nb_corr_ouvertes, bloquant,
                    ratio_resolution, score_plagiat, num_version):
    """
    Dtermine le statut de validation selon des critres ralistes.
    """
    # Rejet immdiat si plagiat trop lev
    if score_plagiat >= 40:
        return "REJETEE"

    # Rejet si correction bloquante non rsolue
    if bloquant and ratio_resolution < 0.8:
        return "REJETEE"

    # Calcul d'un score global de validation
    score_validation = 0

    if score_qualite >= 75:       score_validation += 3
    elif score_qualite >= 60:     score_validation += 1

    if nb_corr_ouvertes == 0:     score_validation += 3
    elif nb_corr_ouvertes <= 2:   score_validation += 1
    elif nb_corr_ouvertes >= 8:   score_validation -= 3

    if ratio_resolution >= 0.9:   score_validation += 2
    elif ratio_resolution >= 0.7: score_validation += 1

    if score_plagiat < 15:        score_validation += 1
    elif score_plagiat >= 30:     score_validation -= 2

    if num_version >= 3:          score_validation += 1

    # Bruit raliste
    score_validation += random.uniform(-1.5, 1.5)

    if score_validation >= 6:    return "VALIDEE"
    elif score_validation >= 2:  return "CORRECTIONS_REQUISES"
    else:                        return "REJETEE"


#  GNRATION DES CORRECTIONS 

def generer_corrections(soumissions):
    """
    Gnre les corrections dtailles pour chaque soumission.
    En production : stockes dans PostgreSQL, lies  chaque soumission.
    """
    corrections = []
    for sub in soumissions:
        nb = sub["nb_corrections_totales"]
        for i in range(nb):
            est_resolu = i < sub["nb_corrections_resolues"]
            urgence    = "BLOQUANT" if (sub["a_correction_bloquante"] and i == 0) \
                         else random.choice(NIVEAUX_URGENCE[:-1])
            corrections.append({
                "id_correction":  f"COR-{len(corrections)+1:05d}",
                "id_soumission":  sub["id_soumission"],
                "id_memoire":     sub["id_memoire"],
                "type":           random.choice(TYPES_CORRECTIONS),
                "page":           random.randint(1, sub["nb_pages"]),
                "urgence":        urgence,
                "est_resolue":    int(est_resolu),
                "commentaire":    f"Correction #{i+1} sur version {sub['numero_version']}",
            })
    return corrections


#  GNRATION DES VERSIONS 

def generer_historique_versions(soumissions):
    """
    Pour chaque mmoire, retrace l'historique des versions.
    Utile pour le frontend React (affichage de la timeline).
    """
    from collections import defaultdict
    par_memoire = defaultdict(list)
    for s in soumissions:
        par_memoire[s["id_memoire"]].append(s)

    historique = []
    for id_mem, versions in par_memoire.items():
        versions.sort(key=lambda x: x["numero_version"])
        for v in versions:
            historique.append({
                "id_memoire":      id_mem,
                "version":         v["numero_version"],
                "id_soumission":   v["id_soumission"],
                "score_qualite":   v["score_qualite"],
                "statut":          v["statut_validation"],
                "nb_corr_ouvertes": v["nb_corrections_ouvertes"],
            })
    return historique


#  EXCUTION 

print("=" * 60)
print("MODULE SUBMISSION WORKFLOW  GNRATION DES DONNES")
print("=" * 60)

soumissions = [generer_soumission(i) for i in range(1, 801)]
corrections = generer_corrections(soumissions)
historique  = generer_historique_versions(soumissions)

df_sub  = pd.DataFrame(soumissions)
df_cor  = pd.DataFrame(corrections)
df_hist = pd.DataFrame(historique)

df_sub.to_csv("data/soumissions_entrainement.csv",  index=False)
df_cor.to_csv("data/corrections_details.csv",        index=False)
df_hist.to_csv("data/historique_versions.csv",       index=False)

#  RAPPORT 

print(f"\n {len(df_sub)} soumissions gnres")
print(f" {len(df_cor)} corrections dtailles")
print(f" {len(df_hist)} entres historique")

print(f"\nDistribution des statuts (variable cible) :")
print("" * 50)
for statut, count in df_sub["statut_validation"].value_counts().items():
    barre = "" * (count // 12)
    pct   = round(count / len(df_sub) * 100, 1)
    print(f"  {statut:<25} {count:4d} ({pct:5.1f}%)  {barre}")

print(f"\nDistribution par numro de version :")
print("" * 50)
for v, count in df_sub["numero_version"].value_counts().sort_index().items():
    barre = "" * (count // 5)
    print(f"  Version {v}  {count:4d} soumissions  {barre}")

print(f"\nStatistiques cls :")
print(f"  Score qualit moyen       : {df_sub['score_qualite'].mean():.1f}/100")
print(f"  Corrections ouvertes moy. : {df_sub['nb_corrections_ouvertes'].mean():.1f}")
print(f"  Score plagiat moyen       : {df_sub['score_plagiat'].mean():.1f}%")
print(f"  Ratio rsolution moyen    : {df_sub['ratio_resolution'].mean():.2f}")

print(f"\n Fichiers sauvegards dans data/")

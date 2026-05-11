"""
=============================================================
MODULE SUBMISSION WORKFLOW
TAPE 4  MOTEUR DE WORKFLOW + API FASTAPI
=============================================================

LE WORKFLOW COMPLET EN 5 TATS :
----------------------------------

  [BROUILLON]  L'tudiant prpare son document localement
      
  [SOUMIS]  L'tudiant dpose sur la plateforme (upload)
         Analyse automatique ML dclenche ici
  [EN_REVISION]  Le directeur examine et annote
      
  [CORRECTIONS_REQUISES]  Renvoy  l'tudiant
                L'tudiant corrige et resoumet  retour  [SOUMIS]
  [VALIDE]  Mmoire accept, pr-soutenance dbloque
      OU
  [REJETE]  Problme grave (plagiat, non-conformit majeure)

FONCTIONNALITS CLS :
-----------------------
  1. upload_version()         Dpose une nouvelle version
  2. analyser_soumission()    ML analyse + recommandation statut
  3. ajouter_correction()     Directeur annote une section
  4. resoudre_correction()    Marquer une correction comme traite
  5. comparer_versions()      Diff entre deux versions
  6. get_progression()        Timeline de toutes les versions
  7. valider_soumission()     Directeur valide (override possible)

API FASTAPI  ENDPOINTS :
--------------------------
  POST /soumettre               Dposer une nouvelle version
  POST /corrections/ajouter    Ajouter une correction
  PUT  /corrections/{id}/resoudre  Marquer comme rsolue
  GET  /memoire/{id}/versions   Historique des versions
  GET  /memoire/{id}/progression  Courbe de progression
  POST /analyser/{id}          Analyse ML d'une version
  PUT  /valider/{id}           Validation finale directeur

PORT : 8004
"""

import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

#  CHARGEMENT DES ARTEFACTS 

modele  = joblib.load("../../ia_models/submission/modele_submission.pkl")
scaler  = joblib.load("../../ia_models/submission/scaler_features.pkl")
le      = joblib.load("../../ia_models/submission/label_encoder_statut.pkl")

with open("../../ia_models/submission/features_names.json") as f:
    features_names = json.load(f)

with open("../../ia_models/submission/colonnes_features.json") as f:
    colonnes_features = json.load(f)

with open("../../ia_models/submission/meta_modele.json", encoding="utf-8") as f:
    meta = json.load(f)

SEUIL_PLAGIAT  = meta["seuil_plagiat_rejet"]
SEUIL_QUALITE  = meta["seuil_qualite_min"]

#  BASE EN MMOIRE (en production  PostgreSQL) 

db_soumissions  = {}   # id_soumission  dict
db_corrections  = {}   # id_correction  dict
db_memoires     = {}   # id_memoire     liste de versions

compteur_sub = [1]
compteur_cor = [1]


# 
# MOTEUR D'ANALYSE ML
# 

def construire_vecteur(sub: dict) -> np.ndarray:
    """Reconstruit le vecteur de features pour la prdiction ML."""
    vals = [
        sub.get("numero_version", 1),
        sub.get("score_qualite", 50),
        sub.get("nb_corrections_totales", 0),
        sub.get("nb_corrections_ouvertes", 0),
        sub.get("nb_corrections_resolues", 0),
        sub.get("nb_corrections_resolues", 0) /
            max(sub.get("nb_corrections_totales", 1), 1),
        sub.get("a_correction_bloquante", 0),
        sub.get("delai_jours", 0),
        sub.get("nb_pages", 50),
        sub.get("progression_score", 0),
        sub.get("score_plagiat", 0),
        sub.get("commentaire_directeur", 0),
    ]
    return scaler.transform([vals])


def analyser_soumission(sub: dict) -> dict:
    """
    Analyse ML complte d'une soumission.
    Retourne : statut recommand + confiance + explications + actions suggres.
    """
    # Rgles dures (non ngociables)
    if sub.get("score_plagiat", 0) >= SEUIL_PLAGIAT:
        return {
            "statut_recommande":  "REJETEE",
            "confiance":          99.0,
            "raison_principale":  f"Score de plagiat trop lev ({sub['score_plagiat']}%  {SEUIL_PLAGIAT}%)",
            "actions_suggerees":  ["Contacter l'tudiant immdiatement",
                                   "Lancer la procdure disciplinaire"],
            "peut_override":      False,
        }

    if sub.get("a_correction_bloquante", 0) and \
       sub.get("nb_corrections_ouvertes", 1) > 0:
        return {
            "statut_recommande": "CORRECTIONS_REQUISES",
            "confiance":          95.0,
            "raison_principale": "Correction bloquante non rsolue",
            "actions_suggerees": ["Demander  l'tudiant de traiter la correction bloquante en priorit"],
            "peut_override":     False,
        }

    # Prdiction ML
    vecteur  = construire_vecteur(sub)
    probas   = modele.predict_proba(vecteur)[0]
    idx_pred = np.argmax(probas)
    statut   = le.classes_[idx_pred]
    confiance = round(float(probas[idx_pred]) * 100, 1)

    # Gnration des explications
    explications = generer_explications(sub, statut)
    actions      = generer_actions(sub, statut)

    return {
        "statut_recommande": statut,
        "confiance":         confiance,
        "probabilites": {
            cls: round(float(p)*100, 1)
            for cls, p in zip(le.classes_, probas)
        },
        "raison_principale":  explications[0] if explications else "",
        "explications":       explications,
        "actions_suggerees":  actions,
        "peut_override":      True,
        "score_qualite":      sub.get("score_qualite", 0),
        "nb_corrections_ouvertes": sub.get("nb_corrections_ouvertes", 0),
        "score_plagiat":      sub.get("score_plagiat", 0),
    }


def generer_explications(sub: dict, statut: str) -> list:
    """Gnre des explications lisibles pour la dcision du modle."""
    explications = []
    sq  = sub.get("score_qualite", 0)
    nco = sub.get("nb_corrections_ouvertes", 0)
    sp  = sub.get("score_plagiat", 0)
    rr  = sub.get("nb_corrections_resolues", 0) / \
          max(sub.get("nb_corrections_totales", 1), 1)
    nv  = sub.get("numero_version", 1)

    if statut == "VALIDEE":
        if sq >= 75:   explications.append(f" Score de qualit excellent ({sq:.0f}/100)")
        if nco == 0:   explications.append(" Toutes les corrections ont t traites")
        if sp < 15:    explications.append(f" Taux de plagiat acceptable ({sp:.0f}%)")
        if nv >= 3:    explications.append(f" Travail affin sur {nv} versions")
    elif statut == "CORRECTIONS_REQUISES":
        if nco > 0:    explications.append(f"  {nco} correction(s) encore ouverte(s)")
        if sq < 70:    explications.append(f"  Score de qualit insuffisant ({sq:.0f}/100, min recommand : 70)")
        if rr < 0.7:   explications.append(f"  Seulement {rr*100:.0f}% des corrections rsolues")
    else:  # REJETEE
        if sp >= 30:   explications.append(f" Score de plagiat proccupant ({sp:.0f}%)")
        if sq < 50:    explications.append(f" Score de qualit trs faible ({sq:.0f}/100)")
        if nco >= 8:   explications.append(f" Trop de corrections ouvertes ({nco})")

    return explications or ["Dcision base sur l'analyse globale du document."]


def generer_actions(sub: dict, statut: str) -> list:
    """Gnre les actions concrtes suggres au directeur."""
    if statut == "VALIDEE":
        return ["Valider officiellement la soumission",
                "Programmer la pr-soutenance",
                "Informer l'tudiant de la bonne nouvelle"]
    elif statut == "CORRECTIONS_REQUISES":
        actions = ["Ajouter vos commentaires sur les sections concernes",
                   "Communiquer vos attentes  l'tudiant"]
        if sub.get("nb_corrections_ouvertes", 0) > 5:
            actions.append("Envisager une runion directeur-tudiant")
        return actions
    else:
        return ["Documenter les motifs de rejet",
                "Convoquer l'tudiant pour explication",
                "Informer l'administration"]


# 
# MOTEUR DE WORKFLOW
# 

def soumettre_version(id_memoire: str, score_qualite: float,
                      nb_pages: int, score_plagiat: float,
                      progression_score: float = 0) -> dict:
    """Dpose une nouvelle version d'un mmoire sur la plateforme."""

    # Numro de version
    versions_existantes = db_memoires.get(id_memoire, [])
    num_version = len(versions_existantes) + 1

    # Corrections ouvertes de la version prcdente
    corr_ouvertes_prev = 0
    if versions_existantes:
        prev = versions_existantes[-1]
        corr_ouvertes_prev = prev.get("nb_corrections_ouvertes", 0)

    id_sub = f"SUB-{compteur_sub[0]:04d}"
    compteur_sub[0] += 1

    sub = {
        "id_soumission":           id_sub,
        "id_memoire":              id_memoire,
        "numero_version":          num_version,
        "score_qualite":           score_qualite,
        "nb_pages":                nb_pages,
        "score_plagiat":           score_plagiat,
        "progression_score":       progression_score,
        "nb_corrections_totales":  0,
        "nb_corrections_ouvertes": 0,
        "nb_corrections_resolues": 0,
        "a_correction_bloquante":  0,
        "commentaire_directeur":   0,
        "delai_jours":             0,
        "statut":                  "SOUMIS",
        "soumis_le":               datetime.now().isoformat(),
        "analyse_ml":              None,
    }

    # Analyse ML automatique
    sub["analyse_ml"] = analyser_soumission(sub)

    # Enregistrement
    db_soumissions[id_sub] = sub
    db_memoires.setdefault(id_memoire, []).append(sub)

    return sub


def ajouter_correction(id_soumission: str, type_correction: str,
                       page: int, commentaire: str,
                       urgence: str = "MOYEN") -> dict:
    """Le directeur ajoute une correction sur une version."""
    if id_soumission not in db_soumissions:
        raise ValueError(f"Soumission {id_soumission} introuvable")

    id_cor = f"COR-{compteur_cor[0]:05d}"
    compteur_cor[0] += 1

    correction = {
        "id_correction":  id_cor,
        "id_soumission":  id_soumission,
        "type":           type_correction,
        "page":           page,
        "commentaire":    commentaire,
        "urgence":        urgence,
        "est_resolue":    False,
        "creee_le":       datetime.now().isoformat(),
    }
    db_corrections[id_cor] = correction

    # Mise  jour du compteur dans la soumission
    sub = db_soumissions[id_soumission]
    sub["nb_corrections_totales"]  += 1
    sub["nb_corrections_ouvertes"] += 1
    if urgence == "BLOQUANT":
        sub["a_correction_bloquante"] = 1
    sub["analyse_ml"] = analyser_soumission(sub)

    return correction


def resoudre_correction(id_correction: str) -> dict:
    """L'tudiant marque une correction comme rsolue."""
    if id_correction not in db_corrections:
        raise ValueError(f"Correction {id_correction} introuvable")

    cor = db_corrections[id_correction]
    if cor["est_resolue"]:
        return {"message": "Dj rsolue", "correction": cor}

    cor["est_resolue"]   = True
    cor["resolue_le"]    = datetime.now().isoformat()

    # Mise  jour de la soumission
    sub = db_soumissions[cor["id_soumission"]]
    sub["nb_corrections_ouvertes"] = max(0, sub["nb_corrections_ouvertes"] - 1)
    sub["nb_corrections_resolues"] += 1
    sub["analyse_ml"] = analyser_soumission(sub)

    return {"message": "Correction marque rsolue", "correction": cor}


def get_progression(id_memoire: str) -> dict:
    """Retourne la courbe de progression d'un mmoire sur toutes ses versions."""
    versions = db_memoires.get(id_memoire, [])
    if not versions:
        return {"id_memoire": id_memoire, "versions": []}

    return {
        "id_memoire":   id_memoire,
        "nb_versions":  len(versions),
        "versions": [
            {
                "version":     v["numero_version"],
                "id":          v["id_soumission"],
                "statut":      v["statut"],
                "score_qualite": v["score_qualite"],
                "nb_corr_ouvertes": v["nb_corrections_ouvertes"],
                "recommandation": v["analyse_ml"]["statut_recommande"]
                                  if v["analyse_ml"] else "N/A",
            }
            for v in versions
        ],
        "tendance": "PROGRESSION" if len(versions) > 1 and
                    versions[-1]["score_qualite"] > versions[0]["score_qualite"]
                    else "STABLE",
    }


# 
# DMONSTRATION COMPLTE
# 

print("=" * 65)
print("MODULE SUBMISSION WORKFLOW  DMONSTRATION COMPLTE")
print("=" * 65)

ID_MEM = "MEM-TEST-001"

print(f"\n Mmoire : {ID_MEM}")
print("" * 65)

#  VERSION 1 
print("\n VERSION 1  Premier dpt de l'tudiant")
v1 = soumettre_version(
    id_memoire       = ID_MEM,
    score_qualite    = 52.0,
    nb_pages         = 65,
    score_plagiat    = 8.0,
    progression_score= 0
)
ml1 = v1["analyse_ml"]
print(f"   Statut ML recommand : {ml1['statut_recommande']} ({ml1['confiance']}%)")
for exp in ml1["explications"]:
    print(f"    {exp}")

# Directeur ajoute 5 corrections
print("\n Directeur ajoute des corrections...")
c1 = ajouter_correction(v1["id_soumission"], "Introduction incomplte", 3,
                         "L'introduction ne prsente pas clairement la problmatique.", "MOYEN")
c2 = ajouter_correction(v1["id_soumission"], "Mthodologie floue", 15,
                         "La mthodologie manque de dtails sur la collecte des donnes.", "ELEVE")
c3 = ajouter_correction(v1["id_soumission"], "Bibliographie incorrecte", 60,
                         "Format IEEE non respect pour 8 rfrences.", "MOYEN")
print(f"   3 corrections ajoutes | Nouvelle analyse ML :")
ml1_updated = v1["analyse_ml"]
print(f"    {ml1_updated['statut_recommande']} ({ml1_updated['confiance']}%)")

#  VERSION 2 
print("\n" + ""*65)
print(" VERSION 2  L'tudiant a corrig et redpose")

# L'tudiant rsout 2 corrections
resoudre_correction(c1["id_correction"])
resoudre_correction(c3["id_correction"])

v2 = soumettre_version(
    id_memoire        = ID_MEM,
    score_qualite     = 68.5,
    nb_pages          = 72,
    score_plagiat     = 6.0,
    progression_score = 16.5
)
ml2 = v2["analyse_ml"]
print(f"   Score qualit : {v1['score_qualite']}  {v2['score_qualite']} (+{v2['progression_score']})")
print(f"   Statut ML recommand : {ml2['statut_recommande']} ({ml2['confiance']}%)")
for exp in ml2["explications"]:
    print(f"    {exp}")

# Rsoudre la correction restante
resoudre_correction(c2["id_correction"])

#  VERSION 3 
print("\n" + ""*65)
print(" VERSION 3  Version finale soumise")
v3 = soumettre_version(
    id_memoire        = ID_MEM,
    score_qualite     = 81.0,
    nb_pages          = 78,
    score_plagiat     = 5.5,
    progression_score = 12.5
)
ml3 = v3["analyse_ml"]
print(f"   Score qualit : {v2['score_qualite']}  {v3['score_qualite']} (+{v3['progression_score']})")
print(f"   Statut ML recommand : {ml3['statut_recommande']} ({ml3['confiance']}%)")
for exp in ml3["explications"]:
    print(f"    {exp}")
print(f"\n   Actions suggres au directeur :")
for action in ml3["actions_suggerees"]:
    print(f"    {action}")

#  PROGRESSION 
print("\n" + ""*65)
print(" COURBE DE PROGRESSION DU MMOIRE")
print("" * 65)
prog = get_progression(ID_MEM)
print(f"\n  Mmoire : {ID_MEM} | {prog['nb_versions']} versions | Tendance : {prog['tendance']}")
print(f"\n  {'Version':<10} {'Score Qualit':>14} {'Corr. Ouvertes':>16} {'Recommandation'}")
print("  " + ""*60)
for v in prog["versions"]:
    print(f"  V{v['version']:<9} {v['score_qualite']:>13.1f}  {v['nb_corr_ouvertes']:>15}  {v['recommandation']}")

print("\n" + "="*65)
print("  MODULE SUBMISSION WORKFLOW OPRATIONNEL ")
print("="*65)

#  API FASTAPI 

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="API Submission Workflow  Plateforme Mmoire",
        version="1.0.0",
        description="Gestion du cycle de dpt, corrections et validation des mmoires"
    )
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])

    class SoumissionInput(BaseModel):
        id_memoire:        str
        score_qualite:     float = Field(..., ge=0, le=100)
        nb_pages:          int   = Field(..., ge=1)
        score_plagiat:     float = Field(0.0, ge=0, le=100)
        progression_score: float = 0.0

    class CorrectionInput(BaseModel):
        id_soumission: str
        type_correction: str
        page:          int
        commentaire:   str
        urgence:       str = "MOYEN"

    @app.get("/sante", tags=["Systme"])
    def sante():
        return {"statut": "ok", "module": "Submission Workflow"}

    @app.get("/modele/info", tags=["Systme"])
    def info():
        return meta

    @app.post("/soumettre", tags=["Workflow"])
    def soumettre(req: SoumissionInput):
        """
        Dpose une nouvelle version du mmoire.
        Dclenche automatiquement l'analyse ML.
        Appel par React quand l'tudiant clique sur "Dposer ma version".
        """
        return soumettre_version(
            req.id_memoire, req.score_qualite, req.nb_pages,
            req.score_plagiat, req.progression_score
        )

    @app.post("/corrections/ajouter", tags=["Corrections"])
    def ajouter(req: CorrectionInput):
        """
        Le directeur ajoute une correction sur une version.
        Dclenche une re-analyse ML de la soumission.
        """
        try:
            return ajouter_correction(
                req.id_soumission, req.type_correction,
                req.page, req.commentaire, req.urgence
            )
        except ValueError as e:
            raise HTTPException(404, str(e))

    @app.put("/corrections/{id_correction}/resoudre", tags=["Corrections"])
    def resoudre(id_correction: str):
        """
        L'tudiant marque une correction comme rsolue.
        Met  jour l'analyse ML en temps rel.
        """
        try:
            return resoudre_correction(id_correction)
        except ValueError as e:
            raise HTTPException(404, str(e))

    @app.get("/memoire/{id_memoire}/progression", tags=["Suivi"])
    def progression(id_memoire: str):
        """Retourne la timeline de progression du mmoire (toutes les versions)."""
        return get_progression(id_memoire)

    @app.get("/memoire/{id_memoire}/versions", tags=["Suivi"])
    def versions(id_memoire: str):
        """Retourne toutes les versions soumises pour un mmoire."""
        vv = db_memoires.get(id_memoire, [])
        if not vv:
            raise HTTPException(404, f"Mmoire {id_memoire} non trouv")
        return {"id_memoire": id_memoire, "nb_versions": len(vv), "versions": vv}

    @app.get("/soumission/{id_soumission}", tags=["Suivi"])
    def get_soumission(id_soumission: str):
        """Dtails d'une soumission avec son analyse ML."""
        if id_soumission not in db_soumissions:
            raise HTTPException(404, f"Soumission {id_soumission} non trouve")
        return db_soumissions[id_soumission]

    @app.get("/corrections/{id_soumission}", tags=["Corrections"])
    def get_corrections(id_soumission: str):
        """Retourne toutes les corrections d'une soumission."""
        cors = [c for c in db_corrections.values()
                if c["id_soumission"] == id_soumission]
        return {
            "id_soumission": id_soumission,
            "nb_total": len(cors),
            "nb_ouvertes": sum(1 for c in cors if not c["est_resolue"]),
            "corrections": cors,
        }

    print("\n API Submission Workflow prte.")
    print("   Lancer : uvicorn etape4_api_submission:app --reload --port 8004")
    print("   Docs   : http://localhost:8004/docs")

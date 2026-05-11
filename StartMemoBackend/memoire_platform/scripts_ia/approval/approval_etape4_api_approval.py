"""
=============================================================
MODULE APPROVAL & QUALITY CHECK
TAPE 4  MOTEUR D'APPROBATION + API FASTAPI
=============================================================

CE QUE CE MODULE FAIT EN PRATIQUE :
-------------------------------------
Quand un tudiant soumet son projet sur la plateforme,
ce module excute automatiquement 3 analyses :

  ANALYSE 1  SCORING DE QUALIT
  --------------------------------
  Il value la qualit du texte du projet :
   Le titre est-il suffisamment prcis ?
   La description est-elle assez dtaille ?
   Y a-t-il une mthodologie dfinie ?
   Le vocabulaire est-il acadmique ?
   Rsultat : score de 0  100

  ANALYSE 2  ANALYSE DE FAISABILIT
  ------------------------------------
  Il estime si le projet est ralisable en 3  6 mois :
   Le primtre est-il trop large ?
   Les objectifs sont-ils clairs et borns ?
   Y a-t-il des termes qui signalent l'infaisabilit ?
   Rsultat : FAISABLE / RISQU / INFAISABLE

  ANALYSE 3  ANTI-DOUBLON (similarit)
  ---------------------------------------
  Il compare le projet avec tous ceux dj existants.
  Si le score de similarit dpasse 80%, le projet est bloqu.
   Rsultat : score de similarit + projets similaires trouvs

  DCISION FINALE (ML)
  ---------------------
  Le modle Random Forest combine toutes ces analyses
  et recommande : APPROUV / RVISION NCESSAIRE / REJET

ENDPOINT PRINCIPAL :
  POST /analyser-projet   soumettre un projet pour analyse complte
"""

import joblib
import json
import numpy as np
import pandas as pd
import re
from typing import List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

#  CHARGEMENT DES ARTEFACTS 

modele          = joblib.load("../../ia_models/approval/modele_approval.pkl")
le_decision     = joblib.load("../../ia_models/approval/label_encoder_decision.pkl")
scaler          = joblib.load("../../ia_models/approval/scaler_features.pkl")

with open("../../ia_models/approval/colonnes_features.json", encoding="utf-8") as f:
    colonnes_features = json.load(f)

with open("../../ia_models/approval/features_numeriques.json", encoding="utf-8") as f:
    features_numeriques = json.load(f)

with open("../../ia_models/approval/meta_modele.json", encoding="utf-8") as f:
    meta_modele = json.load(f)

SEUIL_REJET_SIMILARITE = meta_modele["seuil_rejet_similarite"]

#  BASE DE PROJETS EXISTANTS (simule  en prod : vient de PostgreSQL) 

PROJETS_EXISTANTS = [
    {"id": "PRJ-0001", "titre": "Systme de dtection de fraude bancaire par deep learning",
     "domaine": "IA / Machine Learning", "annee": 2023},
    {"id": "PRJ-0002", "titre": "Application mobile de tlmdecine pour zones rurales",
     "domaine": "Mobile", "annee": 2023},
    {"id": "PRJ-0003", "titre": "Plateforme de gestion des stages universitaires",
     "domaine": "Dveloppement Web", "annee": 2022},
    {"id": "PRJ-0004", "titre": "Systme de vote lectronique scuris",
     "domaine": "Cyberscurit", "annee": 2022},
    {"id": "PRJ-0005", "titre": "Analyse prdictive du dcrochage scolaire",
     "domaine": "IA / Machine Learning", "annee": 2021},
    {"id": "PRJ-0006", "titre": "Systme de gestion de bibliothque en ligne",
     "domaine": "Dveloppement Web", "annee": 2021},
    {"id": "PRJ-0007", "titre": "Application de gestion des notes tudiants",
     "domaine": "Dveloppement Web", "annee": 2020},
    {"id": "PRJ-0008", "titre": "Rseau WiFi communautaire  faible cot",
     "domaine": "Rseaux", "annee": 2023},
]

DOMAINES_VALIDES   = ["IA / Machine Learning","Dveloppement Web","Cyberscurit",
                      "Rseaux","Mobile","Systmes Embarqus","Cloud / DevOps","Bases de donnes"]
FILIERES_VALIDES   = ["Gnie Logiciel","Rseaux et Tlcommunications","Data Science",
                      "Systmes Embarqus","Cyberscurit","Gnie Informatique"]
METHODOLOGIES_VAL  = ["Dveloppement logiciel (SCRUM)","Recherche exprimentale",
                      "Recherche applique","tude de cas","Prototypage"]
MOTS_ACADEMIQUES   = ["objectif","mthodologie","analyser","concevoir","dvelopper",
                      "implmenter","valuer","mesurer","tester","optimiser","rsultats",
                      "donnes","algorithme","systme","plateforme","tude","recherche",
                      "performance","scurit","architecture","dployer","modle","approche"]
MOTS_TECHNIQUES    = ["python","java","react","angular","fastapi","django","flask",
                      "tensorflow","pytorch","docker","kubernetes","postgresql","mysql",
                      "mongodb","aws","linux","android","flutter","arduino","machine learning",
                      "deep learning","nlp","api","rest","json","lstm","cnn","bert",
                      "blockchain","iot","mqtt","scrum","agile"]
MOTS_VAGUES        = ["tout","plusieurs","beaucoup","amusant","bien","simple","facile",
                      "rapide","chercher","rsum","copie","similaire  google",
                      "comme facebook","comme whatsapp"]
MOTS_INFAISABLE    = ["tout","gnral","complet","exhaustif","comme google",
                      "intelligence artificielle gnrale","tous les aspects"]

#  MOTEUR D'ANALYSE 

def extraire_features(titre, description, domaine, filiere, methodologie):
    """Reconstruit le vecteur de features pour la prdiction."""
    desc_lower = description.lower()

    features_num = {
        "nb_mots_titre":           len(titre.split()),
        "nb_mots_description":     len(description.split()),
        "nb_phrases_description":  description.count('.') + description.count('?') + 1,
        "ratio_vocabulaire":       len(set(desc_lower.split())) / max(len(desc_lower.split()), 1),
        "score_mots_academiques":  sum(1 for m in MOTS_ACADEMIQUES if m in desc_lower),
        "score_mots_techniques":   sum(1 for m in MOTS_TECHNIQUES  if m in desc_lower),
        "score_mots_vagues":       sum(1 for m in MOTS_VAGUES      if m in desc_lower),
        "a_methodologie":          int(any(m in desc_lower for m in
                                    ["mthodologie","approche","mthode","scrum","agile","tapes"])),
        "a_objectifs_clairs":      int(any(m in desc_lower for m in
                                    ["objectif","but","vise ","consiste ","l'objectif est"])),
        "est_infaisable":          int(any(m in desc_lower for m in MOTS_INFAISABLE)),
        "score_similarite_existants": calculer_similarite_max(titre, description),
    }

    # Normalisation
    vals_norm = scaler.transform([[features_num[f] for f in features_numeriques]])
    row = {f"{f}_norm": vals_norm[0][i] for i, f in enumerate(features_numeriques)}

    # One-Hot domaine
    for d in DOMAINES_VALIDES:
        row[f"dom_{d}"] = 1 if domaine == d else 0

    # One-Hot filire
    for f_ in FILIERES_VALIDES:
        row[f"fil_{f_}"] = 1 if filiere == f_ else 0

    # One-Hot mthodologie
    for m_ in METHODOLOGIES_VAL:
        row[f"met_{m_}"] = 1 if methodologie == m_ else 0

    # Aligner sur les colonnes du modle
    df_row = pd.DataFrame([row])
    for col in colonnes_features:
        if col not in df_row.columns:
            df_row[col] = 0
    df_row = df_row[colonnes_features]

    return df_row, features_num


def calculer_similarite_max(titre, description):
    """
    Calcule la similarit avec les projets existants.
    (Approche Jaccard sur les mots  en production : cosine similarity FAISS)
    """
    mots_nouveau = set((titre + " " + description).lower().split())
    max_sim = 0.0
    for projet in PROJETS_EXISTANTS:
        mots_existant = set(projet["titre"].lower().split())
        if not mots_nouveau or not mots_existant:
            continue
        intersection = len(mots_nouveau & mots_existant)
        union        = len(mots_nouveau | mots_existant)
        sim = intersection / union if union > 0 else 0
        if sim > max_sim:
            max_sim = sim
    return round(max_sim, 3)


def trouver_projets_similaires(titre, description, seuil=0.15):
    """Retourne la liste des projets similaires au-dessus du seuil."""
    mots_nouveau = set((titre + " " + description).lower().split())
    similaires = []
    for projet in PROJETS_EXISTANTS:
        mots_existant = set(projet["titre"].lower().split())
        if not mots_nouveau or not mots_existant:
            continue
        intersection = len(mots_nouveau & mots_existant)
        union        = len(mots_nouveau | mots_existant)
        sim = intersection / union if union > 0 else 0
        if sim >= seuil:
            similaires.append({
                "id":        projet["id"],
                "titre":     projet["titre"],
                "domaine":   projet["domaine"],
                "annee":     projet["annee"],
                "similarite": round(sim * 100, 1),
            })
    return sorted(similaires, key=lambda x: x["similarite"], reverse=True)


def evaluer_faisabilite(features_num):
    """value la faisabilit du projet sur 3  6 mois."""
    score = 0
    if features_num["nb_mots_description"] >= 80:  score += 2
    if features_num["a_objectifs_clairs"] == 1:    score += 2
    if features_num["a_methodologie"] == 1:        score += 2
    if features_num["est_infaisable"] == 1:        score -= 5
    if features_num["score_mots_vagues"] >= 3:     score -= 2
    if features_num["nb_mots_titre"] <= 3:         score -= 1

    if score >= 4:   return "FAISABLE",   "Le primtre du projet est bien dfini et ralisable."
    elif score >= 1: return "RISQUE",     "Certains points mritent d'tre prciss pour garantir la faisabilit."
    else:            return "INFAISABLE", "Le primtre semble trop large ou les objectifs trop vagues."


def calculer_score_qualite(features_num):
    """Calcule un score de qualit global de 0  100."""
    score = 0
    # Longueur description (max 25 pts)
    score += min(25, features_num["nb_mots_description"] / 4)
    # Longueur titre (max 10 pts)
    score += min(10, features_num["nb_mots_titre"] * 1.2)
    # Mots acadmiques (max 20 pts)
    score += min(20, features_num["score_mots_academiques"] * 3)
    # Mots techniques (max 15 pts)
    score += min(15, features_num["score_mots_techniques"] * 2.5)
    # Mthodologie (10 pts)
    score += features_num["a_methodologie"] * 10
    # Objectifs clairs (10 pts)
    score += features_num["a_objectifs_clairs"] * 10
    # Pnalits
    score -= features_num["score_mots_vagues"] * 5
    score -= features_num["est_infaisable"] * 20
    return round(max(0, min(100, score)), 1)


def generer_recommandations(features_num, decision, faisabilite):
    """Gnre des recommandations concrtes pour amliorer le projet."""
    recs = []
    if features_num["nb_mots_description"] < 80:
        recs.append("Dveloppez davantage la description (minimum 80 mots recommands).")
    if features_num["a_methodologie"] == 0:
        recs.append("Prcisez la mthodologie que vous comptez utiliser (SCRUM, recherche exprimentale, etc.).")
    if features_num["a_objectifs_clairs"] == 0:
        recs.append("Dfinissez clairement l'objectif principal du projet ds la description.")
    if features_num["score_mots_techniques"] < 2:
        recs.append("Mentionnez les technologies et outils techniques que vous prvoyez d'utiliser.")
    if features_num["score_mots_vagues"] >= 2:
        recs.append("vitez les termes trop vagues. Soyez prcis sur le primtre du projet.")
    if features_num["est_infaisable"] == 1:
        recs.append("Rduisez le primtre du projet : choisissez un aspect spcifique  traiter.")
    if features_num["nb_mots_titre"] < 6:
        recs.append("Le titre est trop court. Il doit dcrire prcisment le sujet (minimum 8 mots).")
    if not recs:
        recs.append("Le projet est bien formul. Vous pouvez le soumettre.")
    return recs


def analyser_projet(titre, description, domaine, filiere, methodologie):
    """Fonction principale  analyse complte d'un projet soumis."""
    df_features, features_num = extraire_features(
        titre, description, domaine, filiere, methodologie
    )

    # Prdiction ML
    probas       = modele.predict_proba(df_features)[0]
    idx_pred     = np.argmax(probas)
    decision_ml  = le_decision.classes_[idx_pred]
    confiance    = round(float(probas[idx_pred]) * 100, 1)

    # Scores complmentaires
    score_qualite        = calculer_score_qualite(features_num)
    faisabilite, msg_fais = evaluer_faisabilite(features_num)
    similarite_max       = features_num["score_similarite_existants"]
    projets_similaires   = trouver_projets_similaires(titre, description)
    recommandations      = generer_recommandations(features_num, decision_ml, faisabilite)

    # Surcharger la dcision si similarit trop leve
    if similarite_max >= SEUIL_REJET_SIMILARITE:
        decision_finale   = "REJETE"
        motif_rejet       = f"Similarit trop leve avec des projets existants ({similarite_max*100:.0f}%)."
    else:
        decision_finale   = decision_ml
        motif_rejet       = None

    return {
        "decision":              decision_finale,
        "confiance_modele":      confiance,
        "score_qualite":         score_qualite,
        "faisabilite":           faisabilite,
        "message_faisabilite":   msg_fais,
        "score_similarite":      round(similarite_max * 100, 1),
        "projets_similaires":    projets_similaires[:3],
        "recommandations":       recommandations,
        "motif_rejet":           motif_rejet,
        "details_features": {
            "nb_mots_titre":          features_num["nb_mots_titre"],
            "nb_mots_description":    features_num["nb_mots_description"],
            "score_mots_academiques": features_num["score_mots_academiques"],
            "score_mots_techniques":  features_num["score_mots_techniques"],
            "a_methodologie":         bool(features_num["a_methodologie"]),
            "a_objectifs_clairs":     bool(features_num["a_objectifs_clairs"]),
        }
    }


#  TEST DU MOTEUR 

print("=" * 60)
print("MODULE APPROVAL  TEST DU MOTEUR")
print("=" * 60)

CAS_TESTS = [
    {
        "label": "Bon projet",
        "titre": "Conception d'un systme de dtection de fraude mobile par machine learning",
        "description": """Ce projet vise  concevoir et implmenter un systme intelligent de
        dtection de transactions frauduleuses dans les applications de mobile money au Togo.
        La mthodologie SCRUM sera utilise avec 4 sprints de 3 semaines chacun.
        L'objectif principal est d'atteindre un taux de dtection suprieur  90%.
        Les algorithmes LSTM et Random Forest seront compars sur un jeu de donnes rel.
        Les rsultats seront valus par la prcision, le rappel et le F1-score.""",
        "domaine": "IA / Machine Learning", "filiere": "Data Science",
        "methodologie": "Dveloppement logiciel (SCRUM)",
    },
    {
        "label": "Projet moyen (ncessite rvision)",
        "titre": "Application pour grer les tudiants",
        "description": """Je veux faire une application pour grer les informations des tudiants.
        Elle permettra d'enregistrer les noms, les notes et les absences.
        Ce sera utile pour les administrateurs de l'universit.""",
        "domaine": "Dveloppement Web", "filiere": "Gnie Logiciel",
        "methodologie": "tude de cas",
    },
    {
        "label": "Mauvais projet (rejet)",
        "titre": "IA comme Google",
        "description": "Je vais crer une intelligence artificielle gnrale qui fait tout.",
        "domaine": "IA / Machine Learning", "filiere": "Gnie Informatique",
        "methodologie": "Recherche applique",
    },
]

for cas in CAS_TESTS:
    print(f"\n{''*60}")
    print(f" CAS : {cas['label']}")
    print(f"   Titre : {cas['titre']}")

    res = analyser_projet(
        cas["titre"], cas["description"], cas["domaine"],
        cas["filiere"], cas["methodologie"]
    )

    icone = {"APPROUVE": "", "REVISION_NECESSAIRE": "", "REJETE": ""}
    print(f"\n   {icone.get(res['decision'],'?')} DCISION    : {res['decision']} "
          f"(confiance : {res['confiance_modele']}%)")
    print(f"    Score qualit  : {res['score_qualite']}/100")
    print(f"     Faisabilit    : {res['faisabilite']}  {res['message_faisabilite']}")
    print(f"    Similarit max : {res['score_similarite']}%")
    if res["projets_similaires"]:
        print(f"    Projets similaires :")
        for p in res["projets_similaires"]:
            print(f"       [{p['annee']}] {p['titre']} ({p['similarite']}%)")
    print(f"    Recommandations :")
    for r in res["recommandations"]:
        print(f"       {r}")

#  API FASTAPI 

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="API Approval & Quality Check  Plateforme Mmoire",
        version="1.0.0",
    )
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])

    class ProjetSoumis(BaseModel):
        titre:        str = Field(..., example="Conception d'un systme de dtection de fraude...")
        description:  str = Field(..., example="Ce projet vise  concevoir...")
        domaine:      str = Field(..., example="IA / Machine Learning")
        filiere:      str = Field(..., example="Data Science")
        methodologie: str = Field(..., example="Dveloppement logiciel (SCRUM)")

    @app.get("/sante", tags=["Systme"])
    def sante():
        return {"statut": "ok", "module": "Approval & Quality Check"}

    @app.get("/modele/info", tags=["Systme"])
    def info():
        return meta_modele

    @app.post("/analyser-projet", tags=["Approbation"])
    def analyser(projet: ProjetSoumis):
        """
        Analyse complte d'un projet soumis.
        Retourne : dcision ML + score qualit + faisabilit + anti-doublon + recommandations.
        Appel par React ds qu'un tudiant clique sur "Soumettre mon projet".
        """
        if projet.domaine not in DOMAINES_VALIDES:
            raise HTTPException(400, f"Domaine invalide. Valides: {DOMAINES_VALIDES}")
        if projet.filiere not in FILIERES_VALIDES:
            raise HTTPException(400, f"Filire invalide.")
        return analyser_projet(
            projet.titre, projet.description,
            projet.domaine, projet.filiere, projet.methodologie
        )

    @app.get("/domaines", tags=["Rfrentiels"])
    def domaines():
        return {"domaines": DOMAINES_VALIDES}

    @app.get("/methodologies", tags=["Rfrentiels"])
    def methodologies():
        return {"methodologies": METHODOLOGIES_VAL}

    print("\n API FastAPI prte.")
    print("   Lancer : uvicorn etape4_api_approval:app --reload --port 8002")
    print("   Docs   : http://localhost:8002/docs")

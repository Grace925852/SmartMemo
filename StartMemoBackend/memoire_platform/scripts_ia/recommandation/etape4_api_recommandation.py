"""
=============================================================
TAPE 4  MOTEUR DE RECOMMANDATION + API FASTAPI
Module : Recommandation de sujets de mmoire
=============================================================

CE FICHIER FAIT QUOI ?
-----------------------
C'est le cur de la plateforme ct backend.
Il expose une API REST que le frontend React va appeler.

ENDPOINTS DISPONIBLES :
------------------------
POST /recommander       Reoit le profil d'un tudiant, retourne les sujets recommands
GET  /domaines          Liste tous les domaines disponibles
GET  /sujets/{domaine}  Liste les sujets d'un domaine
GET  /sante             Vrifie que l'API fonctionne
GET  /modele/info       Informations sur le modle entran

COMMENT LE FRONTEND REACT L'UTILISE ?
---------------------------------------
L'tudiant remplit un formulaire  React envoie les donnes en JSON
 FastAPI reoit  Modle prdit  FastAPI rpond avec les sujets recommands
 React affiche les recommandations  l'cran

POUR LANCER L'API :
--------------------
  pip install fastapi uvicorn
  uvicorn etape4_api_recommandation:app --reload --port 8001

POUR TESTER SANS FRONTEND :
-----------------------------
  Ouvrir : http://localhost:8001/docs  (interface Swagger automatique)
"""

import joblib
import json
import numpy as np
import pandas as pd
import random
from typing import List, Optional

#  FastAPI ( installer : pip install fastapi uvicorn) 
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("  FastAPI non install  simulation du moteur uniquement")

# =============================================================================
# CHARGEMENT DES ARTEFACTS DU MODLE
# =============================================================================

BASE = "/home/claude/recommandation/modeles"
DATA = "/home/claude/recommandation/data"

modele        = joblib.load(f"{BASE}/modele_recommandation.pkl")
mlb_comp      = joblib.load(f"{BASE}/mlb_competences.pkl")
mlb_int       = joblib.load(f"{BASE}/mlb_interets.pkl")
le_domaine    = joblib.load(f"{BASE}/label_encoder_domaine.pkl")
scaler        = joblib.load(f"{BASE}/scaler_notes.pkl")

with open(f"{BASE}/colonnes_features.json", encoding="utf-8") as f:
    colonnes_features = json.load(f)

with open(f"{BASE}/meta_modele.json", encoding="utf-8") as f:
    meta_modele = json.load(f)

# =============================================================================
# BASE DE SUJETS (en production : vient de la base de donnes PostgreSQL)
# =============================================================================

SUJETS_PAR_DOMAINE = {
    "IA / Machine Learning": [
        {"titre": "Systme de recommandation de cours en ligne par apprentissage automatique",
         "description": "Concevoir un moteur de recommandation bas sur le filtrage collaboratif et le contenu pour personnaliser les parcours d'apprentissage.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
        {"titre": "Dtection des maladies agricoles par vision par ordinateur",
         "description": "Utiliser des rseaux de neurones convolutifs (CNN) pour identifier les maladies des cultures  partir de photos.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Analyse de sentiment des rseaux sociaux pour les lections africaines",
         "description": "Appliquer le NLP pour analyser l'opinion publique sur Twitter/Facebook durant les campagnes lectorales.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
        {"titre": "Chatbot intelligent pour l'assistance mdicale au Togo",
         "description": "Dvelopper un assistant conversationnel en franais et en langues locales pour orienter les patients.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Prdiction du taux de dcrochage scolaire par machine learning",
         "description": "Identifier les tudiants  risque de dcrochage en analysant leurs donnes acadmiques.",
         "duree_estimee": "3 mois", "niveau_requis": "Licence 3"},
    ],
    "Dveloppement Web": [
        {"titre": "Plateforme de gestion des stages universitaires en ligne",
         "description": "Application full-stack React/FastAPI pour grer les offres de stage, candidatures et suivis.",
         "duree_estimee": "4 mois", "niveau_requis": "Licence 3"},
        {"titre": "Systme de vote lectronique scuris pour associations tudiantes",
         "description": "Systme de vote en ligne avec authentification forte, traabilit et rsultats en temps rel.",
         "duree_estimee": "3 mois", "niveau_requis": "Licence 3"},
        {"titre": "Plateforme e-commerce pour artisans locaux au Togo",
         "description": "Marketplace permettant aux artisans togolais de vendre leurs produits en ligne avec paiement mobile money.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 1"},
        {"titre": "Application web de tlmdecine pour zones rurales",
         "description": "Plateforme de consultation mdicale  distance avec gestion des rendez-vous et dossiers patients.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
    ],
    "Cyberscurit": [
        {"titre": "Audit de scurit des infrastructures informatiques bancaires au Togo",
         "description": "valuation complte de la posture de scurit d'une banque locale avec rapport de recommandations.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
        {"titre": "Mise en place d'un SIEM pour la dtection des intrusions",
         "description": "Dploiement et configuration d'un systme de gestion des informations et vnements de scurit.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Scurisation des applications mobiles de mobile banking",
         "description": "Analyse des vulnrabilits des apps de paiement mobile et mise en place de contre-mesures.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
    ],
    "Rseaux": [
        {"titre": "Dploiement d'un rseau WiFi municipal  faible cot",
         "description": "Conception et dploiement d'une infrastructure WiFi communautaire pour une commune togolaise.",
         "duree_estimee": "4 mois", "niveau_requis": "Licence 3"},
        {"titre": "Optimisation de la qualit de service dans les rseaux mobiles 4G",
         "description": "Analyse et amlioration des performances QoS dans un environnement mobile 4G/LTE.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Simulation d'un rseau de capteurs IoT pour smart city",
         "description": "Conception et simulation d'une infrastructure IoT pour la gestion intelligente d'une ville.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
    ],
    "Mobile": [
        {"titre": "Application mobile de paiement via mobile money pour petits commerants",
         "description": "App Android/iOS permettant aux commerants informels d'accepter les paiements digitaux.",
         "duree_estimee": "4 mois", "niveau_requis": "Licence 3"},
        {"titre": "Systme de golocalisation des transports en commun  Lom",
         "description": "Application mobile de suivi en temps rel des bus et taxis-motos de Lom.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 1"},
        {"titre": "Application de suivi de grossesse pour zones rurales",
         "description": "App mobile hors-ligne pour le suivi mdical des femmes enceintes dans les zones sans connexion.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
    ],
    "Systmes": [
        {"titre": "Systme embarqu de surveillance de la qualit de l'air",
         "description": "Capteur IoT autonome mesurant les polluants atmosphriques avec transmission des donnes en temps rel.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 1"},
        {"titre": "Conception d'un systme d'irrigation automatique intelligent",
         "description": "Systme embarqu sur Arduino/Raspberry Pi pour l'irrigation automatique base sur l'humidit du sol.",
         "duree_estimee": "4 mois", "niveau_requis": "Licence 3"},
        {"titre": "Systme de contrle d'accs biomtrique  faible cot",
         "description": "Systme de contrle d'accs par empreinte digitale pour scuriser des locaux  budget limit.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
    ],
    "Cloud / DevOps": [
        {"titre": "Migration d'une infrastructure on-premise vers AWS pour PME",
         "description": "Planification et excution complte de la migration cloud d'une entreprise locale vers AWS.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Mise en place d'un pipeline CI/CD pour quipe de dveloppement",
         "description": "Automatisation complte du cycle de dploiement avec GitHub Actions, Docker et Kubernetes.",
         "duree_estimee": "3 mois", "niveau_requis": "Master 1"},
        {"titre": "Systme de sauvegarde automatique dans le cloud pour PME africaines",
         "description": "Solution de backup automatis et scuris pour les donnes critiques des petites entreprises.",
         "duree_estimee": "3 mois", "niveau_requis": "Licence 3"},
    ],
    "Bases de donnes": [
        {"titre": "Conception d'un entrept de donnes pour le ministre de la sant",
         "description": "Modlisation et implmentation d'un data warehouse pour l'analyse des donnes sanitaires nationales.",
         "duree_estimee": "5 mois", "niveau_requis": "Master 2"},
        {"titre": "Optimisation des requtes dans les systmes de gestion hospitalire",
         "description": "Analyse et optimisation des performances d'une base de donnes hospitalire sous forte charge.",
         "duree_estimee": "4 mois", "niveau_requis": "Master 1"},
        {"titre": "Systme d'archivage intelligent des actes d'tat civil",
         "description": "Base de donnes structure pour la numrisation et l'archivage des actes de naissance, mariage et dcs.",
         "duree_estimee": "4 mois", "niveau_requis": "Licence 3"},
    ],
}

FILIERES_VALIDES    = ["Gnie Logiciel","Rseaux et Tlcommunications","Data Science",
                       "Systmes Embarqus","Cyberscurit","Gnie Informatique"]
NIVEAUX_VALIDES     = ["Licence 3","Master 1","Master 2"]
COMPETENCES_VALIDES = list(mlb_comp.classes_)
INTERETS_VALIDES    = list(mlb_int.classes_)

MODULES_SCOLAIRES = [
    "Algorithmique","POO","Gnie Logiciel","BDD","Architecture","IA","Web",
    "Rseaux","TCP/IP","Scurit Rseau","Administration Linux","Tlcoms",
    "Statistiques","Python","Big Data","Visualisation",
    "lectronique","Programmation C","Microcontrleurs","FPGA","Temps Rel",
    "Cryptographie","Forensics","Pentesting","OSINT","Mobile","Cloud"
]

# =============================================================================
# MOTEUR DE RECOMMANDATION (logique pure, indpendante de FastAPI)
# =============================================================================

def construire_vecteur_features(filiere, niveau, competences, interets, notes):
    """
    Transforme le profil brut d'un tudiant en vecteur numrique
    identique  celui utilis pendant l'entranement.
    """
    row = {col: 0 for col in colonnes_features}

    # Filire (One-Hot)
    cle = f"filiere_{filiere}"
    if cle in row:
        row[cle] = 1

    # Niveau (One-Hot)
    cle = f"niveau_{niveau}"
    if cle in row:
        row[cle] = 1

    # Comptences (MultiLabel)
    comp_matrix = mlb_comp.transform([competences])
    for i, comp in enumerate(mlb_comp.classes_):
        cle = f"comp_{comp.replace(' ','_').replace('/','_')}"
        if cle in row:
            row[cle] = int(comp_matrix[0][i])

    # Intrts (MultiLabel)
    int_matrix = mlb_int.transform([interets])
    for i, interet in enumerate(mlb_int.classes_):
        cle = f"int_{interet.replace(' ','_').replace('/','_')}"
        if cle in row:
            row[cle] = int(int_matrix[0][i])

    # Notes normalises
    for module, note in notes.items():
        cle_note = f"note_{module.replace(' ','_').lower()}_norm"
        if cle_note in row:
            # Normalisation simple sur [8,20]
            row[cle_note] = max(0, min(1, (note - 8) / 12))

    if "moyenne_norm" in row and notes:
        moy = np.mean(list(notes.values()))
        row["moyenne_norm"] = max(0, min(1, (moy - 8) / 12))

    return pd.DataFrame([row])[colonnes_features]


def predire_domaine(filiere, niveau, competences, interets, notes, top_k=3):
    """
    Prdit les top_k domaines les plus adapts au profil de l'tudiant.
    Retourne aussi les sujets suggrs dans chaque domaine.
    """
    vecteur = construire_vecteur_features(filiere, niveau, competences, interets, notes)

    # Probabilits pour chaque domaine
    probas = modele.predict_proba(vecteur)[0]
    indices_tries = np.argsort(probas)[::-1][:top_k]

    recommandations = []
    for rang, idx in enumerate(indices_tries):
        domaine      = le_domaine.classes_[idx]
        score        = round(float(probas[idx]) * 100, 1)
        sujets_dispo = SUJETS_PAR_DOMAINE.get(domaine, [])
        # Slectionner 2 sujets adapts au niveau
        sujets_filtres = [s for s in sujets_dispo if s["niveau_requis"] == niveau]
        if not sujets_filtres:
            sujets_filtres = sujets_dispo
        sujets_choisis = random.sample(sujets_filtres, min(2, len(sujets_filtres)))

        recommandations.append({
            "rang":    rang + 1,
            "domaine": domaine,
            "score_pertinence": score,
            "sujets_suggeres":  sujets_choisis,
            "explication": generer_explication(domaine, filiere, competences, interets),
        })

    return recommandations


def generer_explication(domaine, filiere, competences, interets):
    """Gnre une explication lisible pourquoi ce domaine est recommand."""
    raisons = []
    comp_domaine = {
        "IA / Machine Learning": ["Python","TensorFlow","scikit-learn","NLP","Deep Learning","Pandas"],
        "Dveloppement Web":     ["React","Vue.js","Node.js","Django","FastAPI"],
        "Cyberscurit":         ["Pentesting","Cryptographie","OWASP","Kali Linux"],
        "Rseaux":               ["Cisco","Linux","TCP/IP","Wireshark","Firewall"],
        "Mobile":                ["Android","Flutter","React Native","Swift","Kotlin"],
        "Systmes":              ["C/C++","Arduino","Raspberry Pi","VHDL"],
        "Cloud / DevOps":        ["Docker","Kubernetes","AWS","CI/CD"],
        "Bases de donnes":      ["PostgreSQL","MongoDB","MySQL","ElasticSearch"],
    }
    matching = [c for c in competences if c in comp_domaine.get(domaine, [])]
    if matching:
        raisons.append(f"Vous matrisez {', '.join(matching[:2])}")
    if domaine.lower() in " ".join(interets).lower():
        raisons.append("correspond  vos centres d'intrt")
    if not raisons:
        raisons.append("correspond  votre filire et votre profil global")
    return "Ce domaine est recommand car : " + " et ".join(raisons) + "."


# =============================================================================
# DMONSTRATION  TEST DU MOTEUR SANS API
# =============================================================================

print("=" * 60)
print("TAPE 4  TEST DU MOTEUR DE RECOMMANDATION")
print("=" * 60)

# Profil tudiant test
profil_test = {
    "filiere":     "Data Science",
    "niveau":      "Master 1",
    "competences": ["Python", "Pandas", "scikit-learn", "PostgreSQL"],
    "interets":    ["intelligence artificielle", "data science", "statistiques"],
    "notes": {
        "Statistiques": 17.5,
        "Python":       18.0,
        "Machine Learning": 16.0,
        "BDD":          14.0,
        "Algorithmique": 15.5,
    }
}

print(f"\n Profil tudiant test :")
print(f"   Filire     : {profil_test['filiere']}")
print(f"   Niveau      : {profil_test['niveau']}")
print(f"   Comptences : {', '.join(profil_test['competences'])}")
print(f"   Intrts    : {', '.join(profil_test['interets'])}")
print(f"   Notes       : " + " | ".join(f"{k}:{v}" for k,v in profil_test['notes'].items()))

print("\n Calcul des recommandations...")
recs = predire_domaine(**profil_test, top_k=3)

print(f"\n{''*60}")
print(" RECOMMANDATIONS GNRES :")
print(f"{''*60}")

for rec in recs:
    print(f"\n  #{rec['rang']}  {rec['domaine']} "
          f"(pertinence : {rec['score_pertinence']}%)")
    print(f"       {rec['explication']}")
    for s in rec["sujets_suggeres"]:
        print(f"        \"{s['titre']}\"")
        print(f"          Dure estime : {s['duree_estimee']} | "
              f"Niveau : {s['niveau_requis']}")

# =============================================================================
# API FASTAPI
# =============================================================================

if FASTAPI_AVAILABLE:

    app = FastAPI(
        title="API Recommandation  Plateforme Mmoire",
        description="Moteur de recommandation de sujets de mmoire bas sur le profil tudiant",
        version="1.0.0",
    )

    # Autoriser les appels depuis React (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # URL de React en dveloppement
        allow_methods=["*"],
        allow_headers=["*"],
    )

    #  Schmas de donnes (Pydantic) 

    class ProfilEtudiant(BaseModel):
        filiere:     str = Field(..., example="Data Science")
        niveau:      str = Field(..., example="Master 1")
        competences: List[str] = Field(..., example=["Python","Pandas","scikit-learn"])
        interets:    List[str] = Field(..., example=["intelligence artificielle","data science"])
        notes:       dict      = Field(..., example={"Statistiques": 17.5, "Python": 18.0})
        top_k:       Optional[int] = Field(3, description="Nombre de domaines  recommander")

    class SujetSuggere(BaseModel):
        titre:          str
        description:    str
        duree_estimee:  str
        niveau_requis:  str

    class RecommandationDomaine(BaseModel):
        rang:               int
        domaine:            str
        score_pertinence:   float
        sujets_suggeres:    List[SujetSuggere]
        explication:        str

    class ReponseRecommandation(BaseModel):
        statut:           str
        nb_recommandations: int
        recommandations:  List[RecommandationDomaine]

    #  ENDPOINTS 

    @app.get("/sante", tags=["Systme"])
    def verifier_sante():
        """Vrifie que l'API fonctionne correctement."""
        return {"statut": "ok", "message": "API Recommandation oprationnelle"}

    @app.get("/modele/info", tags=["Systme"])
    def info_modele():
        """Retourne les informations sur le modle entran."""
        return {
            "modele":    meta_modele["nom_modele"],
            "accuracy":  f"{meta_modele['accuracy']}%",
            "f1_score":  f"{meta_modele['f1_score']}%",
            "cv_score":  f"{meta_modele['cv_mean']}%  {meta_modele['cv_std']}%",
            "nb_classes": meta_modele["nb_classes"],
            "classes":   meta_modele["classes"],
            "entrainement": f"{meta_modele['nb_train']} tudiants",
        }

    @app.get("/domaines", tags=["Rfrentiels"])
    def lister_domaines():
        """Retourne la liste de tous les domaines disponibles."""
        return {"domaines": list(SUJETS_PAR_DOMAINE.keys())}

    @app.get("/competences", tags=["Rfrentiels"])
    def lister_competences():
        """Retourne la liste de toutes les comptences reconnues par le modle."""
        return {"competences": COMPETENCES_VALIDES}

    @app.get("/sujets/{domaine}", tags=["Rfrentiels"])
    def lister_sujets(domaine: str):
        """Retourne les sujets disponibles pour un domaine donn."""
        if domaine not in SUJETS_PAR_DOMAINE:
            raise HTTPException(status_code=404, detail=f"Domaine '{domaine}' introuvable")
        return {"domaine": domaine, "sujets": SUJETS_PAR_DOMAINE[domaine]}

    @app.post("/recommander", response_model=ReponseRecommandation, tags=["Recommandation"])
    def recommander(profil: ProfilEtudiant):
        """
        Endpoint principal : reoit le profil d'un tudiant et retourne
        les domaines et sujets de mmoire les plus adapts.

        Appel par le frontend React via :
          fetch('http://localhost:8001/recommander', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(profil)
          })
        """
        # Validation basique
        if profil.filiere not in FILIERES_VALIDES:
            raise HTTPException(400, f"Filire invalide. Valides: {FILIERES_VALIDES}")
        if profil.niveau not in NIVEAUX_VALIDES:
            raise HTTPException(400, f"Niveau invalide. Valides: {NIVEAUX_VALIDES}")

        comp_invalides = [c for c in profil.competences if c not in COMPETENCES_VALIDES]
        if comp_invalides:
            raise HTTPException(400, f"Comptences inconnues: {comp_invalides}")

        # Recommandation
        recs = predire_domaine(
            filiere=profil.filiere,
            niveau=profil.niveau,
            competences=profil.competences,
            interets=profil.interets,
            notes=profil.notes,
            top_k=min(profil.top_k or 3, 5),
        )

        return {
            "statut":             "succes",
            "nb_recommandations": len(recs),
            "recommandations":    recs,
        }

    print("\n" + "=" * 60)
    print(" API FastAPI configure")
    print("   Pour lancer : uvicorn etape4_api_recommandation:app --reload --port 8001")
    print("   Documentation : http://localhost:8001/docs")
    print("=" * 60)

else:
    print("\n  Pour activer l'API, installer : pip install fastapi uvicorn")
    print("   Le moteur de recommandation fonctionne sans l'API.\n")

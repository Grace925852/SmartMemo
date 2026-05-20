import os
os.makedirs("../../ia_models/archive", exist_ok=True)
"""
=============================================================
MODULE SMART ARCHIVE
TAPE 3  MOTEUR COMPLET + RECHERCHE + RECOMMANDATION + API
=============================================================

FONCTIONNALITS :
-----------------
  1. RECHERCHE SMANTIQUE
     Requte texte libre  top-K mmoires les plus pertinents
     Fonctionne mme si les mots exacts ne sont pas dans les titres

  2. RECHERCHE PAR FILTRES
     Domaine, anne, mthodologie, niveau, tags

  3. RECOMMANDATION
     "Vous consultez MEM-0042  voici 5 mmoires similaires"
     Base sur la similarit vectorielle + mme cluster

  4. AUTO-TAGGING  LA VOLE
     Nouveau mmoire soumis  tags assigns automatiquement

  5. AJOUT AU CORPUS
     Aprs soutenance  mmoire index automatiquement

API FASTAPI  PORT 8007
  POST /rechercher               Recherche smantique
  GET  /memoire/{id}             Dtails d'un mmoire
  GET  /recommandations/{id}     Mmoires similaires
  POST /auto-tagger              Gnrer des tags pour un texte
  POST /indexer                  Ajouter un nouveau mmoire
  GET  /clusters                 Clusters thmatiques
  GET  /statistiques             Tableau de bord de l'archive
"""

import joblib
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from typing import Optional, List

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

#  CHARGEMENT 

tfidf  = joblib.load("../../ia_models/archive/tfidf_vectorizer.pkl")
svd    = joblib.load("../../ia_models/archive/svd_lsa.pkl")
kmeans = joblib.load("../../ia_models/archive/kmeans_clusters.pkl")

index_vecteurs = np.load("../../ia_models/archive/index_vecteurs.npy")

with open("../../ia_models/archive/index_metadata.json", encoding="utf-8") as f:
    meta_index = json.load(f)

with open("../../ia_models/archive/meta_modele.json", encoding="utf-8") as f:
    meta = json.load(f)

df_memoires = pd.read_csv("data/memoires_indexes.csv")

N_MEMOIRES = len(meta_index["id_memoire"])


#  UTILITAIRES 

def vectoriser(texte: str) -> np.ndarray:
    v_tfidf = tfidf.transform([str(texte)])
    v_lsa   = svd.transform(v_tfidf)
    return normalize(v_lsa, norm="l2")[0]


def meta_a_dict(idx: int) -> dict:
    """Retourne les mtadonnes d'un mmoire depuis son index."""
    return {
        "id_memoire":   meta_index["id_memoire"][idx],
        "titre":        meta_index["titre"][idx],
        "domaine":      meta_index["domaine"][idx],
        "methodologie": meta_index["methodologie"][idx],
        "niveau":       meta_index["niveau"][idx],
        "annee":        int(meta_index["annee"][idx]),
        "auteur":       meta_index["auteur"][idx],
        "tags":         meta_index["tags"][idx].split("|")[:8],
        "cluster_id":   int(meta_index["cluster_id"][idx]),
        "cluster_nom":  meta_index["cluster_nom"][idx],
        "note":         round(float(meta_index["note"][idx]), 2),
        "est_public":   bool(meta_index["est_public"][idx]),
    }


def appliquer_filtres(indices: list, filtres: dict) -> list:
    """Filtre une liste d'indices selon les critres donns."""
    resultat = []
    for idx in indices:
        dom   = meta_index["domaine"][idx]
        annee = int(meta_index["annee"][idx])
        niv   = meta_index["niveau"][idx]
        methodo = meta_index["methodologie"][idx]
        tags    = meta_index["tags"][idx]
        public  = bool(meta_index["est_public"][idx])

        if not public:
            continue
        if filtres.get("domaine") and dom != filtres["domaine"]:
            continue
        if filtres.get("annee_min") and annee < filtres["annee_min"]:
            continue
        if filtres.get("annee_max") and annee > filtres["annee_max"]:
            continue
        if filtres.get("niveau") and niv != filtres["niveau"]:
            continue
        if filtres.get("methodologie") and methodo != filtres["methodologie"]:
            continue
        if filtres.get("tag") and filtres["tag"].lower() not in tags.lower():
            continue
        resultat.append(idx)
    return resultat


# 
# MOTEUR DE RECHERCHE SMANTIQUE
# 

def rechercher(
    requete: str,
    top_k:   int  = 5,
    domaine: Optional[str] = None,
    annee_min: Optional[int] = None,
    annee_max: Optional[int] = None,
    niveau:  Optional[str] = None,
    methodologie: Optional[str] = None,
    tag:     Optional[str] = None,
) -> dict:
    """
    Recherche smantique dans l'archive.

    FONCTIONNEMENT :
    1. La requte texte est vectorise (TF-IDF + LSA)
    2. On calcule la similarit cosinus avec TOUS les mmoires indexs
    3. On trie par score dcroissant
    4. On applique les filtres
    5. On retourne les top_k rsultats avec snippets

    C'est l'quivalent d'une requte FAISS mais en numpy pur.
    """
    vecteur_requete = vectoriser(requete)

    # Similarit cosinus = produit matriciel (vecteurs normaliss)
    scores = index_vecteurs @ vecteur_requete

    # Top-K  3 pour avoir assez aprs filtrage
    top_indices_bruts = np.argsort(scores)[::-1][:top_k * 3]

    # Application des filtres
    filtres = {
        "domaine": domaine, "annee_min": annee_min, "annee_max": annee_max,
        "niveau": niveau, "methodologie": methodologie, "tag": tag,
    }
    indices_filtres = appliquer_filtres(top_indices_bruts.tolist(), filtres)[:top_k]

    resultats = []
    for idx in indices_filtres:
        m = meta_a_dict(idx)
        # Snippet : extrait de la description correspondant  la requte
        desc = df_memoires.iloc[idx]["description"] \
               if idx < len(df_memoires) else ""
        m["score_pertinence"] = round(float(scores[idx]) * 100, 1)
        m["snippet"]          = desc[:200] + "..." if len(desc) > 200 else desc
        resultats.append(m)

    return {
        "requete":           requete,
        "nb_resultats":      len(resultats),
        "filtres_appliques": {k:v for k,v in filtres.items() if v},
        "resultats":         resultats,
    }


# 
# MOTEUR DE RECOMMANDATION
# 

def recommander(id_memoire: str, top_k: int = 5) -> dict:
    """
    Recommande des mmoires similaires  celui consult.

    STRATGIE :
    1. Chercher l'index du mmoire dans la base
    2. Calculer la similarit avec tous les autres mmoires
    3. Exclure le mmoire lui-mme et les trs faibles scores
    4. Bonus +20% pour les mmoires du mme cluster thmatique
    """
    ids = meta_index["id_memoire"]
    if id_memoire not in ids:
        return {"erreur": f"Mmoire {id_memoire} non trouv"}

    idx_source = ids.index(id_memoire)
    vecteur    = index_vecteurs[idx_source]
    cluster    = int(meta_index["cluster_id"][idx_source])

    scores = index_vecteurs @ vecteur

    # Bonus pour le mme cluster
    scores_bonus = scores.copy()
    for i, cid in enumerate(meta_index["cluster_id"]):
        if int(cid) == cluster and i != idx_source:
            scores_bonus[i] *= 1.2  # bonus 20%

    # Exclure le mmoire source et les non-publics
    scores_bonus[idx_source] = -1
    for i, pub in enumerate(meta_index["est_public"]):
        if not bool(pub):
            scores_bonus[i] = -1

    top_indices = np.argsort(scores_bonus)[::-1][:top_k]

    recommandations = []
    for idx in top_indices:
        if scores_bonus[idx] <= 0:
            continue
        m = meta_a_dict(idx)
        m["score_similarite"] = round(float(scores[idx]) * 100, 1)
        m["meme_cluster"]     = int(meta_index["cluster_id"][idx]) == cluster
        recommandations.append(m)

    source = meta_a_dict(idx_source)
    return {
        "memoire_source":     source,
        "nb_recommandations": len(recommandations),
        "recommandations":    recommandations,
    }


# 
# AUTO-TAGGING
# 

def auto_tagger(titre: str, description: str, top_k: int = 8) -> dict:
    """
    Gnre automatiquement des tags pour un nouveau mmoire.
    Combine TF-IDF keywords + clustering pour identifier le thme.
    """
    texte = f"{titre} {description}"

    # Tags par TF-IDF
    vecteur_tfidf = tfidf.transform([texte])
    feature_names = tfidf.get_feature_names_out()
    scores_tfidf  = vecteur_tfidf.toarray()[0]
    top_idx       = scores_tfidf.argsort()[::-1][:top_k]
    tags_tfidf    = [feature_names[i] for i in top_idx if scores_tfidf[i] > 0]

    # Cluster prdit
    vecteur_lsa = svd.transform(vecteur_tfidf)
    vecteur_norm = normalize(vecteur_lsa, norm="l2")
    cluster_pred = int(kmeans.predict(vecteur_norm)[0])
    cluster_nom  = meta["clusters"].get(str(cluster_pred), f"Cluster {cluster_pred}")

    # Domaine prdit (cluster dominant)
    return {
        "tags_suggeres":  tags_tfidf[:8],
        "cluster_predit": cluster_pred,
        "domaine_predit": cluster_nom,
        "nb_tags":        len(tags_tfidf),
    }


# 
# AJOUT AU CORPUS
# 

def indexer_nouveau_memoire(id_mem: str, titre: str, description: str,
                             domaine: str, methodologie: str,
                             niveau: str, annee: int,
                             auteur: str, note: float) -> dict:
    """Indexe un nouveau mmoire soutenu dans l'archive."""
    global index_vecteurs

    texte       = f"{titre} {description}"
    vecteur     = vectoriser(texte)
    tagging     = auto_tagger(titre, description)
    cluster_id  = tagging["cluster_predit"]
    cluster_nom = tagging["domaine_predit"]

    index_vecteurs = np.vstack([index_vecteurs, vecteur.reshape(1, -1)])

    for key, val in [
        ("id_memoire", id_mem), ("titre", titre), ("domaine", domaine),
        ("methodologie", methodologie), ("niveau", niveau), ("annee", annee),
        ("auteur", auteur), ("tags", "|".join(tagging["tags_suggeres"])),
        ("cluster_id", cluster_id), ("cluster_nom", cluster_nom),
        ("note", note), ("est_public", True),
    ]:
        meta_index[key].append(val)

    np.save("../../ia_models/archive/index_vecteurs.npy", index_vecteurs)

    return {
        "message":      f"Mmoire {id_mem} index avec succs",
        "tags_assignes": tagging["tags_suggeres"],
        "cluster":       cluster_nom,
        "nouveau_total": len(meta_index["id_memoire"]),
    }


# 
# DMONSTRATION
# 

print("="*65)
print("MODULE SMART ARCHIVE  DMONSTRATION")
print("="*65)

#  TEST 1 : Recherche smantique 
print("\n TEST 1  Recherche smantique")
print(""*65)
REQUETES = [
    "application mobile sant zones rurales Afrique",
    "scurit rseau entreprise dtection intrusion",
    "machine learning prdiction donnes acadmiques",
]
for req in REQUETES:
    res = rechercher(req, top_k=3)
    print(f"\n  Requte : \"{req}\"")
    print(f"  {res['nb_resultats']} rsultats trouvs :")
    for r in res["resultats"]:
        print(f"    [{r['score_pertinence']:5.1f}%] {r['titre'][:50]}"
              f"  ({r['domaine']}, {r['annee']})")

#  TEST 2 : Recherche avec filtres 
print("\n\n TEST 2  Recherche avec filtres (domaine + anne)")
print(""*65)
res_filtre = rechercher(
    "systme automatique intelligent",
    top_k=4,
    domaine="IA / Machine Learning",
    annee_min=2022,
)
print(f"  Requte filtre : domaine=IA, annee2022")
print(f"  {res_filtre['nb_resultats']} rsultats :")
for r in res_filtre["resultats"]:
    print(f"    [{r['score_pertinence']:5.1f}%] {r['titre'][:50]}"
          f"  ({r['annee']})")

#  TEST 3 : Recommandation 
print("\n\n TEST 3  Recommandation de mmoires similaires")
print(""*65)
id_test = meta_index["id_memoire"][0]
rec     = recommander(id_test, top_k=4)
print(f"  Source  : {rec['memoire_source']['titre'][:50]}")
print(f"  Domaine : {rec['memoire_source']['domaine']}")
print(f"\n  Mmoires recommands :")
for r in rec["recommandations"]:
    cluster_flag = " mme cluster" if r["meme_cluster"] else ""
    print(f"    [{r['score_similarite']:5.1f}%] {r['titre'][:45]}"
          f"  {cluster_flag}")

#  TEST 4 : Auto-tagging 
print("\n\n  TEST 4  Auto-tagging d'un nouveau mmoire")
print(""*65)
tags_res = auto_tagger(
    titre="Dveloppement d'un systme de paiement NFC scuris pour smartphones Android",
    description="Ce projet implmente un systme de paiement sans contact bas sur NFC "
                "avec chiffrement AES-256 et authentification biomtrique sur Android.",
)
print(f"  Tags suggrs  : {', '.join(tags_res['tags_suggeres'])}")
print(f"  Domaine prdit : {tags_res['domaine_predit']}")

#  TEST 5 : Indexation d'un nouveau mmoire 
print("\n\n TEST 5  Indexation d'un nouveau mmoire soutenu")
print(""*65)
res_idx = indexer_nouveau_memoire(
    id_mem="MEM-NOUVEAU-001",
    titre="Plateforme de microfinance mobile pour femmes entrepreneures",
    description="Application mobile combinant mobile money et crdit scoring "
                "par machine learning pour faciliter l'accs au financement "
                "des femmes entrepreneures en Afrique de l'Ouest.",
    domaine="Mobile", methodologie="Recherche applique",
    niveau="Master 2", annee=2024,
    auteur="Abena KOFI", note=17.5,
)
print(f"  {res_idx['message']}")
print(f"  Tags assigns : {', '.join(res_idx['tags_assignes'])}")
print(f"  Cluster       : {res_idx['cluster']}")
print(f"  Corpus total  : {res_idx['nouveau_total']} mmoires")

print(f"\n{'='*65}")
print(f"   Archive : {N_MEMOIRES} mmoires indexs")
print(f"   Clusters : {meta['nb_clusters']} thmes")
print(f"   Variance explique : {meta['variance_expliquee']}%")
print("="*65)

#  API FASTAPI 

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="API Smart Archive  Plateforme Mmoire",
        version="1.0.0",
        description="Archive intelligente avec recherche smantique et recommandation"
    )
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])

    class RequeteRecherche(BaseModel):
        texte:        str = Field(..., min_length=3)
        top_k:        int = 5
        domaine:      Optional[str] = None
        annee_min:    Optional[int] = None
        annee_max:    Optional[int] = None
        niveau:       Optional[str] = None
        methodologie: Optional[str] = None
        tag:          Optional[str] = None

    class NouveauMemoire(BaseModel):
        id_memoire:   str
        titre:        str
        description:  str
        domaine:      str
        methodologie: str
        niveau:       str
        annee:        int
        auteur:       str
        note:         float

    class TexteATagger(BaseModel):
        titre:       str
        description: str

    @app.get("/sante", tags=["Systme"])
    def sante():
        return {"statut": "ok", "module": "Smart Archive",
                "memoires_indexes": len(meta_index["id_memoire"])}

    @app.get("/statistiques", tags=["Tableau de bord"])
    def statistiques():
        """Tableau de bord de l'archive."""
        ids  = meta_index["id_memoire"]
        doms = meta_index["domaine"]
        anns = meta_index["annee"]
        dom_counts  = {}
        for d in doms: dom_counts[d]  = dom_counts.get(d, 0)  + 1
        ann_counts  = {}
        for a in anns: ann_counts[int(a)] = ann_counts.get(int(a), 0) + 1
        return {
            "nb_memoires":         len(ids),
            "nb_clusters":         meta["nb_clusters"],
            "variance_expliquee":  meta["variance_expliquee"],
            "repartition_domaines": dict(sorted(dom_counts.items(),
                                                key=lambda x:-x[1])),
            "repartition_annees":  dict(sorted(ann_counts.items())),
            "clusters":            meta["clusters"],
        }

    @app.post("/rechercher", tags=["Recherche"])
    def endpoint_rechercher(req: RequeteRecherche):
        """
        Recherche smantique dans l'archive.
        Comprend le SENS de la requte, pas juste les mots exacts.
        Appel quand l'utilisateur tape dans la barre de recherche React.
        """
        return rechercher(
            req.texte, req.top_k, req.domaine, req.annee_min,
            req.annee_max, req.niveau, req.methodologie, req.tag
        )

    @app.get("/memoire/{id_memoire}", tags=["Mmoires"])
    def get_memoire(id_memoire: str):
        """Dtails complets d'un mmoire archiv."""
        ids = meta_index["id_memoire"]
        if id_memoire not in ids:
            raise HTTPException(404, f"Mmoire {id_memoire} non trouv")
        idx  = ids.index(id_memoire)
        m    = meta_a_dict(idx)
        row  = df_memoires[df_memoires["id_memoire"] == id_memoire]
        if not row.empty:
            m["description"] = row.iloc[0].get("description","")
            m["resume"]      = row.iloc[0].get("resume","")
        return m

    @app.get("/recommandations/{id_memoire}", tags=["Recommandation"])
    def get_recommandations(id_memoire: str, top_k: int = 5):
        """
        Mmoires similaires  celui consult.
        Affich dans le panneau latral React "Vous pourriez aussi aimer".
        """
        return recommander(id_memoire, top_k)

    @app.post("/auto-tagger", tags=["Auto-tagging"])
    def endpoint_auto_tagger(req: TexteATagger):
        """Gnre des tags automatiquement pour un texte donn."""
        return auto_tagger(req.titre, req.description)

    @app.post("/indexer", tags=["Indexation"])
    def endpoint_indexer(req: NouveauMemoire):
        """
        Indexe un nouveau mmoire soutenu dans l'archive.
        Appel automatiquement aprs validation de la soutenance.
        """
        return indexer_nouveau_memoire(
            req.id_memoire, req.titre, req.description,
            req.domaine, req.methodologie, req.niveau,
            req.annee, req.auteur, req.note
        )

    @app.get("/clusters", tags=["Clusters"])
    def get_clusters():
        """Retourne les clusters thmatiques et leur contenu."""
        clusters_detail = {}
        for cid_str, cnom in meta["clusters"].items():
            cid  = int(cid_str)
            idxs = [i for i,c in enumerate(meta_index["cluster_id"]) if int(c)==cid]
            clusters_detail[cid_str] = {
                "nom":        cnom,
                "nb_memoires": len(idxs),
                "exemples":   [meta_index["titre"][i] for i in idxs[:3]],
            }
        return {"nb_clusters": meta["nb_clusters"], "clusters": clusters_detail}

    @app.get("/domaines", tags=["Rfrentiels"])
    def get_domaines():
        return {"domaines": list(set(meta_index["domaine"]))}

    print("\n API Smart Archive prte.")
    print("   Lancer : uvicorn etape3_api_archive:app --reload --port 8007")
    print("   Docs   : http://localhost:8007/docs")

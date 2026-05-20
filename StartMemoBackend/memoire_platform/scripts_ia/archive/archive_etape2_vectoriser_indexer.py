import os
os.makedirs("../../ia_models/archive", exist_ok=True)
"""
=============================================================
MODULE SMART ARCHIVE
TAPE 2  VECTORISATION + INDEX SMANTIQUE + CLUSTERING
=============================================================

3 FONCTIONS CONSTRUITES ICI :
-------------------------------

A) INDEX SMANTIQUE (TF-IDF + LSA)
   Chaque mmoire  vecteur 80 dimensions
   Stock dans une matrice (300  80)
   Recherche = produit matriciel en quelques ms

B) CLUSTERING THMATIQUE (K-Means)
   Regroupe automatiquement les mmoires en clusters thmatiques
   Sans qu'un humain ait  les classer manuellement
   Utilis pour : "Vous consultez un mmoire du cluster IoT
    voici d'autres mmoires de ce cluster"

C) AUTO-TAGGING AMLIOR (TF-IDF Keywords)
   Extrait les mots-cls les plus reprsentatifs de chaque mmoire
   pour enrichir les tags assigns  l'tape 1
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
import joblib
import json

print("=" * 60)
print("MODULE SMART ARCHIVE  TAPE 2 : VECTORISATION")
print("=" * 60)

df = pd.read_csv("data/memoires_archives.csv")
print(f"\n {len(df)} mmoires chargs")

#  A. VECTORISATION TF-IDF + LSA 

print("\n  A  Vectorisation TF-IDF + LSA...")

corpus = df["texte_complet"].fillna("").tolist()

tfidf = TfidfVectorizer(
    max_features=4000,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.80,
    strip_accents="unicode",
    lowercase=True,
)
X_tfidf = tfidf.fit_transform(corpus)
print(f"   TF-IDF : {X_tfidf.shape[0]} docs  {X_tfidf.shape[1]} features")

svd = TruncatedSVD(n_components=80, random_state=42)
X_lsa = svd.fit_transform(X_tfidf)
variance = round(svd.explained_variance_ratio_.sum() * 100, 1)
print(f"   LSA    : {X_lsa.shape[0]} docs  {X_lsa.shape[1]} dimensions")
print(f"   Variance explique : {variance}%")

X_norm = normalize(X_lsa, norm="l2")
np.save("../../ia_models/archive/index_vecteurs.npy", X_norm)
print(f"    Index vectoriel sauvegard : {X_norm.shape}")

#  B. CLUSTERING K-MEANS 

print("\n  B  Clustering thmatique (K-Means)...")

N_CLUSTERS = 8   # 1 cluster  1 domaine thmatique

kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
labels_clusters = kmeans.fit_predict(X_norm)

df["cluster_id"] = labels_clusters

# Nommer les clusters selon leur domaine dominant
cluster_labels = {}
for i in range(N_CLUSTERS):
    mask     = df["cluster_id"] == i
    domaines = df[mask]["domaine"].value_counts()
    cluster_labels[i] = domaines.index[0] if len(domaines) > 0 else f"Cluster {i}"

df["cluster_nom"] = df["cluster_id"].map(cluster_labels)

print(f"   {N_CLUSTERS} clusters identifis :")
for cid, cnom in cluster_labels.items():
    count = (df["cluster_id"] == cid).sum()
    barre = "" * (count // 4)
    print(f"   Cluster {cid} ({cnom:<30}) {count:3d} mmoires  {barre}")

#  C. AUTO-TAGGING AMLIOR 

print("\n  C  Extraction de mots-cls TF-IDF (auto-tagging amlior)...")

feature_names = tfidf.get_feature_names_out()

def extraire_mots_cles(idx_doc: int, top_k: int = 5) -> list:
    """Extrait les top_k mots-cls les plus reprsentatifs d'un document."""
    vecteur_tfidf = X_tfidf[idx_doc].toarray()[0]
    top_indices   = vecteur_tfidf.argsort()[::-1][:top_k]
    mots_cles     = [feature_names[i] for i in top_indices
                     if vecteur_tfidf[i] > 0]
    return mots_cles


# Enrichir les tags existants avec les mots-cls TF-IDF
tags_enrichis = []
for idx in range(len(df)):
    tags_existants = set(df.iloc[idx]["tags"].split("|"))
    mots_cles      = extraire_mots_cles(idx, top_k=5)
    tags_enrichis_set = tags_existants | set(mots_cles)
    tags_enrichis.append("|".join(sorted(tags_enrichis_set)))

df["tags_enrichis"] = tags_enrichis

#  SAUVEGARDE FINALE 

df.to_csv("data/memoires_indexes.csv", index=False)
joblib.dump(tfidf,  "../../ia_models/archive/tfidf_vectorizer.pkl")
joblib.dump(svd,    "../../ia_models/archive/svd_lsa.pkl")
joblib.dump(kmeans, "../../ia_models/archive/kmeans_clusters.pkl")

# Mtadonnes de l'index pour la recherche
meta_index = {
    "id_memoire":   df["id_memoire"].tolist(),
    "titre":        df["titre"].tolist(),
    "domaine":      df["domaine"].tolist(),
    "methodologie": df["methodologie"].tolist(),
    "niveau":       df["niveau"].tolist(),
    "annee":        df["annee"].tolist(),
    "auteur":       df["auteur"].tolist(),
    "tags":         df["tags_enrichis"].tolist(),
    "cluster_id":   df["cluster_id"].tolist(),
    "cluster_nom":  df["cluster_nom"].tolist(),
    "note":         df["note_soutenance"].tolist(),
    "est_public":   df["est_public"].tolist(),
}
with open("../../ia_models/archive/index_metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta_index, f, ensure_ascii=False)

cluster_info = {str(k): v for k, v in cluster_labels.items()}
meta = {
    "nb_memoires":         len(df),
    "nb_clusters":         N_CLUSTERS,
    "clusters":            cluster_info,
    "variance_expliquee":  variance,
    "dim_embedding":       80,
    "nb_features_tfidf":   X_tfidf.shape[1],
}
with open("../../ia_models/archive/meta_modele.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n Index vectoriel        modeles/index_vecteurs.npy")
print(f" TF-IDF vectorizer      modeles/tfidf_vectorizer.pkl")
print(f" SVD/LSA                modeles/svd_lsa.pkl")
print(f" K-Means clusters       modeles/kmeans_clusters.pkl")
print(f" Mtadonnes index      modeles/index_metadata.json")
print(f" Mmoires indexs       data/memoires_indexes.csv")
print("\n" + "="*60)
print("  TAPE 2 TERMINE  Archive vectorise et indexe")
print("="*60)

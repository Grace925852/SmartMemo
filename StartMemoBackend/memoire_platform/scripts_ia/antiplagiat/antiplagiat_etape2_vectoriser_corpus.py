"""
=============================================================
MODULE ANTI-PLAGIAT AVANC
TAPE 2  VECTORISATION TF-IDF + LSA + INDEX VECTORIEL
=============================================================

COMMENT FONCTIONNE LA VECTORISATION ?
--------------------------------------

TAPE A  TF-IDF (Term Frequency  Inverse Document Frequency)
  Transforme chaque texte en vecteur de frquences de mots.
  Ex : "dtection de fraude"  [0, 0.45, 0, 0.32, 0.28, ...]

  - TF = frquence du mot dans le document
  - IDF = raret du mot dans tous les documents
   Les mots rares et informatifs ont plus de poids

TAPE B  SVD Tronque (Truncated SVD = LSA)
  Rduit les vecteurs TF-IDF de 5000 dimensions  100 dimensions.
  Ce processus capture les RELATIONS SMANTIQUES entre les mots.
  Ex : "fraude" et "arnaque" se retrouvent proches dans l'espace vectoriel

  C'est l'quivalent lger de BERT, sans GPU ncessaire.

TAPE C  NORMALISATION L2
  Chaque vecteur est normalis pour que la similarit cosinus
  soit calculable comme un simple produit scalaire.

TAPE D  INDEX VECTORIEL (numpy-based)
  Tous les vecteurs des 200 mmoires archivs sont stocks
  dans une matrice. La recherche de similarit = multiplication matricielle.
  En production : remplacer par FAISS pour des milliers de documents.

SIMILARIT COSINUS :
  cos(A, B) = (A  B) / (|A|  |B|)
   1.0 = textes identiques
   0.0 = textes compltement diffrents
   En pratique : > 0.80 = plagiat fort, 0.40-0.80 = suspicion

CE SCRIPT PRODUIT :
  - Le vectoriseur TF-IDF entran sur le corpus
  - Le rducteur SVD (LSA)
  - L'index vectoriel de tous les mmoires archivs
  - Les features numriques pour le modle de classification
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import json

print("=" * 60)
print("MODULE ANTI-PLAGIAT  TAPE 2 : VECTORISATION")
print("=" * 60)

df_archives  = pd.read_csv("data/memoires_archives.csv")
df_nouvelles = pd.read_csv("data/nouvelles_soumissions.csv")
df_paires    = pd.read_csv("data/paires_entrainement.csv")

print(f"\n Corpus archiv  : {len(df_archives)} mmoires")
print(f"   Nouvelles sub.  : {len(df_nouvelles)}")
print(f"   Paires d'entr.  : {len(df_paires)}")

#  TAPE A : ENTRANEMENT TF-IDF 

print("\n  TAPE A  Entranement TF-IDF sur le corpus archiv...")

# On entrane le TF-IDF UNIQUEMENT sur les textes archivs
# (comme en production : le modle connat uniquement les anciens mmoires)
corpus_archives = df_archives["texte_complet"].fillna("").tolist()

tfidf = TfidfVectorizer(
    max_features=3000,     # Garder les 3000 mots les plus informatifs
    ngram_range=(1, 2),    # Unigrammes + bigrammes ("machine learning" = 1 feature)
    min_df=2,              # Ignorer les mots qui n'apparaissent qu'une fois
    max_df=0.85,           # Ignorer les mots trop frquents (>85% des docs)
    strip_accents="unicode",
    lowercase=True,
)
X_tfidf_archives = tfidf.fit_transform(corpus_archives)
print(f"   TF-IDF : {X_tfidf_archives.shape[0]} docs  {X_tfidf_archives.shape[1]} features")

#  TAPE B : RDUCTION DIMENSIONNELLE (LSA) 

print("\n  TAPE B  Rduction LSA (SVD) : 3000  100 dimensions...")

svd = TruncatedSVD(n_components=100, random_state=42)
X_lsa_archives = svd.fit_transform(X_tfidf_archives)

# Variance explique (mesure la qualit de la rduction)
variance_expliquee = round(svd.explained_variance_ratio_.sum() * 100, 1)
print(f"   LSA : {X_lsa_archives.shape[0]} docs  {X_lsa_archives.shape[1]} dimensions")
print(f"   Variance explique : {variance_expliquee}% (objectif > 60%)")

#  TAPE C : NORMALISATION L2 

print("\n  TAPE C  Normalisation L2 des vecteurs...")

X_norm_archives = normalize(X_lsa_archives, norm="l2")
print(f"   Index vectoriel : {X_norm_archives.shape}  prt pour la recherche")

#  TAPE D : INDEX VECTORIEL DES ARCHIVES 

print("\n  TAPE D  Construction de l'index vectoriel...")

# Sauvegarder l'index + les mtadonnes associes
index_data = {
    "id_memoire": df_archives["id_memoire"].tolist(),
    "titre":      df_archives["titre"].tolist(),
    "domaine":    df_archives["domaine"].tolist(),
    "annee":      df_archives["annee"].tolist(),
    "auteur":     df_archives["auteur"].tolist(),
}
np.save("modeles/index_vecteurs.npy", X_norm_archives)
with open("modeles/index_metadata.json", "w", encoding="utf-8") as f:
    json.dump(index_data, f, ensure_ascii=False)

print(f"   [OK] Index sauvegard : {X_norm_archives.shape[0]} vecteurs de dim {X_norm_archives.shape[1]}")

#  PRPARATION DES FEATURES POUR LE CLASSIFICATEUR 

print("\n  Construction des features pour le classificateur ML...")

def vectoriser_texte(texte):
    """Transforme un texte en vecteur LSA normalis."""
    vec_tfidf = tfidf.transform([str(texte)])
    vec_lsa   = svd.transform(vec_tfidf)
    return normalize(vec_lsa, norm="l2")[0]


def similarite_cosinus(vA, vB):
    """Calcule la similarit cosinus entre deux vecteurs normaliss."""
    return float(np.dot(vA, vB))


def extraire_features_paire(texte_a, texte_b):
    """
    Extrait les features numriques d'une paire de textes.
    Ce sont ces features que le classificateur ML utilise.
    """
    vA = vectoriser_texte(texte_a)
    vB = vectoriser_texte(texte_b)

    sim_cosinus = similarite_cosinus(vA, vB)

    # Features supplmentaires
    mots_a = set(str(texte_a).lower().split())
    mots_b = set(str(texte_b).lower().split())
    intersection = mots_a & mots_b
    union         = mots_a | mots_b

    jaccard = len(intersection) / max(len(union), 1)

    # Diffrence de longueur (les textes trs diffrents en longueur = moins de plagiat)
    len_a = len(str(texte_a).split())
    len_b = len(str(texte_b).split())
    ratio_longueur = min(len_a, len_b) / max(len_a, len_b, 1)

    # Proportion de mots communs rares (mots informatifs partags)
    mots_rares_communs = len([m for m in intersection if len(m) > 6])

    # Score de similarit avec le 2me texte dans l'index complet
    scores_index = X_norm_archives @ vB
    top_score    = float(np.max(scores_index))

    return {
        "sim_cosinus":           round(sim_cosinus, 4),
        "jaccard":               round(jaccard, 4),
        "ratio_longueur":        round(ratio_longueur, 4),
        "mots_rares_communs":    mots_rares_communs,
        "top_score_index":       round(top_score, 4),
        "diff_sim_top":          round(abs(sim_cosinus - top_score), 4),
    }


print("   Vectorisation des 700 paires (peut prendre quelques secondes)...")
features_list = []
for _, row in df_paires.iterrows():
    f = extraire_features_paire(row["texte_a"], row["texte_b"])
    features_list.append(f)

df_features = pd.DataFrame(features_list)
df_features["categorie_similarite"] = df_paires["categorie_similarite"].values
df_features["score_similarite"]     = df_paires["score_similarite"].values

print(f"   [OK] Features calcules : {df_features.shape}")

#  SPLIT TRAIN / TEST 

feature_cols = ["sim_cosinus","jaccard","ratio_longueur",
                "mots_rares_communs","top_score_index","diff_sim_top"]
X = df_features[feature_cols]
le = LabelEncoder()
y  = le.fit_transform(df_features["categorie_similarite"])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

X_train.to_csv("data/X_train.csv", index=False)
X_test.to_csv("data/X_test.csv",  index=False)
np.save("data/y_train.npy", y_train)
np.save("data/y_test.npy",  y_test)

print(f"\n Train : {len(X_train)} | Test : {len(X_test)}")
print(f"   Classes : {dict(zip(le.classes_, le.transform(le.classes_)))}")

#  SAUVEGARDE DES ARTEFACTS 

joblib.dump(tfidf, "modeles/tfidf_vectorizer.pkl")
joblib.dump(svd,   "modeles/svd_lsa.pkl")
joblib.dump(le,    "modeles/label_encoder_similarite.pkl")

with open("modeles/feature_cols.json", "w") as f:
    json.dump(feature_cols, f)

# Statistiques de la feature la plus importante : sim_cosinus
print(f"\n[STAT] Distribution de la similarit cosinus par catgorie :")
print("" * 55)
df_stats = df_features.groupby("categorie_similarite")["sim_cosinus"].agg(["mean","min","max"])
for cat, row in df_stats.iterrows():
    print(f"  {cat:<20} moy:{row['mean']:.3f}  min:{row['min']:.3f}  max:{row['max']:.3f}")

print(f"\n[OK] Vectoriseur TF-IDF   modeles/tfidf_vectorizer.pkl")
print(f"[OK] Rducteur SVD/LSA   modeles/svd_lsa.pkl")
print(f"[OK] Index vectoriel      modeles/index_vecteurs.npy")
print(f"[OK] Mtadonnes index    modeles/index_metadata.json")
print("\n" + "="*60)
print("  TAPE 2 TERMINE  Corpus vectoris et index")
print("="*60)

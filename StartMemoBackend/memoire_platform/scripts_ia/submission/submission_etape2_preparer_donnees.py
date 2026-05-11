import os
os.makedirs("../../ia_models/submission", exist_ok=True)
"""
=============================================================
MODULE SUBMISSION WORKFLOW
TAPE 2  PRPARATION DES DONNES
=============================================================

TRANSFORMATIONS :
-----------------
Toutes nos features sont dj numriques.
On applique juste :
  1. Normalisation MinMax des valeurs continues
  2. Encodage de la variable cible (VALIDEE / CORRECTIONS / REJETEE)
  3. Split train/test stratifi
  4. Analyse des corrlations pour comprendre ce qui influence le statut
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import json

print("=" * 60)
print("MODULE SUBMISSION  TAPE 2 : PRPARATION")
print("=" * 60)

df = pd.read_csv("data/soumissions_entrainement.csv")
print(f"\n {len(df)} soumissions | {df.shape[1]} colonnes")

#  FEATURES D'ENTRANEMENT 
features = [
    "numero_version",
    "score_qualite",
    "nb_corrections_totales",
    "nb_corrections_ouvertes",
    "nb_corrections_resolues",
    "ratio_resolution",
    "a_correction_bloquante",
    "delai_jours",
    "nb_pages",
    "progression_score",
    "score_plagiat",
    "commentaire_directeur",
]

#  NORMALISATION 
scaler = MinMaxScaler()
X_norm = scaler.fit_transform(df[features])
X = pd.DataFrame(X_norm, columns=[f"{f}_norm" for f in features])

print(f"\n Features normalises : {X.shape[1]} colonnes")

#  VARIABLE CIBLE 
le = LabelEncoder()
y  = le.fit_transform(df["statut_validation"])

print(f"   Classes : {dict(zip(le.classes_, le.transform(le.classes_)))}")

#  CORRLATIONS (pour comprendre le modle) 
print(f"\n Corrlation des features avec le statut :")
print("" * 55)
df_temp = df[features].copy()
df_temp["statut_num"] = y
correlations = df_temp.corr()["statut_num"].drop("statut_num").sort_values()
for feat, corr in correlations.items():
    barre = "" * int(abs(corr) * 30)
    signe = "+" if corr > 0 else "-"
    print(f"  {feat:<32} {signe}{abs(corr):.3f}  {barre}")

#  SPLIT 
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"\n Train : {X_train.shape[0]} | Test : {X_test.shape[0]}")

#  SAUVEGARDE 
X_train.to_csv("data/X_train.csv", index=False)
X_test.to_csv("data/X_test.csv",  index=False)
np.save("data/y_train.npy", y_train)
np.save("data/y_test.npy",  y_test)

joblib.dump(scaler, "../../ia_models/submission/scaler_features.pkl")
joblib.dump(le,     "../../ia_models/submission/label_encoder_statut.pkl")

with open("../../ia_models/submission/features_names.json", "w") as f:
    json.dump(features, f)
with open("../../ia_models/submission/colonnes_features.json", "w") as f:
    json.dump(list(X.columns), f)

print("\n Fichiers sauvegards.")
print("=" * 60)
print("  TAPE 2 TERMINE")
print("=" * 60)

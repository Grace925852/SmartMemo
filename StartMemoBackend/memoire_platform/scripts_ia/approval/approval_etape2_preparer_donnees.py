import os
os.makedirs("../../ia_models/approval", exist_ok=True)
"""
=============================================================
MODULE APPROVAL & QUALITY CHECK
TAPE 2  PRPARATION DES DONNES
=============================================================

TRANSFORMATIONS APPLIQUES :
------------------------------
1. Encodage One-Hot   domaine, filire, mthodologie
2. Les features numriques (scores, longueurs)  dj numriques
3. Normalisation MinMax  remettre tout sur la mme chelle
4. Encodage de la cible  APPROUVE=0 / REJETE=1 / REVISION=2
5. Split 80/20 stratifi
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import json

print("=" * 60)
print("MODULE APPROVAL  TAPE 2 : PRPARATION")
print("=" * 60)

df = pd.read_csv("data/projets_entrainement.csv")
print(f"\n {df.shape[0]} projets chargs | {df.shape[1]} colonnes")

#  FEATURES NUMRIQUES (dj calcules  l'tape 1) 
features_numeriques = [
    "nb_mots_titre", "nb_mots_description", "nb_phrases_description",
    "ratio_vocabulaire", "score_mots_academiques", "score_mots_techniques",
    "score_mots_vagues", "a_methodologie", "a_objectifs_clairs",
    "est_infaisable", "score_similarite_existants",
]

#  FEATURES CATGORIELLES  One-Hot 
df_domaine   = pd.get_dummies(df["domaine"],           prefix="dom")
df_filiere   = pd.get_dummies(df["filiere_etudiant"],  prefix="fil")
df_methodo   = pd.get_dummies(df["methodologie"],      prefix="met")

print(f"\n Encodage :")
print(f"   Domaines       {df_domaine.shape[1]} colonnes")
print(f"   Filires       {df_filiere.shape[1]} colonnes")
print(f"   Mthodologies  {df_methodo.shape[1]} colonnes")

#  NORMALISATION DES FEATURES NUMRIQUES 
scaler = MinMaxScaler()
df_num_norm = pd.DataFrame(
    scaler.fit_transform(df[features_numeriques]),
    columns=[f"{c}_norm" for c in features_numeriques],
    index=df.index
)
print(f"   Features num.  {df_num_norm.shape[1]} colonnes normalises")

#  ASSEMBLAGE 
X = pd.concat([df_num_norm, df_domaine, df_filiere, df_methodo], axis=1)

#  VARIABLE CIBLE 
le = LabelEncoder()
y  = le.fit_transform(df["decision"])

print(f"\n Feature matrix : {X.shape[0]}  {X.shape[1]}")
print(f"   Classes : {dict(zip(le.classes_, le.transform(le.classes_)))}")

#  SPLIT TRAIN / TEST 
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"\n Train : {X_train.shape[0]} | Test : {X_test.shape[0]}")

#  SAUVEGARDE 
X_train.to_csv("data/X_train.csv",  index=False)
X_test.to_csv("data/X_test.csv",   index=False)
np.save("data/y_train.npy", y_train)
np.save("data/y_test.npy",  y_test)

joblib.dump(le,     "../../ia_models/approval/label_encoder_decision.pkl")
joblib.dump(scaler, "../../ia_models/approval/scaler_features.pkl")

with open("../../ia_models/approval/colonnes_features.json", "w", encoding="utf-8") as f:
    json.dump(list(X.columns), f)

# Sauvegarder aussi les noms des colonnes numriques pour la prdiction
with open("../../ia_models/approval/features_numeriques.json", "w", encoding="utf-8") as f:
    json.dump(features_numeriques, f)

print("\n Tous les fichiers sauvegards.")
print("=" * 60)
print("  TAPE 2 TERMINE")
print("=" * 60)

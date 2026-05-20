"""
=============================================================
TAPE 2  PRPARATION ET NETTOYAGE DES DONNES
Module : Recommandation de sujets de mmoire
=============================================================

CE SCRIPT FAIT QUOI ?
---------------------
Un modle ML ne comprend que des NOMBRES.
Mais nos donnes contiennent :
  - du texte  : "Gnie Logiciel", "Python|React|Django"
  - des nombres : notes, moyenne
  - des listes  : comptences, intrts

Ce script transforme tout a en un tableau 100% numrique
que le modle pourra utiliser pour apprendre.

LES TRANSFORMATIONS APPLIQUES :
---------------------------------
1. One-Hot Encoding   filire "Gnie Logiciel" devient [1,0,0,0,0,0]
2. MultiLabelBinarizer  comptences "Python|React"  [0,1,0,...,1,...]
3. Normalisation  ramener toutes les notes sur la mme chelle [0,1]
4. Split train/test  80% pour apprendre, 20% pour tester
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import os
os.makedirs("../../ia_models/recommandation", exist_ok=True)

print("=" * 60)
print("TAPE 2  PRPARATION DES DONNES")
print("=" * 60)

os.makedirs("/home/claude/recommandation/modeles", exist_ok=True)

#  1. CHARGEMENT 

df = pd.read_csv("/home/claude/recommandation/data/etudiants_entrainement.csv")
print(f"\n Donnes charges : {df.shape[0]} lignes  {df.shape[1]} colonnes")

#  2. ENCODAGE DE LA FILIRE (One-Hot Encoding) 
# Avant : filiere = "Gnie Logiciel"
# Aprs : filiere_Gnie_Logiciel=1, filiere_Data_Science=0, ...
# Pourquoi ? Le modle ne peut pas comparer du texte directement

print("\n Encodage des variables catgorielles...")

df_filieres = pd.get_dummies(df["filiere"], prefix="filiere")
print(f"   Filires  {df_filieres.shape[1]} colonnes binaires")

df_niveaux = pd.get_dummies(df["niveau"], prefix="niveau")
print(f"   Niveaux   {df_niveaux.shape[1]} colonnes binaires")

#  3. ENCODAGE DES COMPTENCES (MultiLabel) 
# Avant : competences = "Python|React|Django"
# Aprs : comp_Python=1, comp_React=1, comp_Django=1, comp_TensorFlow=0, ...

mlb_comp = MultiLabelBinarizer()
competences_split = df["competences"].apply(lambda x: x.split("|"))
df_competences = pd.DataFrame(
    mlb_comp.fit_transform(competences_split),
    columns=[f"comp_{c.replace(' ','_').replace('/','_')}" for c in mlb_comp.classes_],
    index=df.index
)
print(f"   Comptences  {df_competences.shape[1]} colonnes binaires")

#  4. ENCODAGE DES INTRTS (MultiLabel) 

mlb_int = MultiLabelBinarizer()
interets_split = df["interets"].apply(lambda x: x.split("|"))
df_interets = pd.DataFrame(
    mlb_int.fit_transform(interets_split),
    columns=[f"int_{i.replace(' ','_').replace('/','_')}" for i in mlb_int.classes_],
    index=df.index
)
print(f"   Intrts    {df_interets.shape[1]} colonnes binaires")

#  5. NORMALISATION DES NOTES (MinMaxScaler) 
# Ramne toutes les notes entre 0 et 1
# Pourquoi ? vite qu'une note sur 20 "crase" une note sur 5

colonnes_notes = [c for c in df.columns if c.startswith("note_")]
scaler = MinMaxScaler()
df_notes_norm = pd.DataFrame(
    scaler.fit_transform(df[colonnes_notes]),
    columns=[c + "_norm" for c in colonnes_notes],
    index=df.index
)
df_notes_norm["moyenne_norm"] = scaler.fit_transform(df[["moyenne_generale"]])
print(f"   Notes       {df_notes_norm.shape[1]} colonnes normalises [0,1]")

#  6. ASSEMBLAGE DU TABLEAU FINAL 

# On assemble toutes les features transformes
X = pd.concat([df_filieres, df_niveaux, df_competences, df_interets, df_notes_norm], axis=1)

# Variable cible Y : le domaine choisi (transform en nombre)
le = LabelEncoder()
y = le.fit_transform(df["domaine_cible"])

print(f"\n Tableau de features final : {X.shape[0]} lignes  {X.shape[1]} colonnes")
print(f"   Variable cible Y : {len(le.classes_)} classes possibles")
print(f"   Classes : {list(le.classes_)}")

#  7. SPLIT TRAIN / TEST 
# 80% des donnes pour entraner le modle
# 20% pour tester si le modle fonctionne sur des donnes inconnues

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
    # stratify=y : garantit que chaque domaine est bien reprsent dans les deux sets
)

print(f"\n Dcoupage train/test :")
print(f"   Entranement : {X_train.shape[0]} tudiants (80%)")
print(f"   Test         : {X_test.shape[0]} tudiants  (20%)")

#  8. SAUVEGARDE 
# On sauvegarde tout pour ne pas recalculer  chaque fois

X_train.to_csv("/home/claude/recommandation/data/X_train.csv", index=False)
X_test.to_csv("/home/claude/recommandation/data/X_test.csv",  index=False)
np.save("/home/claude/recommandation/data/y_train.npy", y_train)
np.save("/home/claude/recommandation/data/y_test.npy",  y_test)

# Sauvegarder les encodeurs (on en aura besoin pour les nouvelles prdictions)
joblib.dump(mlb_comp, "/home/claude/recommandation/modeles/mlb_competences.pkl")
joblib.dump(mlb_int,  "/home/claude/recommandation/modeles/mlb_interets.pkl")
joblib.dump(le,       "/home/claude/recommandation/modeles/label_encoder_domaine.pkl")
joblib.dump(scaler,   "/home/claude/recommandation/modeles/scaler_notes.pkl")

# Sauvegarder aussi la liste des colonnes (pour reconstruire les features plus tard)
colonnes = list(X.columns)
import json
with open("/home/claude/recommandation/modeles/colonnes_features.json", "w") as f:
    json.dump(colonnes, f)

print("\n Fichiers sauvegards :")
print("   /data/X_train.csv        Features d'entranement")
print("   /data/X_test.csv         Features de test")
print("   /data/y_train.npy        Labels d'entranement")
print("   /data/y_test.npy         Labels de test")
print("   /modeles/mlb_competences.pkl   Encodeur comptences")
print("   /modeles/mlb_interets.pkl      Encodeur intrts")
print("   /modeles/label_encoder_domaine.pkl  Dcodeur domaines")
print("   /modeles/scaler_notes.pkl      Normaliseur notes")
print("   /modeles/colonnes_features.json  Liste des colonnes")

print("\n" + "=" * 60)
print("  TAPE 2 TERMINE  Donnes prtes pour l'entranement")
print("=" * 60)

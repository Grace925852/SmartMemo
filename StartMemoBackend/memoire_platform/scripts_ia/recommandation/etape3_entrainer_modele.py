"""
=============================================================
TAPE 3  ENTRANEMENT ET VALUATION DU MODLE
Module : Recommandation de sujets de mmoire
=============================================================

CE SCRIPT FAIT QUOI ?
---------------------
On va entraner PLUSIEURS modles diffrents sur les mmes donnes,
puis comparer leurs performances pour choisir le meilleur.

LES MODLES TESTS :
---------------------
1. Random Forest       Fort de arbres de dcision. Trs robuste.
2. Gradient Boosting   Arbres en cascade, chacun corrige l'erreur du prcdent.
3. KNN (K plus proches voisins)  "Tes voisins ont choisi a, tu choisiras a aussi"
4. SVM                 Trouve la meilleure frontire entre les classes

MTRIQUES D'VALUATION :
--------------------------
- Accuracy   : % de bonnes prdictions (ex: 87% de bonnes recommandations)
- Precision  : Sur les recommandations faites, combien sont vraiment pertinentes
- Recall     : Sur tous les vrais cas d'un domaine, combien ont t retrouvs
- F1-Score   : quilibre entre Precision et Recall

 LA FIN : le meilleur modle est sauvegard pour l'API.
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score
)
from sklearn.model_selection import cross_val_score

print("=" * 60)
print("TAPE 3  ENTRANEMENT DU MODLE")
print("=" * 60)

#  1. CHARGEMENT DES DONNES PRPARES 

X_train = pd.read_csv("/home/claude/recommandation/data/X_train.csv")
X_test  = pd.read_csv("/home/claude/recommandation/data/X_test.csv")
y_train = np.load("/home/claude/recommandation/data/y_train.npy")
y_test  = np.load("/home/claude/recommandation/data/y_test.npy")
le      = joblib.load("/home/claude/recommandation/modeles/label_encoder_domaine.pkl")

print(f"\n Donnes charges :")
print(f"   X_train : {X_train.shape}  |  y_train : {y_train.shape}")
print(f"   X_test  : {X_test.shape}   |  y_test  : {y_test.shape}")
print(f"   Classes : {list(le.classes_)}")

#  2. DFINITION DES MODLES  COMPARER 

modeles = {
    "Random Forest": RandomForestClassifier(
        n_estimators=200,    # 200 arbres de dcision dans la fort
        max_depth=None,      # Profondeur illimite (les arbres grandissent au max)
        min_samples_split=2, # Au moins 2 chantillons pour diviser un nud
        random_state=42,
        n_jobs=-1            # Utilise tous les curs du processeur
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=150,    # 150 arbres en cascade
        learning_rate=0.1,   # Vitesse d'apprentissage (petit = plus prudent)
        max_depth=5,         # Profondeur max de chaque arbre
        random_state=42
    ),
    "KNN (5 voisins)": KNeighborsClassifier(
        n_neighbors=5,       # Regarde les 5 tudiants les plus similaires
        metric="euclidean",  # Distance euclidienne pour mesurer la similarit
        weights="distance"   # Les voisins plus proches ont plus de poids
    ),
    "SVM": SVC(
        kernel="rbf",        # Noyau radial (bon pour donnes non linaires)
        C=10,                # Paramtre de rgularisation
        gamma="scale",       # Mise  l'chelle automatique du noyau
        probability=True,    # Ncessaire pour avoir des scores de confiance
        random_state=42
    ),
}

#  3. ENTRANEMENT ET VALUATION 

resultats = {}

print("\n" + "" * 60)
print("ENTRANEMENT EN COURS...")
print("" * 60)

for nom, modele in modeles.items():

    print(f"\n  {nom}...")

    #  Entranement 
    debut = time.time()
    modele.fit(X_train, y_train)
    duree_train = round(time.time() - debut, 2)

    #  Prdiction sur les donnes de TEST (jamais vues) 
    y_pred = modele.predict(X_test)

    #  Calcul des mtriques 
    acc    = accuracy_score(y_test, y_pred)
    f1     = f1_score(y_test, y_pred, average="weighted")

    # Validation croise 5-fold (entrane 5 fois sur des sous-ensembles diffrents)
    # C'est le test le plus fiable de la qualit du modle
    cv_scores = cross_val_score(modele, X_train, y_train, cv=5, scoring="accuracy")

    resultats[nom] = {
        "modele":       modele,
        "accuracy":     round(acc  * 100, 2),
        "f1_score":     round(f1   * 100, 2),
        "cv_mean":      round(cv_scores.mean() * 100, 2),
        "cv_std":       round(cv_scores.std()  * 100, 2),
        "duree_train":  duree_train,
        "y_pred":       y_pred,
    }

    print(f"    Accuracy : {acc*100:.1f}%  |  F1 : {f1*100:.1f}%  "
          f"|  CV : {cv_scores.mean()*100:.1f}%  {cv_scores.std()*100:.1f}%  "
          f"|  Temps : {duree_train}s")

#  4. TABLEAU COMPARATIF 

print("\n" + "=" * 60)
print("TABLEAU COMPARATIF DES MODLES")
print("=" * 60)
print(f"\n{'Modle':<25} {'Accuracy':>10} {'F1-Score':>10} {'CV Moyen':>12} {'Temps':>8}")
print("" * 70)

meilleur_nom   = None
meilleur_score = 0

for nom, res in resultats.items():
    etoile = ""
    if res["cv_mean"] > meilleur_score:
        meilleur_score = res["cv_mean"]
        meilleur_nom   = nom
    print(f"  {nom:<23} {res['accuracy']:>9.1f}%  {res['f1_score']:>9.1f}%  "
          f"{res['cv_mean']:>9.1f}%{res['cv_std']:.1f}  {res['duree_train']:>6.1f}s")

print("" * 70)
print(f"\n MEILLEUR MODLE : {meilleur_nom} "
      f"(CV = {resultats[meilleur_nom]['cv_mean']}%)")

#  5. RAPPORT DTAILL DU MEILLEUR MODLE 

print(f"\n" + "=" * 60)
print(f"RAPPORT DTAILL  {meilleur_nom}")
print("=" * 60)

meilleur = resultats[meilleur_nom]
y_pred_best = meilleur["y_pred"]
noms_classes = le.classes_

print("\nRapport par domaine :")
print("" * 60)
rapport = classification_report(
    y_test, y_pred_best,
    target_names=noms_classes,
    output_dict=True
)

print(f"{'Domaine':<30} {'Prcision':>10} {'Rappel':>10} {'F1':>8} {'Support':>8}")
print("" * 70)
for domaine in noms_classes:
    r = rapport[domaine]
    print(f"  {domaine:<28} {r['precision']*100:>9.1f}%  "
          f"{r['recall']*100:>9.1f}%  {r['f1-score']*100:>7.1f}%  "
          f"{int(r['support']):>7}")

print("" * 70)
print(f"  {'Moyenne globale':<28} "
      f"{rapport['weighted avg']['precision']*100:>9.1f}%  "
      f"{rapport['weighted avg']['recall']*100:>9.1f}%  "
      f"{rapport['weighted avg']['f1-score']*100:>7.1f}%  "
      f"{int(rapport['weighted avg']['support']):>7}")

#  6. MATRICE DE CONFUSION 

print(f"\n Matrice de confusion ({meilleur_nom}) :")
print("   (Ligne = vrai domaine | Colonne = domaine prdit)\n")

cm = confusion_matrix(y_test, y_pred_best)
abrev = [d[:8] for d in noms_classes]
header = "          " + "  ".join(f"{a:>8}" for a in abrev)
print(header)
print("         " + "" * (len(abrev) * 10))

for i, (ligne, dom) in enumerate(zip(cm, noms_classes)):
    vals = "  ".join(
        f"\033[1m{v:>8}\033[0m" if j == i else f"{v:>8}"
        for j, v in enumerate(ligne)
    )
    print(f"  {dom[:8]:>8}  {vals}")

#  7. SAUVEGARDE DU MEILLEUR MODLE 

print(f"\n Sauvegarde du meilleur modle ({meilleur_nom})...")

chemin_modele = "/home/claude/recommandation/modeles/modele_recommandation.pkl"
import os; os.makedirs("../../ia_models/recommandation", exist_ok=True); joblib.dump(meilleur["modele"], chemin_modele)

# Sauvegarder aussi les mtadonnes du modle
meta = {
    "nom_modele":    meilleur_nom,
    "accuracy":      meilleur["accuracy"],
    "f1_score":      meilleur["f1_score"],
    "cv_mean":       meilleur["cv_mean"],
    "cv_std":        meilleur["cv_std"],
    "nb_features":   X_train.shape[1],
    "nb_classes":    len(noms_classes),
    "classes":       list(noms_classes),
    "nb_train":      len(X_train),
    "nb_test":       len(X_test),
}
with open("/home/claude/recommandation/modeles/meta_modele.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"    Modle sauvegard  {chemin_modele}")
print(f"    Mtadonnes        /modeles/meta_modele.json")

print("\n" + "=" * 60)
print("  TAPE 3 TERMINE  Modle entran et sauvegard")
print(f"  Meilleur modle : {meilleur_nom} | Accuracy : {meilleur['accuracy']}%")
print("=" * 60)

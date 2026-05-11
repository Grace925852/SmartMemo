"""
=============================================================
MODULE APPROVAL & QUALITY CHECK
TAPE 3  ENTRANEMENT DU MODLE
=============================================================

MODLES COMPARS :
-------------------
1. Random Forest          Robuste, gre bien les donnes mixtes
2. Gradient Boosting      Trs prcis sur les donnes structures
3. Logistic Regression    Simple, interprtable, bon pour 3 classes
4. SVM                    Efficace sur donnes de taille moyenne
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model  import LogisticRegression
from sklearn.svm           import SVC
from sklearn.metrics       import accuracy_score, f1_score, classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score

print("=" * 60)
print("MODULE APPROVAL  TAPE 3 : ENTRANEMENT")
print("=" * 60)

X_train = pd.read_csv("data/X_train.csv")
X_test  = pd.read_csv("data/X_test.csv")
y_train = np.load("data/y_train.npy")
y_test  = np.load("data/y_test.npy")
le      = joblib.load("../../ia_models/approval/label_encoder_decision.pkl")

print(f"\n Train : {X_train.shape} | Test : {X_test.shape}")
print(f"   Classes : {list(le.classes_)}")

#  MODLES 

modeles = {
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=None, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.1, max_depth=5, random_state=42),
    "Rgression Logistique": LogisticRegression(
        max_iter=1000, C=1.0, random_state=42),
    "SVM": SVC(
        kernel="rbf", C=10, gamma="scale", probability=True, random_state=42),
}

#  ENTRANEMENT 

resultats = {}
print("\n" + "" * 60)
print("ENTRANEMENT EN COURS...")
print("" * 60)

for nom, modele in modeles.items():
    print(f"\n  {nom}...")
    t0 = time.time()
    modele.fit(X_train, y_train)
    duree = round(time.time() - t0, 2)

    y_pred    = modele.predict(X_test)
    acc       = accuracy_score(y_test, y_pred)
    f1        = f1_score(y_test, y_pred, average="weighted")
    cv_scores = cross_val_score(modele, X_train, y_train, cv=5, scoring="accuracy")

    resultats[nom] = {
        "modele": modele, "accuracy": round(acc*100,2),
        "f1_score": round(f1*100,2),
        "cv_mean": round(cv_scores.mean()*100,2),
        "cv_std":  round(cv_scores.std()*100,2),
        "duree": duree, "y_pred": y_pred,
    }
    print(f"    Accuracy:{acc*100:.1f}% | F1:{f1*100:.1f}% | "
          f"CV:{cv_scores.mean()*100:.1f}%{cv_scores.std()*100:.1f}% | {duree}s")

#  COMPARATIF 

print("\n" + "=" * 60)
print("TABLEAU COMPARATIF")
print("=" * 60)
print(f"\n{'Modle':<28} {'Accuracy':>10} {'F1':>8} {'CV Moyen':>12} {'Temps':>7}")
print("" * 68)

meilleur_nom, meilleur_score = None, 0
for nom, res in resultats.items():
    if res["cv_mean"] > meilleur_score:
        meilleur_score = res["cv_mean"]
        meilleur_nom   = nom
    print(f"  {nom:<26} {res['accuracy']:>9.1f}%  {res['f1_score']:>7.1f}%  "
          f"{res['cv_mean']:>8.1f}%{res['cv_std']:.1f}  {res['duree']:>5.1f}s")

print("" * 68)
print(f"\n MEILLEUR : {meilleur_nom} (CV = {resultats[meilleur_nom]['cv_mean']}%)")

#  RAPPORT DTAILL 

meilleur = resultats[meilleur_nom]
y_pred_best = meilleur["y_pred"]
noms_classes = le.classes_

print(f"\n{'='*60}")
print(f"RAPPORT DTAILL  {meilleur_nom}")
print("=" * 60)
print(f"\n{'Classe':<25} {'Prcision':>10} {'Rappel':>9} {'F1':>8} {'Nb':>6}")
print("" * 62)
rapport = classification_report(y_test, y_pred_best, target_names=noms_classes, output_dict=True)
for cls in noms_classes:
    r = rapport[cls]
    print(f"  {cls:<23} {r['precision']*100:>9.1f}%  "
          f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  {int(r['support']):>5}")
print("" * 62)
r = rapport["weighted avg"]
print(f"  {'Moyenne pondre':<23} {r['precision']*100:>9.1f}%  "
      f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  {int(r['support']):>5}")

# Matrice de confusion
print(f"\n Matrice de confusion :")
cm = confusion_matrix(y_test, y_pred_best)
abrev = [c[:12] for c in noms_classes]
print("              " + "  ".join(f"{a:>12}" for a in abrev))
print("             " + "" * (len(abrev) * 14))
for i, (ligne, cls) in enumerate(zip(cm, noms_classes)):
    vals = "  ".join(f"\033[1m{v:>12}\033[0m" if j==i else f"{v:>12}" for j,v in enumerate(ligne))
    print(f"  {cls[:12]:>12}  {vals}")

# Importance des features (si Random Forest ou Gradient Boosting)
if hasattr(meilleur["modele"], "feature_importances_"):
    print(f"\n Top 10 features les plus importantes :")
    importances = pd.Series(
        meilleur["modele"].feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False).head(10)
    for feat, imp in importances.items():
        barre = "" * int(imp * 200)
        print(f"   {feat:<40} {imp:.4f}  {barre}")

#  SAUVEGARDE 

import os; os.makedirs("../../ia_models/approval", exist_ok=True); joblib.dump(meilleur["modele"], "../../ia_models/approval/modele_approval.pkl")

meta = {
    "nom_modele": meilleur_nom,
    "accuracy":   meilleur["accuracy"],
    "f1_score":   meilleur["f1_score"],
    "cv_mean":    meilleur["cv_mean"],
    "cv_std":     meilleur["cv_std"],
    "nb_features": X_train.shape[1],
    "nb_classes":  len(noms_classes),
    "classes":     list(noms_classes),
    "nb_train":    len(X_train),
    "nb_test":     len(X_test),
    "seuil_rejet_similarite": 0.80,
}
with open("../../ia_models/approval/meta_modele.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n Modle sauvegard  modeles/modele_approval.pkl")
print(f"   Mtadonnes       modeles/meta_modele.json")
print("\n" + "=" * 60)
print(f"  TAPE 3 TERMINE  {meilleur_nom} | Accuracy : {meilleur['accuracy']}%")
print("=" * 60)

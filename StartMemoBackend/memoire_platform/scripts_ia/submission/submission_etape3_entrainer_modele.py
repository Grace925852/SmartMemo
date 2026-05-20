"""
=============================================================
MODULE SUBMISSION WORKFLOW
TAPE 3  ENTRANEMENT DU MODLE
=============================================================

OBJECTIF :
-----------
Prdire automatiquement si une version de mmoire est :
   VALIDEE            : peut passer en pr-soutenance
   CORRECTIONS_REQUISES : retour  l'tudiant avec commentaires
   REJETEE            : problme grave (plagiat, non-conformit)

Le directeur peut toujours override la dcision du modle,
mais le modle lui propose une recommandation argumente.

MODLES COMPARS :
-------------------
1. Random Forest           Robuste, bien adapt aux donnes mixtes
2. Gradient Boosting       Trs prcis sur donnes structures
3. Rgression Logistique   Simple, interprtable (explique la dcision)
4. SVM                     Efficace sur jeux moyens

PARTICULARIT DE CE MODULE :
------------------------------
On ajoute une analyse d'EXPLICABILIT du modle.
Pour chaque prdiction, le systme explique POURQUOI
il recommande ce statut  essentiel pour que le directeur
puisse faire confiance au modle.
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)
from sklearn.model_selection import cross_val_score

print("=" * 60)
print("MODULE SUBMISSION  TAPE 3 : ENTRANEMENT")
print("=" * 60)

X_train = pd.read_csv("data/X_train.csv")
X_test  = pd.read_csv("data/X_test.csv")
y_train = np.load("data/y_train.npy")
y_test  = np.load("data/y_test.npy")
le      = joblib.load("../../ia_models/submission/label_encoder_statut.pkl")

print(f"\n Train:{X_train.shape} | Test:{X_test.shape}")
print(f"   Classes : {list(le.classes_)}")

#  MODLES 

modeles = {
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced",   # important : compense le dsquilibre des classes
        random_state=42, n_jobs=-1
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.1,
        max_depth=5, random_state=42
    ),
    "Rgression Logistique": LogisticRegression(
        max_iter=1000, C=1.0,
        class_weight="balanced",
        random_state=42
    ),
    "SVM": SVC(
        kernel="rbf", C=10, gamma="scale",
        class_weight="balanced",
        probability=True, random_state=42
    ),
}

#  ENTRANEMENT 

resultats = {}
print("\n Entranement en cours...\n")

for nom, modele in modeles.items():
    t0    = time.time()
    modele.fit(X_train, y_train)
    duree = round(time.time() - t0, 2)

    y_pred = modele.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    f1     = f1_score(y_test, y_pred, average="weighted")
    cv     = cross_val_score(modele, X_train, y_train, cv=5, scoring="f1_weighted")

    resultats[nom] = {
        "modele": modele, "accuracy": round(acc*100,2),
        "f1": round(f1*100,2),
        "cv_mean": round(cv.mean()*100,2),
        "cv_std":  round(cv.std()*100,2),
        "duree": duree, "y_pred": y_pred,
    }
    print(f"   {nom}")
    print(f"     Accuracy={acc*100:.1f}% | F1={f1*100:.1f}% | "
          f"CV F1={cv.mean()*100:.1f}%{cv.std()*100:.1f}% ({duree}s)")

#  TABLEAU COMPARATIF 

print(f"\n{''*65}")
print(f"{'Modle':<28} {'Accuracy':>10} {'F1':>8} {'CV F1':>12} {'Temps':>7}")
print("" * 65)
meilleur_nom, meilleur_cv = None, 0
for nom, res in resultats.items():
    if res["cv_mean"] > meilleur_cv:
        meilleur_cv  = res["cv_mean"]
        meilleur_nom = nom
    print(f"  {nom:<26} {res['accuracy']:>9.1f}%  {res['f1']:>7.1f}%  "
          f"{res['cv_mean']:>8.1f}%{res['cv_std']:.1f}  {res['duree']:>5.1f}s")
print("" * 65)
print(f"\n Meilleur : {meilleur_nom} (CV F1={meilleur_cv:.1f}%)")

#  RAPPORT DTAILL 

meilleur    = resultats[meilleur_nom]
y_pred_best = meilleur["y_pred"]
noms_cls    = le.classes_

print(f"\n{'='*60}")
print(f"RAPPORT DTAILL  {meilleur_nom}")
print("=" * 60)
print(f"\n{'Classe':<25} {'Prcision':>10} {'Rappel':>9} {'F1':>8} {'Nb':>6}")
print("" * 62)
rapport = classification_report(
    y_test, y_pred_best, target_names=noms_cls, output_dict=True
)
for cls in noms_cls:
    r = rapport[cls]
    print(f"  {cls:<23} {r['precision']*100:>9.1f}%  "
          f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  "
          f"{int(r['support']):>5}")
print("" * 62)
r = rapport["weighted avg"]
print(f"  {'Moyenne pondre':<23} {r['precision']*100:>9.1f}%  "
      f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  "
      f"{int(r['support']):>5}")

# Matrice de confusion
print(f"\n Matrice de confusion :")
cm     = confusion_matrix(y_test, y_pred_best)
abrevs = [c[:12] for c in noms_cls]
print("              " + "  ".join(f"{a:>12}" for a in abrevs))
print("             " + "" * (len(abrevs)*14))
for i, (ligne, cls) in enumerate(zip(cm, noms_cls)):
    vals = "  ".join(
        f"\033[1m{v:>12}\033[0m" if j==i else f"{v:>12}"
        for j,v in enumerate(ligne)
    )
    print(f"  {cls[:12]:>12}  {vals}")

# Importance des features
if hasattr(meilleur["modele"], "feature_importances_"):
    print(f"\n Importance des features (Top 8) :")
    importances = pd.Series(
        meilleur["modele"].feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False).head(8)
    for feat, imp in importances.items():
        barre = "" * int(imp * 300)
        print(f"   {feat:<35} {imp:.4f}  {barre}")

#  SAUVEGARDE 

import os; os.makedirs("../../ia_models/submission", exist_ok=True); joblib.dump(meilleur["modele"], "../../ia_models/submission/modele_submission.pkl")

meta = {
    "nom_modele": meilleur_nom,
    "accuracy":   meilleur["accuracy"],
    "f1_score":   meilleur["f1"],
    "cv_f1":      meilleur_cv,
    "cv_std":     meilleur["cv_std"],
    "nb_classes": len(noms_cls),
    "classes":    list(noms_cls),
    "nb_train":   len(X_train),
    "seuil_plagiat_rejet":  40.0,
    "seuil_qualite_min":    60.0,
}
with open("../../ia_models/submission/meta_modele.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n Modle sauvegard  modeles/modele_submission.pkl")
print("\n" + "=" * 60)
print(f"  TAPE 3 TERMINE | {meilleur_nom} | Acc={meilleur['accuracy']}%")
print("=" * 60)

"""
=============================================================
MODULE ANTI-PLAGIAT AVANC
TAPE 3  ENTRANEMENT DU CLASSIFIEUR DE PLAGIAT
=============================================================

CE QUE LE MODLE APPREND :
----------------------------
 partir des features de similarit (cosinus, Jaccard, etc.),
le modle classe chaque paire de textes en :
  - ORIGINAL           aucune similitude
  - SIMILAIRE          reformulation lgre, pas de plagiat
  - PLAGIAT_PARTIEL    copie d'une partie significative
  - PLAGIAT_TOTAL      copie quasi-intgrale

Il apprend aussi  prdire le SCORE PRCIS de similarit (01).
"""

import pandas as pd
import numpy as np
import joblib
import json
import time
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)
from sklearn.model_selection import cross_val_score

print("=" * 60)
print("MODULE ANTI-PLAGIAT  TAPE 3 : ENTRANEMENT")
print("=" * 60)

X_train = pd.read_csv("data/X_train.csv")
X_test  = pd.read_csv("data/X_test.csv")
y_train = np.load("data/y_train.npy")
y_test  = np.load("data/y_test.npy")
le      = joblib.load("modeles/label_encoder_similarite.pkl")

print(f"\n Train:{X_train.shape} | Test:{X_test.shape}")
print(f"   Classes : {list(le.classes_)}")

#  MODLES 

modeles = {
    "Random Forest": RandomForestClassifier(
        n_estimators=200, random_state=42, n_jobs=-1),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.1, max_depth=5, random_state=42),
    "SVM": SVC(
        kernel="rbf", C=10, gamma="scale",
        probability=True, random_state=42),
    "Rgression Logistique": LogisticRegression(
        max_iter=1000, random_state=42),
}

#  ENTRANEMENT 

resultats = {}
print("\n[WAIT] Entranement...\n")

for nom, modele in modeles.items():
    t0 = time.time()
    modele.fit(X_train, y_train)
    duree = round(time.time()-t0, 2)

    y_pred = modele.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    f1     = f1_score(y_test, y_pred, average="weighted")
    cv     = cross_val_score(modele, X_train, y_train, cv=5, scoring="f1_weighted")

    resultats[nom] = {
        "modele": modele, "accuracy": round(acc*100,2),
        "f1": round(f1*100,2), "cv_mean": round(cv.mean()*100,2),
        "cv_std": round(cv.std()*100,2), "duree": duree, "y_pred": y_pred,
    }
    print(f"  [OK] {nom}")
    print(f"     Acc={acc*100:.1f}% | F1={f1*100:.1f}% | "
          f"CV={cv.mean()*100:.1f}%{cv.std()*100:.1f}% ({duree}s)")

#  TABLEAU COMPARATIF 

print(f"\n{''*65}")
print(f"{'Modle':<28} {'Accuracy':>10} {'F1':>8} {'CV F1':>12} {'Temps':>7}")
print(""*65)
meilleur_nom, meilleur_cv = None, 0
for nom, res in resultats.items():
    if res["cv_mean"] > meilleur_cv:
        meilleur_cv  = res["cv_mean"]
        meilleur_nom = nom
    print(f"  {nom:<26} {res['accuracy']:>9.1f}%  {res['f1']:>7.1f}%  "
          f"{res['cv_mean']:>8.1f}%{res['cv_std']:.1f}  {res['duree']:>5.1f}s")
print(""*65)
print(f"\n[BEST] Meilleur : {meilleur_nom} (CV F1={meilleur_cv:.1f}%)")

#  RAPPORT DTAILL 

meilleur    = resultats[meilleur_nom]
y_pred_best = meilleur["y_pred"]
noms_cls    = le.classes_

print(f"\n{'='*60}")
print(f"RAPPORT DTAILL  {meilleur_nom}")
print("="*60)
print(f"\n{'Classe':<20} {'Prcision':>10} {'Rappel':>9} {'F1':>8} {'Nb':>6}")
print(""*57)
rapport = classification_report(
    y_test, y_pred_best, target_names=noms_cls, output_dict=True
)
for cls in noms_cls:
    r = rapport[cls]
    print(f"  {cls:<18} {r['precision']*100:>9.1f}%  "
          f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  "
          f"{int(r['support']):>5}")
print(""*57)
r = rapport["weighted avg"]
print(f"  {'Moyenne pondre':<18} {r['precision']*100:>9.1f}%  "
      f"{r['recall']*100:>8.1f}%  {r['f1-score']*100:>7.1f}%  "
      f"{int(r['support']):>5}")

# Matrice de confusion
print(f"\n[STAT] Matrice de confusion :")
cm = confusion_matrix(y_test, y_pred_best)
abr = [c[:10] for c in noms_cls]
print("             " + "  ".join(f"{a:>10}" for a in abr))
print("            " + ""*(len(abr)*12))
for i,(ligne,cls) in enumerate(zip(cm, noms_cls)):
    vals = "  ".join(
        f"\033[1m{v:>10}\033[0m" if j==i else f"{v:>10}"
        for j,v in enumerate(ligne)
    )
    print(f"  {cls[:10]:>10}  {vals}")

# Importance des features
if hasattr(meilleur["modele"], "feature_importances_"):
    print(f"\n[SEARCH] Importance des features :")
    importances = pd.Series(
        meilleur["modele"].feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)
    for feat, imp in importances.items():
        barre = "" * int(imp * 400)
        print(f"   {feat:<30} {imp:.4f}  {barre}")

#  SAUVEGARDE 

OUTPUT_DIR = "../../ia_models/antiplagiat"
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sauvegarde du modle principal pour l'API
joblib.dump(meilleur["modele"], f"{OUTPUT_DIR}/modele_antiplagiat.pkl")

# Sauvegarde locale aussi (optionnel)
os.makedirs("modeles", exist_ok=True)
joblib.dump(meilleur["modele"], "modeles/modele_plagiat_clf.pkl")

meta = {
    "nom_modele": meilleur_nom,
    "accuracy":   meilleur["accuracy"],
    "f1_score":   meilleur["f1"],
    "cv_f1":      meilleur_cv,
    "cv_std":     meilleur["cv_std"],
    "classes":    list(noms_cls),
    "seuils": {
        "ORIGINAL":        [0.00, 0.25],
        "SIMILAIRE":       [0.25, 0.50],
        "PLAGIAT_PARTIEL": [0.50, 0.80],
        "PLAGIAT_TOTAL":   [0.80, 1.00],
    },
    "seuil_alerte":  0.50,
    "seuil_rejet":   0.80,
}

# Sauvegarde des mtadonnes pour l'API et localement
with open(f"{OUTPUT_DIR}/meta_modele.json","w",encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

with open("modeles/meta_modele.json","w",encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\n[SAVE] Classifieur  {OUTPUT_DIR}/modele_antiplagiat.pkl")
print("\n"+"="*60)
print(f"  TAPE 3 TERMINE | {meilleur_nom} | Acc={meilleur['accuracy']}%")
print("="*60)

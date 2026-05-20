"""
=============================================================
MODULE ANTI-PLAGIAT AVANCÉ
ÉTAPE 4 — MOTEUR COMPLET + RAPPORT + API FASTAPI
=============================================================

PIPELINE COMPLET D'ANALYSE :
------------------------------

  Nouveau texte soumis
      ↓
  [1] Vectorisation TF-IDF + LSA → vecteur de 100 dimensions
      ↓
  [2] Recherche dans l'index (similarité cosinus avec 200 archives)
      → Top-5 mémoires les plus similaires
      ↓
  [3] Analyse par section (introduction, méthodologie, résultats, conclusion)
      → Score de plagiat par section
      ↓
  [4] Classificateur ML → catégorie (ORIGINAL / SIMILAIRE / PLAGIAT)
      ↓
  [5] Génération du rapport PDF structuré :
      - Score global de plagiat (0–100%)
      - Statut : PROPRE / AVERTISSEMENT / RISQUE_ÉLEVÉ / BLOQUÉ
      - Tableau des passages suspects avec source identifiée
      - Recommandations concrètes

API FASTAPI — PORT 8005
  POST /analyser          → Analyse complète d'un texte
  POST /analyser-sections → Analyse section par section
  GET  /corpus/stats      → Statistiques du corpus archivé
  POST /corpus/ajouter    → Ajouter un mémoire au corpus après soutenance
"""

import joblib
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ─── CHARGEMENT DES ARTEFACTS ────────────────────────────────────────────────

tfidf    = joblib.load("modeles/tfidf_vectorizer.pkl")
svd      = joblib.load("modeles/svd_lsa.pkl")
clf      = joblib.load("modeles/modele_plagiat_clf.pkl")
le       = joblib.load("modeles/label_encoder_similarite.pkl")

index_vecteurs = np.load("modeles/index_vecteurs.npy")

with open("modeles/index_metadata.json", encoding="utf-8") as f:
    index_meta = json.load(f)

with open("modeles/feature_cols.json") as f:
    feature_cols = json.load(f)

with open("modeles/meta_modele.json", encoding="utf-8") as f:
    meta = json.load(f)

SEUIL_ALERTE = meta["seuil_alerte"]
SEUIL_REJET  = meta["seuil_rejet"]
N_ARCHIVES   = len(index_meta["id_memoire"])


# ─── FONCTIONS UTILITAIRES ───────────────────────────────────────────────────

def vectoriser(texte: str) -> np.ndarray:
    """Transforme un texte en vecteur LSA normalisé."""
    vec_tfidf = tfidf.transform([str(texte)])
    vec_lsa   = svd.transform(vec_tfidf)
    return normalize(vec_lsa, norm="l2")[0]


def rechercher_similaires(vecteur: np.ndarray, top_k: int = 5) -> list:
    """
    Recherche les top_k mémoires archivés les plus similaires.
    C'est la recherche vectorielle : produit matriciel = similarité cosinus.
    Équivalent à FAISS pour notre corpus de 200 mémoires.
    """
    scores = index_vecteurs @ vecteur
    indices_tries = np.argsort(scores)[::-1][:top_k]

    resultats = []
    for idx in indices_tries:
        resultats.append({
            "rang":          int(idx) + 1,
            "id_memoire":    index_meta["id_memoire"][idx],
            "titre":         index_meta["titre"][idx],
            "domaine":       index_meta["domaine"][idx],
            "annee":         int(index_meta["annee"][idx]),
            "auteur":        index_meta["auteur"][idx],
            "score_cosinus": round(float(scores[idx]), 4),
            "pct_similarite": round(float(scores[idx]) * 100, 1),
        })
    return resultats


def extraire_features(vecteur_a: np.ndarray, texte_a: str,
                      vecteur_b: np.ndarray, texte_b: str,
                      top_score_index: float) -> list:
    """Recalcule les features pour le classificateur."""
    sim = float(np.dot(vecteur_a, vecteur_b))
    mots_a = set(str(texte_a).lower().split())
    mots_b = set(str(texte_b).lower().split())
    jaccard = len(mots_a & mots_b) / max(len(mots_a | mots_b), 1)
    len_a   = len(str(texte_a).split())
    len_b   = len(str(texte_b).split())
    ratio_l = min(len_a, len_b) / max(len_a, len_b, 1)
    rares   = len([m for m in (mots_a & mots_b) if len(m) > 6])
    diff    = abs(sim - top_score_index)
    return [sim, jaccard, ratio_l, rares, top_score_index, diff]


def statut_depuis_score(score: float) -> dict:
    """Détermine le statut et la couleur selon le score de similarité."""
    if score < 0.25:
        return {"statut":"PROPRE",        "couleur":"vert",  "icone":"✅",
                "message":"Aucune similarité problématique détectée."}
    elif score < 0.50:
        return {"statut":"AVERTISSEMENT", "couleur":"jaune", "icone":"⚠️ ",
                "message":"Similarité légère détectée. Vérification recommandée."}
    elif score < 0.80:
        return {"statut":"RISQUE_ELEVE",  "couleur":"orange","icone":"🔶",
                "message":"Similarité forte. Examen approfondi obligatoire."}
    else:
        return {"statut":"BLOQUE",        "couleur":"rouge", "icone":"❌",
                "message":"Plagiat quasi-certain. Soumission bloquée."}


# ═══════════════════════════════════════════════════════════════════════
# MOTEUR D'ANALYSE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════

def analyser_texte_complet(texte: str, id_soumission: str = "INCONNU") -> dict:
    """
    Analyse complète d'un texte pour détecter le plagiat.
    Retourne un rapport structuré complet.
    """
    # 1. Vectorisation
    vecteur = vectoriser(texte)

    # 2. Recherche des archives similaires
    similaires = rechercher_similaires(vecteur, top_k=5)
    top_score  = similaires[0]["score_cosinus"] if similaires else 0.0

    # 3. Chargement du texte source le plus similaire pour comparaison
    df_archives = pd.read_csv("data/memoires_archives.csv")
    idx_source  = index_meta["id_memoire"].index(similaires[0]["id_memoire"]) \
                  if similaires else 0
    texte_source = df_archives.iloc[idx_source]["texte_complet"] \
                   if idx_source < len(df_archives) else ""
    vecteur_source = vectoriser(texte_source)

    # 4. Extraction des features et classification ML
    features = extraire_features(vecteur, texte, vecteur_source,
                                  texte_source, top_score)
    proba    = clf.predict_proba([features])[0]
    idx_pred = np.argmax(proba)
    categorie = le.classes_[idx_pred]

    # 5. Score global de plagiat
    # Combinaison du score cosinus et de la confiance ML
    score_plagiat_global = round(
        (top_score * 0.70 + float(proba[idx_pred]) * 0.30), 4
    )

    # 6. Statut
    statut_info = statut_depuis_score(top_score)

    # 7. Rapport des probabilités ML
    probas_ml = {
        cls: round(float(p)*100, 1)
        for cls, p in zip(le.classes_, proba)
    }

    return {
        "id_soumission":       id_soumission,
        "score_plagiat":       round(top_score * 100, 1),
        "score_global":        round(score_plagiat_global * 100, 1),
        "categorie_ml":        categorie,
        "probabilites_ml":     probas_ml,
        "statut":              statut_info["statut"],
        "icone":               statut_info["icone"],
        "message":             statut_info["message"],
        "peut_soumettre":      top_score < SEUIL_REJET,
        "top5_similaires":     similaires,
        "source_principale": {
            "id":          similaires[0]["id_memoire"] if similaires else None,
            "titre":       similaires[0]["titre"] if similaires else None,
            "auteur":      similaires[0]["auteur"] if similaires else None,
            "annee":       similaires[0]["annee"] if similaires else None,
            "similarite":  similaires[0]["pct_similarite"] if similaires else 0,
        },
    }


def analyser_par_sections(intro: str, methodo: str,
                           resultats: str, conclusion: str,
                           id_soumission: str = "INCONNU") -> dict:
    """
    Analyse chaque section du mémoire séparément.
    Permet d'identifier précisément QUELLE partie est plagiée.
    """
    sections = {
        "introduction":  intro,
        "methodologie":  methodo,
        "resultats":     resultats,
        "conclusion":    conclusion,
    }

    rapport_sections = {}
    scores_sections  = []

    for nom_section, texte_section in sections.items():
        if not texte_section or len(texte_section.strip()) < 20:
            rapport_sections[nom_section] = {
                "score": 0.0, "statut": "PROPRE", "similaire_a": None
            }
            continue

        vecteur   = vectoriser(texte_section)
        similaires = rechercher_similaires(vecteur, top_k=3)
        score_sec  = similaires[0]["score_cosinus"] if similaires else 0.0
        scores_sections.append(score_sec)
        statut_sec = statut_depuis_score(score_sec)

        rapport_sections[nom_section] = {
            "score_similarite":  round(score_sec * 100, 1),
            "statut":            statut_sec["statut"],
            "icone":             statut_sec["icone"],
            "similaire_a":       similaires[0] if similaires else None,
            "top3_similaires":   similaires,
        }

    # Score global = moyenne pondérée (introduction et conclusion ont plus de poids)
    poids   = [0.30, 0.25, 0.25, 0.20]
    score_global = sum(s*p for s,p in zip(scores_sections, poids)) \
                   if len(scores_sections) == 4 else \
                   (np.mean(scores_sections) if scores_sections else 0.0)

    statut_global = statut_depuis_score(score_global)

    return {
        "id_soumission":    id_soumission,
        "score_global":     round(score_global * 100, 1),
        "statut_global":    statut_global["statut"],
        "icone":            statut_global["icone"],
        "message":          statut_global["message"],
        "peut_soumettre":   score_global < SEUIL_REJET,
        "sections":         rapport_sections,
        "section_la_plus_suspecte": max(
            rapport_sections.items(),
            key=lambda x: x[1].get("score_similarite", 0)
        )[0],
    }


# ═══════════════════════════════════════════════════════════════════════
# DÉMONSTRATION COMPLÈTE
# ═══════════════════════════════════════════════════════════════════════

print("="*65)
print("MODULE ANTI-PLAGIAT — DÉMONSTRATION COMPLÈTE")
print("="*65)

df_archives  = pd.read_csv("data/memoires_archives.csv")
df_nouvelles = pd.read_csv("data/nouvelles_soumissions.csv")

CAS_TESTS = [
    {
        "label":    "✅ Mémoire ORIGINAL",
        "id":       "NEW-ORIG-001",
        "row":      df_nouvelles[df_nouvelles["type_reel"]=="ORIGINAL"].iloc[0],
    },
    {
        "label":    "⚠️  Mémoire PLAGIAT LÉGER",
        "id":       "NEW-LEG-001",
        "row":      df_nouvelles[df_nouvelles["type_reel"]=="PLAGIAT_LEGER"].iloc[0],
    },
    {
        "label":    "❌ Mémoire PLAGIAT PARTIEL",
        "id":       "NEW-PART-001",
        "row":      df_nouvelles[df_nouvelles["type_reel"]=="PLAGIAT_PARTIEL"].iloc[0],
    },
]

for cas in CAS_TESTS:
    row  = cas["row"]
    texte = str(row["texte_complet"])
    print(f"\n{'─'*65}")
    print(f"CAS : {cas['label']}")
    print(f"Type réel : {row['type_reel']}")

    # ── Analyse texte complet
    rapport = analyser_texte_complet(texte, cas["id"])
    print(f"\n  📊 RAPPORT D'ANALYSE :")
    print(f"     Score plagiat      : {rapport['score_plagiat']}%")
    print(f"     Statut             : {rapport['icone']} {rapport['statut']}")
    print(f"     Catégorie ML       : {rapport['categorie_ml']}")
    print(f"     Peut soumettre     : {'Oui' if rapport['peut_soumettre'] else 'NON — BLOQUÉ'}")
    print(f"\n  🔍 Top 3 archives similaires :")
    for s in rapport["top5_similaires"][:3]:
        print(f"     [{s['pct_similarite']:5.1f}%] {s['titre'][:45]}"
              f"  ({s['domaine']}, {s['annee']})")

    # ── Analyse par sections
    if all(c in row.index for c in ["introduction","methodologie","resultats","conclusion"]):
        rapport_sec = analyser_par_sections(
            str(row.get("introduction","")),
            str(row.get("methodologie","")),
            str(row.get("resultats","")),
            str(row.get("conclusion","")),
            cas["id"],
        )
        print(f"\n  📑 Analyse par section :")
        for nom_sec, info in rapport_sec["sections"].items():
            print(f"     {nom_sec:<15} : {info['icone']} "
                  f"{info.get('score_similarite',0):5.1f}%  {info['statut']}")
        print(f"\n     Section la plus suspecte : {rapport_sec['section_la_plus_suspecte']}")

print(f"\n{'='*65}")
print(f"  ✅ Corpus : {N_ARCHIVES} mémoires indexés")
print(f"  ✅ Modèle : {meta['nom_modele']} | Acc={meta['accuracy']}% | F1={meta['f1_score']}%")
print(f"  ✅ Seuil alerte : {SEUIL_ALERTE*100:.0f}% | Seuil rejet : {SEUIL_REJET*100:.0f}%")
print("="*65)

# ─── API FASTAPI ─────────────────────────────────────────────────────────────

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="API Anti-Plagiat — Plateforme Mémoire",
        version="1.0.0",
        description="Détection de plagiat par analyse sémantique vectorielle"
    )
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])

    class TexteInput(BaseModel):
        id_soumission: str = "INCONNU"
        texte_complet: str = Field(..., min_length=50)

    class SectionsInput(BaseModel):
        id_soumission: str = "INCONNU"
        introduction:  str = ""
        methodologie:  str = ""
        resultats:     str = ""
        conclusion:    str = ""

    class MemoireNouveau(BaseModel):
        id_memoire: str
        titre:      str
        domaine:    str
        annee:      int
        auteur:     str
        texte_complet: str

    @app.get("/sante", tags=["Système"])
    def sante():
        return {"statut": "ok", "module": "Anti-Plagiat",
                "corpus": f"{N_ARCHIVES} mémoires indexés"}

    @app.get("/corpus/stats", tags=["Corpus"])
    def stats_corpus():
        return {
            "nb_memoires_indexes": N_ARCHIVES,
            "dimensions_vecteurs": index_vecteurs.shape[1],
            "modele_classification": meta["nom_modele"],
            "accuracy": meta["accuracy"],
            "seuil_alerte": SEUIL_ALERTE * 100,
            "seuil_rejet":  SEUIL_REJET  * 100,
        }

    @app.post("/analyser", tags=["Analyse"])
    def analyser(req: TexteInput):
        """
        Analyse complète d'un texte.
        Retourne score de plagiat, statut, top-5 sources similaires.
        Appelé automatiquement à chaque dépôt de version.
        """
        if len(req.texte_complet.strip()) < 50:
            raise HTTPException(400, "Texte trop court (minimum 50 caractères)")
        return analyser_texte_complet(req.texte_complet, req.id_soumission)

    @app.post("/analyser-sections", tags=["Analyse"])
    def analyser_sections(req: SectionsInput):
        """
        Analyse section par section (intro, méthodo, résultats, conclusion).
        Identifie précisément quelle partie du mémoire est suspecte.
        """
        return analyser_par_sections(
            req.introduction, req.methodologie,
            req.resultats, req.conclusion, req.id_soumission
        )

    @app.post("/corpus/ajouter", tags=["Corpus"])
    def ajouter_au_corpus(req: MemoireNouveau):
        """
        Ajoute un mémoire validé au corpus de référence après soutenance.
        Chaque nouveau mémoire soutenu enrichit la base de détection.
        """
        global index_vecteurs
        nouveau_vecteur = vectoriser(req.texte_complet).reshape(1, -1)
        index_vecteurs  = np.vstack([index_vecteurs, nouveau_vecteur])

        for key in index_meta:
            if key == "id_memoire": index_meta[key].append(req.id_memoire)
            elif key == "titre":    index_meta[key].append(req.titre)
            elif key == "domaine":  index_meta[key].append(req.domaine)
            elif key == "annee":    index_meta[key].append(req.annee)
            elif key == "auteur":   index_meta[key].append(req.auteur)

        np.save("modeles/index_vecteurs.npy", index_vecteurs)
        with open("modeles/index_metadata.json","w",encoding="utf-8") as f:
            json.dump(index_meta, f, ensure_ascii=False)

        return {
            "message": f"Mémoire {req.id_memoire} ajouté au corpus",
            "nouveau_total": len(index_meta["id_memoire"]),
        }

    print("\n✅ API Anti-Plagiat prête.")
    print("   Lancer : uvicorn etape4_api_antiplagiat:app --reload --port 8005")
    print("   Docs   : http://localhost:8005/docs")

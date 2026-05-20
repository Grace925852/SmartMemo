"""
=============================================================
MODULE ANTI-PLAGIAT AVANC
TAPE 1  GNRATION DES DONNES D'ENTRANEMENT
=============================================================

CE MODULE FAIT QUOI ?
----------------------
Quand un tudiant dpose son mmoire, ce module :

  1. DCOUPE le document en fragments (paragraphes)
  2. TRANSFORME chaque fragment en vecteur numrique (embedding)
      Un texte devient un tableau de 50 chiffres qui capture son SENS
  3. COMPARE ces vecteurs avec ceux de tous les anciens mmoires
      via la similarit cosinus : deux textes similaires = vecteurs proches
  4. GNRE un rapport avec le score de plagiat et les passages copis

POURQUOI LA SIMILARIT VECTORIELLE EST MEILLEURE QU'UNE SIMPLE RECHERCHE ?
---------------------------------------------------------------------------
Recherche classique : "introduction"  "prsentation du sujet"
   Ces phrases sont diffrentes MOT  MOT mais veulent dire la mme chose

Similarit vectorielle : les deux textes donnent des vecteurs TRS proches
   Le systme dtecte la copie mme si les mots ont t changs

APPROCHE UTILISE (sans GPU) :
-------------------------------
  TF-IDF + SVD (Truncated SVD) = LSA (Latent Semantic Analysis)
   Transforme chaque texte en vecteur de 50 dimensions
   Capture les relations smantiques entre les mots
   Fonctionne parfaitement sans GPU
   En production : remplacer par Sentence-BERT pour plus de prcision

DONNES GNRES :
------------------
  - 200 mmoires archivs (corpus de rfrence)
  - 50 nouvelles soumissions  analyser (dont certaines plagies)
  - Paires de textes avec scores de similarit rels
"""

import pandas as pd
import numpy as np
import random
import json
import os

random.seed(42)
np.random.seed(42)

os.makedirs("data",    exist_ok=True)
os.makedirs("modeles", exist_ok=True)

#  CORPUS DE TEXTES ACADMIQUES 
# Paragraphes ralistes pour gnrer les mmoires

INTRO_TEMPLATES = [
    "Ce travail vise  concevoir et implmenter {sujet} en utilisant {tech}. "
    "La problmatique principale est {probleme}. Notre approche repose sur {methode}.",

    "Dans le cadre de ce mmoire, nous proposons {sujet}. "
    "Face  {probleme}, nous avons choisi d'utiliser {tech} comme solution principale. "
    "La mthodologie adopte est {methode}.",

    "L'objectif de cette tude est de rsoudre {probleme} grce  {sujet}. "
    "Nous utilisons {tech} combin avec {methode} pour atteindre cet objectif.",

    "Ce projet de fin d'tudes porte sur {sujet}. "
    "La motivation principale est {probleme} qui constitue un dfi majeur. "
    "Nous proposons une solution base sur {tech} en suivant une approche {methode}.",
]

SUJETS = [
    "un systme de dtection de fraude bancaire",
    "une plateforme de tlmdecine",
    "un moteur de recommandation de cours",
    "un systme de gestion des stocks intelligents",
    "une application de paiement mobile scurise",
    "un systme de surveillance de la qualit de l'air",
    "une plateforme e-commerce pour artisans locaux",
    "un systme de vote lectronique",
    "un chatbot d'assistance mdicale",
    "une application de covoiturage universitaire",
    "un systme de contrle d'accs biomtrique",
    "une plateforme de gestion des ressources humaines",
    "un systme de prdiction du dcrochage scolaire",
    "un outil d'analyse de sentiment sur les rseaux sociaux",
    "un systme d'archivage intelligent de documents",
]

TECHNOLOGIES = [
    "Python et TensorFlow", "React et FastAPI", "Django et PostgreSQL",
    "Flutter et Firebase", "Arduino et Raspberry Pi", "Docker et Kubernetes",
    "machine learning et scikit-learn", "deep learning et PyTorch",
    "blockchain et smart contracts", "NLP et transformers BERT",
]

PROBLEMES = [
    "la lenteur des processus manuels actuels",
    "le manque d'accessibilit aux services dans les zones rurales",
    "la scurit insuffisante des donnes personnelles",
    "le cot lev des solutions existantes sur le march",
    "l'absence d'outils adapts au contexte africain",
    "la difficult d'accs aux soins mdicaux",
    "les pertes financires dues aux erreurs humaines",
    "le manque de traabilit dans les processus administratifs",
]

METHODOLOGIES = [
    "SCRUM avec des sprints de 2 semaines",
    "la recherche exprimentale avec validation empirique",
    "le prototypage rapide et l'itration continue",
    "une tude de cas approfondie avec donnes relles",
    "la recherche-action avec participation des utilisateurs finaux",
]

METHODO_SECTIONS = [
    "La mthodologie de dveloppement choisie est {methode}. "
    "Nous avons structur le travail en {nb_phases} phases distinctes. "
    "Chaque phase comprend des livrables mesurables et des critres de validation clairs.",

    "Pour raliser ce projet, nous avons adopt {methode}. "
    "Cette approche nous permet de livrer des incrments fonctionnels rgulirement. "
    "Le travail a t divis en {nb_phases} itrations de dure gale.",

    "L'approche mthodologique retenue est {methode}. "
    "Elle se dcline en {nb_phases} grandes tapes : analyse des besoins, "
    "conception, implmentation, tests et dploiement.",
]

RESULTATS_SECTIONS = [
    "Les tests raliss montrent que notre solution atteint {perf}% de prcision. "
    "Les performances obtenues dpassent les solutions existantes de {gain}%. "
    "L'interface utilisateur a t valide par {nb_users} utilisateurs rels.",

    "Notre systme a t valu sur un jeu de donnes de {nb_data} enregistrements. "
    "Les rsultats indiquent une amlioration de {gain}% par rapport  l'approche classique. "
    "Le temps de rponse moyen est de {temps}ms, ce qui rpond aux exigences.",

    "Les exprimentations confirment la viabilit de notre approche avec {perf}% d'efficacit. "
    "Compar aux solutions actuelles, nous observons un gain de {gain}% sur les mtriques cls. "
    "Ces rsultats ont t valids par une quipe de {nb_users} experts du domaine.",
]

CONCLUSION_SECTIONS = [
    "Ce travail a permis de dvelopper {sujet} qui rpond efficacement  {probleme}. "
    "Les rsultats obtenus sont satisfaisants et ouvrent la voie  des amliorations futures. "
    "Les perspectives incluent l'intgration de nouvelles fonctionnalits et l'extension  d'autres contextes.",

    "En conclusion, nous avons conu et implment {sujet}. "
    "Notre solution apporte une rponse concrte  {probleme}. "
    "Les travaux futurs porteront sur l'amlioration des performances et la scalabilit du systme.",

    "Ce mmoire prsente {sujet} comme solution  {probleme}. "
    "Les objectifs fixs au dpart ont t atteints. "
    "Cette tude constitue une base solide pour de futures recherches dans ce domaine.",
]


def generer_texte_memoire(sujet, tech, probleme, methode):
    """Gnre un texte de mmoire complet (4 sections)."""
    intro = random.choice(INTRO_TEMPLATES).format(
        sujet=sujet, tech=tech, probleme=probleme, methode=methode
    )
    methodo = random.choice(METHODO_SECTIONS).format(
        methode=methode, nb_phases=random.randint(3, 6)
    )
    resultats = random.choice(RESULTATS_SECTIONS).format(
        perf=random.randint(80, 98),
        gain=random.randint(15, 45),
        nb_users=random.randint(10, 50),
        nb_data=random.randint(500, 10000),
        temps=random.randint(50, 500),
    )
    conclusion = random.choice(CONCLUSION_SECTIONS).format(
        sujet=sujet, probleme=probleme
    )
    return {
        "introduction":  intro,
        "methodologie":  methodo,
        "resultats":     resultats,
        "conclusion":    conclusion,
        "texte_complet": f"{intro} {methodo} {resultats} {conclusion}",
    }


def plagier_texte(texte_original, niveau="partiel"):
    """
    Simule le plagiat en modifiant partiellement un texte.
    niveau = 'leger' (10-30%), 'partiel' (40-70%), 'total' (80-100%)
    """
    mots = texte_original.split()

    SYNONYMES = {
        "concevoir":    "dvelopper",    "implmenter":  "raliser",
        "utilisant":    "employant",     "principal":    "majeur",
        "propose":      "prsente",      "problmatique":"challenge",
        "rsoudre":     "traiter",       "objectif":     "but",
        "approche":     "mthode",       "systme":      "outil",
        "dvelopper":   "construire",    "amlioration": "optimisation",
        "rsultats":    "performances",  "solution":     "rponse",
        "application":  "logiciel",      "plateforme":   "systme",
        "donnes":      "informations",  "utilisateurs": "utilisateurs finaux",
        "montrent":     "indiquent",     "obtenus":      "acquis",
    }

    taux = {"leger": 0.15, "partiel": 0.50, "total": 0.85}[niveau]
    nb_a_changer = int(len(mots) * taux)
    indices = random.sample(range(len(mots)), min(nb_a_changer, len(mots)))

    mots_plagies = mots.copy()
    for idx in indices:
        mot_lower = mots[idx].lower().strip(".,;:!?")
        if mot_lower in SYNONYMES:
            mots_plagies[idx] = SYNONYMES[mot_lower]

    return " ".join(mots_plagies)


#  GNRATION DES MMOIRES ARCHIVS (corpus de rfrence) 

print("=" * 60)
print("MODULE ANTI-PLAGIAT  GNRATION DES DONNES")
print("=" * 60)

print("\n[CORPUS] Generation du corpus de reference (200 anciens memoires)...")

memoires_archives = []
for i in range(200):
    sujet    = random.choice(SUJETS)
    tech     = random.choice(TECHNOLOGIES)
    probleme = random.choice(PROBLEMES)
    methode  = random.choice(METHODOLOGIES)
    texte    = generer_texte_memoire(sujet, tech, probleme, methode)

    memoires_archives.append({
        "id_memoire":     f"ARCH-{i+1:04d}",
        "titre":          f"{sujet.capitalize()} avec {tech}",
        "domaine":        random.choice(["IA","Web","Cyber","Rseau","Mobile","IoT","Cloud","BDD"]),
        "annee":          random.randint(2018, 2024),
        "auteur":         f"Etudiant_{i+1:04d}",
        **texte,
    })

#  GNRATION DES NOUVELLES SOUMISSIONS 

print("[DOC] Generation de 50 nouvelles soumissions (dont plagiees)...")

nouvelles_soumissions = []

# 20 soumissions originales
for i in range(20):
    sujet    = random.choice(SUJETS)
    tech     = random.choice(TECHNOLOGIES)
    probleme = random.choice(PROBLEMES)
    methode  = random.choice(METHODOLOGIES)
    texte    = generer_texte_memoire(sujet, tech, probleme, methode)
    nouvelles_soumissions.append({
        "id_soumission":      f"NEW-ORIG-{i+1:03d}",
        "type_reel":          "ORIGINAL",
        "source_plagiat":     None,
        "niveau_plagiat":     "aucun",
        **texte,
    })

# 15 soumissions avec plagiat lger
for i in range(15):
    source = random.choice(memoires_archives)
    nouvelles_soumissions.append({
        "id_soumission":      f"NEW-LEG-{i+1:03d}",
        "type_reel":          "PLAGIAT_LEGER",
        "source_plagiat":     source["id_memoire"],
        "niveau_plagiat":     "leger",
        "introduction":       plagier_texte(source["introduction"], "leger"),
        "methodologie":       plagier_texte(source["methodologie"], "leger"),
        "resultats":          plagier_texte(source["resultats"], "leger"),
        "conclusion":         plagier_texte(source["conclusion"], "leger"),
        "texte_complet":      plagier_texte(source["texte_complet"], "leger"),
    })

# 15 soumissions avec plagiat partiel
for i in range(15):
    source = random.choice(memoires_archives)
    nouvelles_soumissions.append({
        "id_soumission":      f"NEW-PART-{i+1:03d}",
        "type_reel":          "PLAGIAT_PARTIEL",
        "source_plagiat":     source["id_memoire"],
        "niveau_plagiat":     "partiel",
        "introduction":       plagier_texte(source["introduction"], "partiel"),
        "methodologie":       plagier_texte(source["methodologie"], "partiel"),
        "resultats":          plagier_texte(source["resultats"], "partiel"),
        "conclusion":         plagier_texte(source["conclusion"], "partiel"),
        "texte_complet":      plagier_texte(source["texte_complet"], "partiel"),
    })

#  GNRATION DES PAIRES D'ENTRANEMENT 
# Pour entraner un modle de classification du niveau de plagiat,
# on gnre des paires (texte_original, texte_compare) + score de similarit

print(" Gnration des paires d'entranement (texte A vs texte B)...")

paires = []

# Paires non similaires (similitude ~ 020%)
for i in range(300):
    a = random.choice(memoires_archives)
    b = random.choice(memoires_archives)
    while b["id_memoire"] == a["id_memoire"]:
        b = random.choice(memoires_archives)
    paires.append({
        "id_paire": f"PAIR-{len(paires)+1:05d}",
        "texte_a":  a["texte_complet"],
        "texte_b":  b["texte_complet"],
        "categorie_similarite": "ORIGINAL",  # variable cible catgorielle
        "score_similarite": round(random.uniform(0, 0.20), 3),
    })

# Paires lgrement similaires (2040%)  reformulations mineures
for i in range(150):
    source = random.choice(memoires_archives)
    texte_modifie = plagier_texte(source["texte_complet"], "leger")
    paires.append({
        "id_paire": f"PAIR-{len(paires)+1:05d}",
        "texte_a":  source["texte_complet"],
        "texte_b":  texte_modifie,
        "categorie_similarite": "SIMILAIRE",
        "score_similarite": round(random.uniform(0.20, 0.45), 3),
    })

# Paires fortement similaires (4580%)  plagiat partiel
for i in range(150):
    source = random.choice(memoires_archives)
    texte_plagi = plagier_texte(source["texte_complet"], "partiel")
    paires.append({
        "id_paire": f"PAIR-{len(paires)+1:05d}",
        "texte_a":  source["texte_complet"],
        "texte_b":  texte_plagi,
        "categorie_similarite": "PLAGIAT_PARTIEL",
        "score_similarite": round(random.uniform(0.45, 0.80), 3),
    })

# Paires quasi-identiques (80100%)  plagiat total
for i in range(100):
    source = random.choice(memoires_archives)
    texte_copie = plagier_texte(source["texte_complet"], "total")
    paires.append({
        "id_paire": f"PAIR-{len(paires)+1:05d}",
        "texte_a":  source["texte_complet"],
        "texte_b":  texte_copie,
        "categorie_similarite": "PLAGIAT_TOTAL",
        "score_similarite": round(random.uniform(0.80, 0.99), 3),
    })

random.shuffle(paires)

#  SAUVEGARDE 

df_archives = pd.DataFrame(memoires_archives)
df_nouvelles = pd.DataFrame(nouvelles_soumissions)
df_paires    = pd.DataFrame(paires)

df_archives.to_csv("data/memoires_archives.csv",     index=False)
df_nouvelles.to_csv("data/nouvelles_soumissions.csv", index=False)
df_paires.to_csv("data/paires_entrainement.csv",      index=False)

#  RAPPORT 

print(f"\n[OK] Corpus archive : {len(df_archives)} memoires")
print(f"[OK] Nouvelles soumissions : {len(df_nouvelles)}")
print(f"[OK] Paires d'entrainement : {len(df_paires)}\n")

print("Distribution des paires (variable cible) :")
print("" * 50)
for cat, count in df_paires["categorie_similarite"].value_counts().items():
    pct   = round(count / len(df_paires) * 100, 1)
    barre = "" * (count // 12)
    print(f"  {cat:<20} {count:4d} ({pct:5.1f}%)  {barre}")

print(f"\nDistribution des nouvelles soumissions :")
print("" * 50)
for typ, count in df_nouvelles["type_reel"].value_counts().items():
    print(f"  {typ:<22} {count:4d}")

print(f"\n[OK] Fichiers sauvegardes dans data/")

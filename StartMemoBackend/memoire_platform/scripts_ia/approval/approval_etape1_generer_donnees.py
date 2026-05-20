"""
=============================================================
MODULE APPROVAL & QUALITY CHECK
TAPE 1  GNRATION DES DONNES D'ENTRANEMENT
=============================================================

CE MODULE FAIT QUOI ?
----------------------
Quand un tudiant soumet son projet de mmoire, ce module
value AUTOMATIQUEMENT la qualit du projet avant que le
directeur ou l'examinateur ne le lise.

Il analyse 3 choses :
  1. QUALIT DU SUJET      Le sujet est-il bien formul, cohrent, acadmique ?
  2. FAISABILIT           Peut-on le raliser en 3  6 mois ?
  3. ANTI-DOUBLON          Ce sujet ressemble-t-il trop  un projet dj existant ?

VARIABLE CIBLE (ce que le modle prdit) :
------------------------------------------
   decision : "APPROUVE" / "REVISION_NECESSAIRE" / "REJETE"

CE SCRIPT FAIT QUOI ICI ?
---------------------------
On gnre 600 projets de mmoire fictifs mais ralistes,
avec leurs caractristiques et la dcision du comit.
Ces donnes simulent ce qu'un vrai comit pdagogique
aurait dcid sur ces projets.
"""

import pandas as pd
import numpy as np
import random
import os

random.seed(42)
np.random.seed(42)

os.makedirs("data", exist_ok=True)
os.makedirs("modeles", exist_ok=True)

#  DONNES DE BASE 

# Sujets bien formuls ( tendent vers APPROUVE)
SUJETS_BONNE_QUALITE = [
    ("Conception d'un systme de dtection de fraude bancaire par deep learning au Togo",
     "Ce travail vise  concevoir et implmenter un systme intelligent de dtection de transactions frauduleuses en utilisant des rseaux de neurones LSTM appliqus aux donnes de mobile money au Togo. La mthodologie inclut la collecte de donnes anonymises, le prtraitement, l'entranement du modle et l'valuation des performances sur un jeu de test rel."),

    ("Dveloppement d'une application mobile de tlmdecine pour les zones rurales togolaises",
     "Cette tude propose le dveloppement d'une application Android permettant aux patients des zones rurales d'accder  des consultations mdicales  distance. L'application intgre un module de golocalisation des centres de sant, un systme de prise de rendez-vous et un dossier mdical numrique simplifi."),

    ("Mise en place d'un systme de vote lectronique scuris pour les lections universitaires",
     "Ce projet consiste  concevoir et dployer une plateforme de vote lectronique scurise base sur la cryptographie asymtrique et la blockchain lgre. L'objectif est de garantir l'anonymat, l'intgrit et la traabilit des votes lors des lections au sein de l'universit."),

    ("Analyse prdictive du taux de dcrochage scolaire par apprentissage automatique",
     "Cette recherche applique des algorithmes de machine learning (Random Forest, XGBoost) pour prdire le risque de dcrochage scolaire  partir de donnes acadmiques et socio-conomiques. Un tableau de bord de visualisation est dvelopp pour les responsables pdagogiques."),

    ("Conception d'un entrept de donnes pour le suivi pidmiologique au Ministre de la Sant",
     "Ce projet vise  concevoir un data warehouse selon la modlisation en toile pour centraliser les donnes pidmiologiques nationales. Il inclut la mise en place d'un pipeline ETL, le dploiement sous PostgreSQL et la cration de rapports analytiques sur Power BI."),

    ("Dploiement d'une infrastructure rseau WiFi communautaire  faible cot",
     "Cette tude propose le dploiement d'un rseau WiFi communautaire dans un quartier priurbain de Lom en utilisant des quipements open source. Le projet couvre la conception, la simulation sous GNS3, le dploiement et la mesure des performances relles."),

    ("Implmentation d'un SIEM open source pour la dtection d'intrusions en entreprise",
     "Ce travail consiste  dployer et configurer un SIEM bas sur Wazuh/ELK Stack pour centraliser la gestion des logs et dtecter les intrusions dans une PME locale. Il inclut la dfinition des rgles de corrlation et les procdures de rponse aux incidents."),

    ("Systme embarqu de surveillance environnementale bas sur IoT",
     "Ce projet dveloppe un systme de capteurs connects (Arduino + Raspberry Pi) pour surveiller la qualit de l'air, l'humidit et la temprature dans un environnement industriel. Les donnes sont transmises via MQTT et visualises sur un dashboard Grafana."),

    ("Plateforme e-commerce B2B pour l'approvisionnement des PME africaines",
     "Cette tude conoit une marketplace B2B permettant aux PME d'Afrique de l'Ouest de s'approvisionner auprs de fournisseurs locaux et internationaux. La plateforme intgre un module de paiement mobile money, une gestion des stocks et un systme de notation des fournisseurs."),

    ("Classification automatique de documents administratifs par traitement du langage naturel",
     "Ce projet applique des techniques de NLP (TF-IDF, BERT) pour classifier automatiquement des documents administratifs numriss en catgories prdfinies. L'objectif est de rduire le temps de traitement manuel dans les services administratifs."),
]

# Sujets moyens ( tendent vers REVISION_NECESSAIRE)
SUJETS_QUALITE_MOYENNE = [
    ("Application pour grer les notes des tudiants",
     "Je veux faire une application pour grer les notes. Elle permettra d'entrer les notes et de calculer les moyennes. Ce sera utile pour les professeurs."),

    ("tude sur la scurit des rseaux wifi",
     "Ce projet parle de la scurit wifi. On va voir comment scuriser un rseau wifi et quels sont les problmes qui existent avec les rseaux sans fil dans les entreprises."),

    ("Cration d'un site web pour une cole",
     "Le projet consiste  crer un site web pour une cole. Le site aura des pages pour prsenter l'cole, les cours et les professeurs. Il y aura aussi un espace pour les tudiants."),

    ("Systme de gestion de bibliothque",
     "Dvelopper un logiciel de gestion de bibliothque qui permet d'enregistrer les livres, les emprunts et les retours. Le systme aura une interface simple pour les bibliothcaires."),

    ("Application de chat en temps rel",
     "Ce projet vise  crer une application de messagerie instantane. Les utilisateurs pourront envoyer des messages en temps rel. On utilisera des websockets pour la communication."),

    ("Analyse des donnes de vente d'une entreprise",
     "Ce travail va analyser les donnes de vente d'une entreprise commerciale pour trouver des tendances. On utilisera Excel et Python pour faire les analyses et crer des graphiques."),

    ("Dveloppement d'une application Android pour les transports",
     "On va dvelopper une application Android pour les transports en commun. L'application montrera les horaires et les itinraires disponibles dans la ville."),

    ("Mise en place d'un rseau local pour une entreprise",
     "Ce projet va mettre en place un rseau local pour une petite entreprise. On va choisir les quipements, configurer les switches et les routeurs, et tester la connectivit."),
]

# Sujets mauvais ( tendent vers REJETE)
SUJETS_MAUVAISE_QUALITE = [
    ("Faire un jeu vido",
     "Je veux faire un jeu. Ce sera amusant."),

    ("Application",
     "Une application mobile."),

    ("Recherche sur internet",
     "Je vais chercher des informations sur internet sur plusieurs sujets informatiques et faire un rsum de ce que j'ai trouv."),

    ("Copie du systme bancaire",
     "Reproduire exactement le systme de la banque Ecobank avec toutes ses fonctionnalits en 2 mois."),

    ("Intelligence artificielle gnrale",
     "Crer une intelligence artificielle gnrale capable de tout faire comme un humain."),

    ("tude de tout ce qui concerne les rseaux",
     "Ce mmoire va couvrir tous les aspects des rseaux informatiques depuis les dbuts jusqu' aujourd'hui."),

    ("Systme comme Google",
     "Crer un moteur de recherche similaire  Google pour l'Afrique."),

    ("Projet sur la blockchain",
     "La blockchain c'est bien. Je vais faire quelque chose avec la blockchain."),
]

DOMAINES = [
    "IA / Machine Learning", "Dveloppement Web", "Cyberscurit",
    "Rseaux", "Mobile", "Systmes Embarqus", "Cloud / DevOps", "Bases de donnes"
]

FILIERES = [
    "Gnie Logiciel", "Rseaux et Tlcommunications", "Data Science",
    "Systmes Embarqus", "Cyberscurit", "Gnie Informatique"
]

METHODOLOGIES = [
    "Dveloppement logiciel (SCRUM)", "Recherche exprimentale",
    "Recherche applique", "tude de cas", "Prototypage"
]

#  FONCTIONS D'EXTRACTION DE FEATURES 

def calculer_features_texte(titre, description):
    """
    Extrait des caractristiques numriques mesurables
    depuis le titre et la description du projet.
    Ce sont ces chiffres que le modle va apprendre  interprter.
    """
    # Longueurs
    nb_mots_titre       = len(titre.split())
    nb_mots_description = len(description.split())
    nb_phrases_desc     = description.count('.') + description.count('?') + 1

    # Richesse du vocabulaire
    mots_desc   = description.lower().split()
    mots_uniques = len(set(mots_desc))
    ratio_vocab  = round(mots_uniques / max(len(mots_desc), 1), 3)

    # Prsence de mots-cls acadmiques (indicateurs de qualit)
    mots_academiques = [
        "objectif", "mthodologie", "analyser", "concevoir", "dvelopper",
        "implmenter", "valuer", "mesurer", "tester", "optimiser",
        "rsultats", "donnes", "algorithme", "systme", "plateforme",
        "tude", "recherche", "performance", "scurit", "architecture",
        "dployer", "modle", "approche", "framework", "solution"
    ]
    desc_lower = description.lower()
    score_mots_academiques = sum(1 for m in mots_academiques if m in desc_lower)

    # Prsence de mots techniques (indicateurs de domaine clair)
    mots_techniques = [
        "python", "java", "react", "angular", "fastapi", "django", "flask",
        "tensorflow", "pytorch", "docker", "kubernetes", "postgresql", "mysql",
        "mongodb", "aws", "linux", "android", "flutter", "arduino",
        "machine learning", "deep learning", "nlp", "api", "rest", "json",
        "lstm", "cnn", "bert", "blockchain", "iot", "mqtt", "scrum", "agile"
    ]
    score_mots_techniques = sum(1 for m in mots_techniques if m in desc_lower)

    # Indicateurs ngatifs (mauvaise qualit)
    mots_vagues = [
        "tout", "plusieurs", "beaucoup", "amusant", "bien", "simple",
        "facile", "rapide", "chercher", "rsum", "copie", "similaire  google",
        "comme facebook", "comme whatsapp"
    ]
    score_mots_vagues = sum(1 for m in mots_vagues if m in desc_lower)

    # Prsence d'une mthodologie clairement dfinie
    methodo_keywords = [
        "mthodologie", "approche", "mthode", "scrum", "agile",
        "cycle de vie", "tapes", "phases", "processus", "dmarche"
    ]
    a_methodologie = int(any(m in desc_lower for m in methodo_keywords))

    # Prsence d'objectifs clairs
    objectif_keywords = [
        "objectif", "but", "finalit", "vise ", "consiste ",
        "permettre de", "l'objectif est", "ce projet vise"
    ]
    a_objectifs_clairs = int(any(m in desc_lower for m in objectif_keywords))

    # Faisabilit estime (heuristique)
    mots_infaisable = [
        "tout", "gnral", "complet", "exhaustif", "comme google",
        "intelligence artificielle gnrale", "tous les aspects"
    ]
    est_infaisable = int(any(m in desc_lower for m in mots_infaisable))

    return {
        "nb_mots_titre":           nb_mots_titre,
        "nb_mots_description":     nb_mots_description,
        "nb_phrases_description":  nb_phrases_desc,
        "ratio_vocabulaire":       ratio_vocab,
        "score_mots_academiques":  score_mots_academiques,
        "score_mots_techniques":   score_mots_techniques,
        "score_mots_vagues":       score_mots_vagues,
        "a_methodologie":          a_methodologie,
        "a_objectifs_clairs":      a_objectifs_clairs,
        "est_infaisable":          est_infaisable,
    }


def determiner_decision(features, qualite_base):
    """
    Dtermine la dcision du comit en fonction des features
    et de la qualit de base du sujet.
    Ajoute du bruit pour rendre les donnes ralistes.
    """
    score = 0

    # Critres positifs
    if features["nb_mots_titre"] >= 8:             score += 2
    if features["nb_mots_description"] >= 80:      score += 3
    if features["score_mots_academiques"] >= 5:    score += 3
    if features["score_mots_techniques"] >= 3:     score += 2
    if features["a_methodologie"] == 1:            score += 3
    if features["a_objectifs_clairs"] == 1:        score += 2
    if features["ratio_vocabulaire"] >= 0.6:       score += 1

    # Critres ngatifs
    if features["score_mots_vagues"] >= 2:         score -= 3
    if features["est_infaisable"] == 1:            score -= 5
    if features["nb_mots_description"] < 30:       score -= 4
    if features["score_mots_academiques"] < 2:     score -= 2

    # Bonus selon qualit de base
    bonus = {"bon": 5, "moyen": 0, "mauvais": -5}
    score += bonus[qualite_base]

    # Bruit alatoire raliste
    score += random.uniform(-1.5, 1.5)

    # Dcision finale
    if score >= 8:
        return "APPROUVE"
    elif score >= 3:
        return "REVISION_NECESSAIRE"
    else:
        return "REJETE"


def generer_score_similarite():
    """Score de similarit avec les projets existants (0 = unique, 1 = copie)"""
    return round(random.uniform(0.0, 0.95), 3)


#  GNRATION DES 600 PROJETS 

print("=" * 60)
print("MODULE APPROVAL  GNRATION DES DONNES")
print("=" * 60)

projets = []

# 250 projets de bonne qualit
for i in range(250):
    titre, description = random.choice(SUJETS_BONNE_QUALITE)
    # Variations lgres pour diversifier
    titre = titre + (f"  Cas d'tude {i%10+1}" if i % 5 == 0 else "")
    features = calculer_features_texte(titre, description)
    decision = determiner_decision(features, "bon")
    score_sim = round(random.uniform(0.0, 0.45), 3)  # Bons sujets moins similaires

    projets.append({
        "id_projet": f"PRJ-{i+1:04d}",
        "titre": titre,
        "description": description,
        "domaine": random.choice(DOMAINES),
        "filiere_etudiant": random.choice(FILIERES),
        "methodologie": random.choice(METHODOLOGIES),
        "score_similarite_existants": score_sim,
        **features,
        "decision": decision,   #  VARIABLE CIBLE
    })

# 220 projets de qualit moyenne
for i in range(220):
    titre, description = random.choice(SUJETS_QUALITE_MOYENNE)
    titre = titre + (f" v{i%3+2}" if i % 4 == 0 else "")
    features = calculer_features_texte(titre, description)
    decision = determiner_decision(features, "moyen")
    score_sim = round(random.uniform(0.2, 0.75), 3)

    projets.append({
        "id_projet": f"PRJ-{250+i+1:04d}",
        "titre": titre,
        "description": description,
        "domaine": random.choice(DOMAINES),
        "filiere_etudiant": random.choice(FILIERES),
        "methodologie": random.choice(METHODOLOGIES),
        "score_similarite_existants": score_sim,
        **features,
        "decision": decision,
    })

# 130 projets de mauvaise qualit
for i in range(130):
    titre, description = random.choice(SUJETS_MAUVAISE_QUALITE)
    features = calculer_features_texte(titre, description)
    decision = determiner_decision(features, "mauvais")
    score_sim = round(random.uniform(0.5, 0.95), 3)

    projets.append({
        "id_projet": f"PRJ-{470+i+1:04d}",
        "titre": titre,
        "description": description,
        "domaine": random.choice(DOMAINES),
        "filiere_etudiant": random.choice(FILIERES),
        "methodologie": random.choice(METHODOLOGIES),
        "score_similarite_existants": score_sim,
        **features,
        "decision": decision,
    })

# Mlanger les donnes
random.shuffle(projets)

df = pd.DataFrame(projets)
chemin = "data/projets_entrainement.csv"
df.to_csv(chemin, index=False)

#  RAPPORT 

print(f"\n {len(df)} projets gnrs\n")
print("Distribution des dcisions (variable cible) :")
print("" * 45)
for decision, count in df["decision"].value_counts().items():
    barre = "" * (count // 8)
    pct   = round(count / len(df) * 100, 1)
    print(f"  {decision:<25} {count:3d} ({pct:4.1f}%)  {barre}")

print("\nDistribution des domaines :")
print("" * 45)
for dom, count in df["domaine"].value_counts().items():
    print(f"  {dom:<30} {count:3d}")

print(f"\n Fichier  {chemin}")
print(f"   Dimensions : {df.shape[0]} lignes  {df.shape[1]} colonnes")
print("\nColonnes gnres :")
for col in df.columns:
    print(f"   {col}")

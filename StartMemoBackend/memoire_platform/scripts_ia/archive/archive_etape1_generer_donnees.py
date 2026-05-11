"""
=============================================================
MODULE SMART ARCHIVE
TAPE 1  GNRATION DES DONNES + AUTO-TAGGING
=============================================================

CE MODULE FAIT QUOI ?
----------------------
C'est la bibliothque intelligente de la plateforme.

  1. INDEXATION : Chaque mmoire soutenu est automatiquement
     index avec ses mtadonnes + son embedding vectoriel

  2. AUTO-TAGGING : L'IA assigne automatiquement des tags
     (thme, domaine, mthodologie, mots-cls) sans intervention humaine

  3. RECHERCHE SMANTIQUE : Un utilisateur tape
     "application sant zones rurales Afrique"  le systme
     retourne les mmoires les plus pertinents, mme si ces
     mots exacts ne figurent pas dans les titres

  4. RECOMMANDATION : "Vous consultez ce mmoire sur l'IA
     mdicale  voici 3 travaux similaires que vous pourriez
     trouver utiles"

DIFFRENCE AVEC L'ANTI-PLAGIAT :
----------------------------------
  Anti-plagiat  cherche les COPIES (mauvaise chose)
  Smart Archive  cherche les TRAVAUX SIMILAIRES pour s'inspirer
  Mme technologie (TF-IDF + LSA), usage diffrent.

DONNES GNRES :
------------------
  300 mmoires archivs avec mtadonnes compltes
  + tags auto-gnrs
  + embeddings vectoriels
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

#  DONNES DE BASE 

DOMAINES = [
    "IA / Machine Learning", "Dveloppement Web", "Cyberscurit",
    "Rseaux", "Mobile", "Systmes Embarqus", "Cloud / DevOps", "Bases de donnes"
]

METHODOLOGIES = [
    "Dveloppement logiciel (SCRUM)",
    "Recherche exprimentale",
    "Recherche applique",
    "tude de cas",
    "Prototypage rapide",
    "Recherche-action",
    "Dveloppement dirig par les tests (TDD)",
]

NIVEAUX = ["Licence 3", "Master 1", "Master 2"]
ANNEES  = list(range(2018, 2025))

SUJETS_PAR_DOMAINE = {
    "IA / Machine Learning": [
        ("Dtection de fraude bancaire par deep learning",
         "Ce travail propose un systme de dtection des transactions frauduleuses "
         "bas sur les rseaux LSTM. Les donnes proviennent d'une banque togolaise. "
         "Nous avons compar plusieurs architectures deep learning sur 50 000 transactions."),
        ("Systme de recommandation de cours personnaliss",
         "Nous dveloppons un moteur de recommandation hybride combinant filtrage "
         "collaboratif et content-based pour personnaliser les parcours d'apprentissage "
         "en ligne. L'valuation montre 87% de pertinence sur des donnes relles."),
        ("Prdiction du dcrochage scolaire par machine learning",
         "Ce projet applique Random Forest et XGBoost pour identifier les tudiants "
         " risque de dcrochage  partir de donnes acadmiques et comportementales. "
         "Un tableau de bord de visualisation est dvelopp pour les responsables."),
        ("Chatbot mdical en langues locales africaines",
         "Dveloppement d'un assistant conversationnel pour orienter les patients "
         "en franais et en Ew. Utilisation de BERT fine-tun et d'une base de "
         "connaissances mdicales valide par des professionnels de sant."),
        ("Classification d'images agricoles par CNN",
         "Systme de dtection automatique des maladies des cultures grce  des "
         "rseaux convolutifs. Dataset de 15 000 images de plantes annotes. "
         "Prcision de 94% sur la classification de 8 maladies principales."),
        ("Analyse de sentiment pour les lections africaines",
         "Application du NLP pour analyser l'opinion publique sur les rseaux "
         "sociaux pendant les campagnes lectorales. Modle CamemBERT adapt "
         "au franais africain avec 89% d'exactitude."),
    ],
    "Dveloppement Web": [
        ("Plateforme de gestion des stages universitaires",
         "Application full-stack React/FastAPI permettant aux tudiants de postuler "
         "aux stages, aux entreprises de publier des offres et  l'universit de "
         "suivre les conventions. Dploye sur 3 universits togolaises."),
        ("Systme de vote lectronique scuris",
         "Plateforme de vote en ligne base sur la cryptographie asymtrique RSA "
         "et la blockchain lgre. Garantit l'anonymat, l'intgrit et la traabilit "
         "des votes. Test lors d'une lection tudiante relle."),
        ("Portail de tlmdecine pour zones rurales",
         "Application web de consultation mdicale  distance intgrant la "
         "golocalisation des centres de sant, la prise de rendez-vous et "
         "le dossier mdical numrique simplifi. Mode offline disponible."),
        ("E-commerce pour artisans locaux togolais",
         "Marketplace permettant aux artisans de vendre en ligne avec intgration "
         "du paiement mobile money (Flooz, T-Money). Interface bilingue "
         "franais/anglais. 120 artisans onboards lors du lancement pilote."),
    ],
    "Cyberscurit": [
        ("Audit de scurit des infrastructures bancaires",
         "valuation complte de la posture de scurit d'une banque locale par "
         "tests de pntration, analyse de code et revue de configuration. "
         "Rapport de 47 vulnrabilits identifies avec plan de remdiation."),
        ("Implmentation d'un SIEM open source",
         "Dploiement et configuration de Wazuh/ELK Stack pour la dtection "
         "d'intrusions en temps rel. Dfinition de 120 rgles de corrlation "
         "et procdures de rponse aux incidents pour une PME."),
        ("Scurisation des applications mobile banking",
         "Analyse des vulnrabilits des applications de paiement mobile au Togo "
         "selon OWASP Mobile Top 10. Implmentation des contre-mesures et "
         "chiffrement end-to-end des transactions."),
    ],
    "Rseaux": [
        ("Rseau WiFi communautaire  faible cot",
         "Conception et dploiement d'une infrastructure WiFi dans un quartier "
         "de Lom avec quipements open source (OpenWRT). Couverture de 2km, "
         "120 utilisateurs connects simultanment, cot 40% infrieur au march."),
        ("Optimisation QoS dans les rseaux 4G",
         "tude et amlioration de la qualit de service pour les applications "
         "temps rel sur rseau mobile 4G/LTE. Simulation sous NS-3 et validation "
         "terrain avec mesures de latence et dbit."),
        ("Architecture rseau IoT pour smart city",
         "Conception d'une infrastructure de capteurs connects pour la gestion "
         "intelligente des feux de circulation, de l'clairage public et des "
         "dchets dans une ville de taille moyenne."),
    ],
    "Mobile": [
        ("Application de paiement mobile pour petits commerants",
         "App Android permettant aux commerants informels d'accepter les paiements "
         "digitaux via NFC et QR code. Intgration mobile money. "
         "500 commerants pilotes dans 3 marchs de Lom."),
        ("Golocalisation des transports en commun  Lom",
         "Systme de suivi temps rel des bus et taxis-motos avec application "
         "mobile passager et dashboard chauffeur. Architecture microservices "
         "avec WebSockets pour les mises  jour en temps rel."),
        ("Application de suivi de grossesse pour zones rurales",
         "App mobile hors-ligne pour le suivi mdical des femmes enceintes "
         "sans connexion internet. Synchronisation diffre des donnes. "
         "Dploye dans 12 centres de sant ruraux, 800 femmes suivies."),
    ],
    "Systmes Embarqus": [
        ("Systme de surveillance de la qualit de l'air",
         "Rseau de capteurs IoT autonomes mesurant CO2, PM2.5, NO2 et temprature. "
         "Transmission MQTT vers dashboard Grafana. Autonomie 6 mois sur batterie "
         "avec panneau solaire. Dploy dans 5 quartiers de Lom."),
        ("Irrigation automatique intelligente",
         "Systme embarqu sur Arduino/Raspberry Pi pour l'irrigation selon "
         "l'humidit du sol et les prvisions mto. conomie d'eau de 35% "
         "mesure sur 6 mois dans une exploitation agricole pilote."),
        ("Contrle d'accs biomtrique  faible cot",
         "Systme de contrle d'accs par empreinte digitale et reconnaissance "
         "faciale pour scuriser des locaux  budget limit. Cot matriel "
         "sous 50 000 FCFA. Dploy dans 3 tablissements scolaires."),
    ],
    "Cloud / DevOps": [
        ("Migration infrastructure on-premise vers AWS",
         "Planification et excution complte de la migration cloud d'une PME "
         "locale. Architecture 3-tiers sur AWS avec auto-scaling, backup "
         "automatique et rduction des cots d'infrastructure de 40%."),
        ("Pipeline CI/CD pour quipe de dveloppement",
         "Mise en place d'un pipeline d'intgration et dploiement continus "
         "avec GitHub Actions, Docker et Kubernetes. Rduction du temps de "
         "dploiement de 2 jours  15 minutes. 0 rgression en production."),
        ("Systme de monitoring applicatif temps rel",
         "Dploiement d'une stack de monitoring avec Prometheus, Grafana et "
         "alerting automatique. Couverture de 15 microservices avec dashboards "
         "mtier et techniques. MTTR rduit de 4h  20min."),
    ],
    "Bases de donnes": [
        ("Entrept de donnes pour le Ministre de la Sant",
         "Conception d'un data warehouse selon modlisation en toile pour "
         "centraliser les donnes pidmiologiques nationales. Pipeline ETL "
         "automatis, 50M enregistrements, requtes analytiques en < 2s."),
        ("Optimisation performances BDD hospitalire",
         "Analyse et optimisation d'un systme de gestion hospitalire sous "
         "PostgreSQL. Indexation, partitionnement et rcriture de requtes. "
         "Rduction du temps de rponse moyen de 8s  0.3s."),
        ("Archivage numrique des actes d'tat civil",
         "Base de donnes structure pour la numrisation et l'archivage des "
         "actes de naissance, mariage et dcs. OCR automatique sur documents "
         "scanns. 500 000 actes numriss, recherche en temps rel."),
    ],
}

TAGS_PAR_DOMAINE = {
    "IA / Machine Learning":  ["machine-learning","deep-learning","nlp","python",
                                "tensorflow","neural-network","classification","prediction"],
    "Dveloppement Web":      ["react","fastapi","django","full-stack","rest-api",
                                "postgresql","docker","javascript"],
    "Cyberscurit":          ["pentesting","siem","owasp","cryptographie","forensics",
                                "audit","intrusion","vulnerabilite"],
    "Rseaux":                ["wifi","4g","iot","qos","tcp-ip","cisco","ns3","protocole"],
    "Mobile":                 ["android","flutter","ux","mobile-money","offline",
                                "geolocalisation","react-native","kotlin"],
    "Systmes Embarqus":     ["arduino","raspberry-pi","iot","capteurs","mqtt",
                                "temps-reel","energie","embarque"],
    "Cloud / DevOps":         ["aws","docker","kubernetes","ci-cd","terraform",
                                "monitoring","microservices","devops"],
    "Bases de donnes":       ["postgresql","mongodb","etl","datawarehouse","sql",
                                "nosql","optimisation","indexation"],
}

CONTEXTES_AFRIQUE = [
    "Togo", "Afrique de l'Ouest", "zones rurales", "mobile money",
    "langues locales", "contexte africain", "Lom", "PME africaine",
]


def generer_resume(sujet, description, domaine, methodologie):
    contexte = random.choice(CONTEXTES_AFRIQUE)
    return (
        f"{description} "
        f"Ce travail s'inscrit dans le contexte de {contexte}. "
        f"La mthodologie adopte est {methodologie}. "
        f"Les rsultats obtenus constituent une contribution "
        f"significative au domaine de {domaine}."
    )


def auto_tagging(titre, description, domaine):
    """
    Auto-tagging par IA : assigne automatiquement des tags
    en analysant le titre et la description du mmoire.
    """
    tags = set()

    # Tags du domaine
    tags.update(random.sample(TAGS_PAR_DOMAINE[domaine], k=random.randint(3, 5)))

    # Tags extraits du texte (simulation de NLP)
    texte = (titre + " " + description).lower()
    mots_cles_tech = {
        "python": "python", "react": "react", "fastapi": "fastapi",
        "tensorflow": "tensorflow", "pytorch": "pytorch", "bert": "bert",
        "docker": "docker", "kubernetes": "kubernetes", "aws": "aws",
        "android": "android", "flutter": "flutter", "arduino": "arduino",
        "postgresql": "postgresql", "mongodb": "mongodb", "mysql": "mysql",
        "lstm": "deep-learning", "cnn": "deep-learning", "transformer": "nlp",
        "blockchain": "blockchain", "iot": "iot", "mqtt": "iot",
        "scrum": "agile", "agile": "agile", "microservices": "microservices",
    }
    for mot, tag in mots_cles_tech.items():
        if mot in texte:
            tags.add(tag)

    # Tag contexte africain si applicable
    if any(c.lower() in texte for c in ["togo","lom","afrique","africain"]):
        tags.add("afrique")

    return sorted(list(tags))


#  GNRATION DES 300 MMOIRES ARCHIVS 

print("=" * 60)
print("MODULE SMART ARCHIVE  GNRATION DES DONNES")
print("=" * 60)
print("\n Gnration de 300 mmoires archivs...")

memoires = []
for i in range(300):
    domaine     = random.choice(DOMAINES)
    sujets_dom  = SUJETS_PAR_DOMAINE[domaine]
    titre, desc = random.choice(sujets_dom)
    methodologie = random.choice(METHODOLOGIES)
    niveau      = random.choice(NIVEAUX)
    annee       = random.choice(ANNEES)
    tags        = auto_tagging(titre, desc, domaine)
    resume      = generer_resume(titre, desc, domaine, methodologie)

    # Score de qualit alatoire (simulation de la note de soutenance)
    note_soutenance = round(random.uniform(10, 20), 2)

    memoires.append({
        "id_memoire":      f"MEM-{i+1:04d}",
        "titre":           titre,
        "description":     desc,
        "resume":          resume,
        "texte_complet":   f"{titre}. {desc} {resume}",
        "domaine":         domaine,
        "methodologie":    methodologie,
        "niveau":          niveau,
        "annee":           annee,
        "auteur":          f"Etudiant_{i+1:04d}",
        "directeur":       f"Dr. Professeur_{random.randint(1,15):02d}",
        "note_soutenance": note_soutenance,
        "tags":            "|".join(tags),
        "nb_tags":         len(tags),
        "est_public":      int(random.random() > 0.1),  # 90% publics
    })

df = pd.DataFrame(memoires)
df.to_csv("data/memoires_archives.csv", index=False)

#  RAPPORT 

print(f"\n {len(df)} mmoires gnrs\n")
print("Distribution par domaine :")
print("" * 50)
for dom, count in df["domaine"].value_counts().items():
    barre = "" * (count // 3)
    print(f"  {dom:<30} {count:3d}  {barre}")

print(f"\nDistribution par anne :")
print("" * 50)
for annee, count in df["annee"].value_counts().sort_index().items():
    barre = "" * (count // 2)
    print(f"  {annee}  {count:3d} mmoires  {barre}")

print(f"\nTags les plus frquents :")
print("" * 50)
all_tags = []
for tags_str in df["tags"]:
    all_tags.extend(tags_str.split("|"))
from collections import Counter
top_tags = Counter(all_tags).most_common(10)
for tag, count in top_tags:
    barre = "" * (count // 4)
    print(f"  {tag:<25} {count:3d}  {barre}")

print(f"\n Fichier sauvegard  data/memoires_archives.csv")

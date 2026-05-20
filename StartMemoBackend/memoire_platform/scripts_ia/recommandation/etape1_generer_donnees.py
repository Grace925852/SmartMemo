"""
=============================================================
TAPE 1  GNRATION DES DONNES D'ENTRANEMENT
Module : Recommandation de sujets de mmoire
=============================================================

CE SCRIPT FAIT QUOI ?
---------------------
On simule les fiches de 500 anciens tudiants avec :
  - leur profil (filire, notes, comptences, intrts)
  - le sujet de mmoire qu'ils ont finalement choisi
  - le domaine de ce sujet (c'est notre variable cible = ce que le modle doit apprendre  prdire)

POURQUOI ON GNRE DES DONNES ?
---------------------------------
On n'a pas encore de vraies donnes de l'universit.
Ces donnes simules sont RALISTES : elles respectent la logique
"un tudiant fort en IA choisira probablement un sujet IA".
Une fois que l'universit nous donne de vraies donnes, on remplace
ce fichier et on r-entrane le modle.
"""

import pandas as pd
import numpy as np
import random
import json
import os

# Fixer la graine pour que les rsultats soient reproductibles
random.seed(42)
np.random.seed(42)

#  DONNES DE BASE 

FILIERES = [
    "Gnie Logiciel",
    "Rseaux et Tlcommunications",
    "Data Science",
    "Systmes Embarqus",
    "Cyberscurit",
    "Gnie Informatique",
]

NIVEAUX = ["Licence 3", "Master 1", "Master 2"]

# Comptences regroupes par famille
COMPETENCES_PAR_DOMAINE = {
    "IA / Machine Learning": ["Python", "TensorFlow", "scikit-learn", "NLP", "Deep Learning", "Pandas"],
    "Dveloppement Web":     ["React", "Vue.js", "Node.js", "Django", "FastAPI", "HTML/CSS"],
    "Bases de donnes":      ["PostgreSQL", "MongoDB", "MySQL", "ElasticSearch", "Redis"],
    "Rseaux":               ["Cisco", "Linux", "TCP/IP", "VPN", "Wireshark", "Firewall"],
    "Cyberscurit":         ["Pentesting", "Cryptographie", "OWASP", "Forensics", "Kali Linux"],
    "Mobile":                ["Android", "Flutter", "React Native", "Swift", "Kotlin"],
    "Systmes":              ["C/C++", "Arduino", "Raspberry Pi", "VHDL", "Assembleur"],
    "Cloud / DevOps":        ["Docker", "Kubernetes", "AWS", "CI/CD", "Terraform"],
}

# Domaines de sujets de mmoire (= notre variable cible Y)
DOMAINES = list(COMPETENCES_PAR_DOMAINE.keys())

# Sujets de mmoire par domaine (exemples ralistes)
SUJETS_PAR_DOMAINE = {
    "IA / Machine Learning": [
        "Systme de recommandation de cours en ligne par apprentissage automatique",
        "Dtection des maladies agricoles par vision par ordinateur",
        "Analyse de sentiment des rseaux sociaux pour les lections africaines",
        "Chatbot intelligent pour l'assistance mdicale au Togo",
        "Prdiction du taux de dcrochage scolaire par machine learning",
        "Classification automatique des documents administratifs par NLP",
        "Systme de dtection de fraude bancaire par deep learning",
        "Reconnaissance vocale pour les langues locales africaines",
    ],
    "Dveloppement Web": [
        "Plateforme de gestion des stages universitaires en ligne",
        "Systme de vote lectronique scuris pour associations tudiantes",
        "Application web de gestion des ressources humaines pour PME",
        "Plateforme e-commerce pour artisans locaux au Togo",
        "Systme de gestion des bourses universitaires en ligne",
        "Portail de tlservices administratifs pour mairies",
        "Application web de tlmdecine pour zones rurales",
    ],
    "Bases de donnes": [
        "Conception d'un entrept de donnes pour le ministre de la sant",
        "Optimisation des requtes dans les systmes de gestion hospitalire",
        "Migration d'un systme legacy vers une base de donnes NoSQL",
        "Systme d'archivage intelligent des actes d'tat civil",
        "Base de donnes spatiale pour la gestion du cadastre urban",
    ],
    "Rseaux": [
        "Dploiement d'un rseau LAN scuris pour tablissement scolaire",
        "Mise en place d'un rseau WiFi municipal  faible cot",
        "tude et dploiement de la fibre optique dans une universit",
        "Optimisation de la qualit de service dans les rseaux mobiles 4G",
        "Simulation d'un rseau de capteurs IoT pour smart city",
    ],
    "Cyberscurit": [
        "Audit de scurit des infrastructures informatiques bancaires au Togo",
        "Mise en place d'un SIEM pour la dtection des intrusions",
        "Analyse forensique des incidents de cyberscurit",
        "Scurisation des applications mobiles de mobile banking",
        "Implmentation d'un systme Zero Trust pour entreprise",
    ],
    "Mobile": [
        "Application mobile de paiement via mobile money pour petits commerants",
        "Systme de golocalisation des transports en commun  Lom",
        "Application de suivi de grossesse pour zones rurales",
        "Plateforme mobile de covoiturage universitaire",
        "Application d'apprentissage des langues locales sur mobile",
    ],
    "Systmes": [
        "Systme embarqu de surveillance de la qualit de l'air",
        "Conception d'un systme d'irrigation automatique intelligent",
        "Systme de contrle d'accs biomtrique  faible cot",
        "Compteur d'nergie intelligent pour le suivi de consommation",
        "Robot de dsinfection automatique pour tablissements de sant",
    ],
    "Cloud / DevOps": [
        "Migration d'une infrastructure on-premise vers AWS pour PME",
        "Mise en place d'un pipeline CI/CD pour quipe de dveloppement",
        "Architecture microservices avec Docker et Kubernetes",
        "Plateforme de monitoring des applications en temps rel",
        "Systme de sauvegarde automatique dans le cloud pour PME africaines",
    ],
}

# Centres d'intrt par domaine
INTERETS_PAR_DOMAINE = {
    "IA / Machine Learning": ["intelligence artificielle", "data science", "automatisation", "recherche", "statistiques"],
    "Dveloppement Web":     ["dveloppement web", "design UI", "e-commerce", "startup", "applications web"],
    "Bases de donnes":      ["gestion des donnes", "performance", "analyse", "systmes d'information"],
    "Rseaux":               ["infrastructure", "tlcommunications", "protocoles", "administration rseau"],
    "Cyberscurit":         ["scurit informatique", "hacking thique", "protection des donnes", "forensics"],
    "Mobile":                ["applications mobiles", "UX mobile", "fintech", "sant numrique"],
    "Systmes":              ["lectronique", "robotique", "IoT", "systmes temps rel"],
    "Cloud / DevOps":        ["cloud computing", "automatisation", "infrastructure", "dploiement"],
}

# Modules scolaires par filire
MODULES_PAR_FILIERE = {
    "Gnie Logiciel":                ["Algorithmique", "POO", "Gnie Logiciel", "BDD", "Architecture", "IA", "Web"],
    "Rseaux et Tlcommunications": ["Rseaux", "TCP/IP", "Scurit Rseau", "Administration Linux", "Tlcoms"],
    "Data Science":                  ["Statistiques", "Machine Learning", "Python", "Big Data", "Visualisation", "IA"],
    "Systmes Embarqus":            ["lectronique", "Programmation C", "Microcontrleurs", "FPGA", "Temps Rel"],
    "Cyberscurit":                 ["Cryptographie", "Scurit Rseau", "Forensics", "Pentesting", "OSINT"],
    "Gnie Informatique":            ["Algorithmique", "BDD", "Rseaux", "IA", "Web", "Mobile", "Cloud"],
}

#  LOGIQUE DE GNRATION 

def choisir_domaine_selon_profil(filiere, competences_choisies, interets_choisis):
    """
    Logique raliste : le domaine choisi dpend de la filire,
    des comptences et des intrts de l'tudiant.
    Ce n'est pas alatoire  on introduit une vraie corrlation
    pour que le modle puisse l'apprendre.
    """
    scores = {d: 0 for d in DOMAINES}

    # Bonus selon filire
    bonus_filiere = {
        "Gnie Logiciel":                {"Dveloppement Web": 3, "IA / Machine Learning": 2, "Cloud / DevOps": 2},
        "Rseaux et Tlcommunications": {"Rseaux": 4, "Cyberscurit": 2, "Cloud / DevOps": 1},
        "Data Science":                  {"IA / Machine Learning": 5, "Bases de donnes": 2},
        "Systmes Embarqus":            {"Systmes": 5, "IA / Machine Learning": 1, "Rseaux": 1},
        "Cyberscurit":                 {"Cyberscurit": 5, "Rseaux": 2},
        "Gnie Informatique":            {"Dveloppement Web": 2, "Mobile": 2, "IA / Machine Learning": 2, "Cloud / DevOps": 1},
    }
    for domaine, pts in bonus_filiere.get(filiere, {}).items():
        scores[domaine] += pts

    # Bonus selon comptences
    for comp in competences_choisies:
        for domaine, comps_domaine in COMPETENCES_PAR_DOMAINE.items():
            if comp in comps_domaine:
                scores[domaine] += 2

    # Bonus selon intrts
    for interet in interets_choisis:
        for domaine, interets_domaine in INTERETS_PAR_DOMAINE.items():
            if interet in interets_domaine:
                scores[domaine] += 1

    # Ajouter un peu de bruit pour ne pas avoir 100% de corrlation
    for d in scores:
        scores[d] += random.uniform(0, 1.5)

    # Choisir le domaine avec le meilleur score
    return max(scores, key=scores.get)


def generer_etudiant(id_etudiant):
    """Gnre un tudiant fictif avec un profil cohrent."""

    filiere   = random.choice(FILIERES)
    niveau    = random.choice(NIVEAUX)
    modules   = MODULES_PAR_FILIERE[filiere]

    # Notes dans les modules scolaires (entre 8 et 20)
    notes = {}
    for module in modules:
        notes[module] = round(random.uniform(8, 20), 1)

    # Moyenne gnrale
    moyenne = round(np.mean(list(notes.values())), 2)

    # Comptences : choisir 3  6 comptences dans diffrents domaines
    toutes_comp = [c for comps in COMPETENCES_PAR_DOMAINE.values() for c in comps]
    nb_comp = random.randint(3, 6)
    competences = random.sample(toutes_comp, nb_comp)

    # Intrts : choisir 2  4 intrts
    tous_interets = [i for ints in INTERETS_PAR_DOMAINE.values() for i in ints]
    nb_int = random.randint(2, 4)
    interets = random.sample(tous_interets, nb_int)

    # Choisir le domaine selon la logique de profil
    domaine_choisi = choisir_domaine_selon_profil(filiere, competences, interets)

    # Choisir un sujet dans ce domaine
    sujet_choisi = random.choice(SUJETS_PAR_DOMAINE[domaine_choisi])

    return {
        "id_etudiant":     f"ETU-{id_etudiant:04d}",
        "filiere":         filiere,
        "niveau":          niveau,
        "moyenne_generale": moyenne,
        # Notes aplaties en colonnes spares pour le modle
        **{f"note_{m.replace(' ', '_').lower()}": notes.get(m, np.nan) for m in
           ["Algorithmique","POO","Gnie Logiciel","BDD","Architecture","IA","Web",
            "Rseaux","TCP/IP","Scurit Rseau","Administration Linux","Tlcoms",
            "Statistiques","Python","Big Data","Visualisation",
            "lectronique","Programmation C","Microcontrleurs","FPGA","Temps Rel",
            "Cryptographie","Forensics","Pentesting","OSINT","Mobile","Cloud"]},
        "competences":     "|".join(competences),   # stock comme chane spare par |
        "interets":        "|".join(interets),
        "sujet_choisi":    sujet_choisi,
        "domaine_cible":   domaine_choisi,           #  VARIABLE CIBLE (ce que le modle prdit)
    }


#  GNRATION DES 500 TUDIANTS 

print("=" * 60)
print("GNRATION DES DONNES D'ENTRANEMENT")
print("=" * 60)

os.makedirs("/home/claude/recommandation/data", exist_ok=True)

etudiants = [generer_etudiant(i) for i in range(1, 501)]
df = pd.DataFrame(etudiants)

# Remplir les NaN (modules hors filire) par 0
df.fillna(0, inplace=True)

# Sauvegarder
chemin = "/home/claude/recommandation/data/etudiants_entrainement.csv"
df.to_csv(chemin, index=False)

#  RAPPORT DE VRIFICATION 

print(f"\n {len(df)} tudiants gnrs\n")
print("" * 40)
print("Distribution des domaines (variable cible) :")
print("" * 40)
dist = df["domaine_cible"].value_counts()
for domaine, count in dist.items():
    barre = "" * (count // 3)
    print(f"  {domaine:<30} {count:3d} tudiants  {barre}")

print("\n" * 40)
print("Distribution des filires :")
print("" * 40)
for filiere, count in df["filiere"].value_counts().items():
    print(f"  {filiere:<40} {count:3d}")

print("\n" * 40)
print("Aperu des 3 premires lignes :")
print("" * 40)
cols_apercu = ["id_etudiant","filiere","niveau","moyenne_generale","competences","interets","domaine_cible"]
print(df[cols_apercu].head(3).to_string(index=False))

print(f"\n Fichier sauvegard  {chemin}")
print(f"   Dimensions : {df.shape[0]} lignes  {df.shape[1]} colonnes")

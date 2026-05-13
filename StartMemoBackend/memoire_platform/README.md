# Plateforme Intelligente de Gestion du Parcours Mémoire – IPNET
**Backend FastAPI - Infrastructure de base (Jour 1)**

Ce dépôt contient l'architecture initiale, la base de données et les modèles SQLAlchemy pour la plateforme de gestion des mémoires de l'IPNET.

## 🚀 Pour commencer (Instructions pour l'équipe)

1. **Cloner le dépôt** et se placer dans le dossier `memoire_platform` :
   ```bash
   cd memoire_platform
   ```

2. **Créer et activer l'environnement virtuel** :
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Installer les dépendances** :
   *(Le fichier `requirements.txt` contient toutes les librairies dont vous aurez besoin pour la suite du projet : FastAPI, SQLAlchemy, Alembic, sécurité, etc.).*
   ```bash
   pip install -r requirements.txt
   ```

4. **Lancer le serveur de développement** :
   ```bash
   uvicorn app.main:app --reload
   ```
   L'API sera accessible sur [http://127.0.0.1:8000](http://127.0.0.1:8000) et la documentation Swagger sur [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## 🗄️ Base de données (Supabase)
⚠️ **Important** : Le fichier `.env` a été exceptionnellement inclus dans le dépôt pour que toute l'équipe ait accès à la base de données de développement instantanément sans configuration supplémentaire.

- **SGBD** : PostgreSQL (hébergé sur Supabase)
- **URL de connexion** : Déjà configurée dans le `.env` sous `DATABASE_URL`.
- La fonction pour injecter une session de base de données dans vos routes FastAPI est `get_db()`.
  
  **Exemple d'utilisation :**
  ```python
  from fastapi import Depends
  from sqlalchemy.orm import Session
  from app.database import get_db

  @app.get("/exemple")
  def ma_route(db: Session = Depends(get_db)):
      # db est votre session SQLAlchemy
      pass
  ```

## 🏗️ Structure des Modèles (SQLAlchemy)
Les tables sont déjà générées et synchronisées. Voici les modèles disponibles à importer depuis `app.models` :

- `User` : Utilisateurs de base (authentification, rôles).
- `Etudiant` : Profils étudiants (relié à User).
- `Encadreur` : Profils encadreurs (relié à User).
- `MembreJury` : Membres du jury (relié à User).
- `Sujet` : Sujets de mémoire proposés et statuts.
- `Memoire` : Table pivot liant un étudiant, un sujet et un encadreur.
- `VersionMemoire` : Dépôts successifs de fichiers pour un mémoire.
- `Commentaire` : Retours des encadreurs sur les versions.
- `Affectation` : Assignation officielle.
- `Soutenance` : Planification, salle, jury et notes.
- `Archive` : Catalogue public des mémoires validés.

**Exemple d'import :**
```python
from app.models import Etudiant, Memoire, User
```

## 📝 Schémas Pydantic
Des schémas de base ont été créés dans `app/schemas/` pour la validation des données d'entrée/sortie (`UserOut`, `EtudiantCreate`, etc.). N'hésitez pas à les enrichir selon les besoins de vos routes API.

---

## 🧠 Modules d'Intelligence Artificielle (Nouveau)

Le projet intègre désormais une suite de 7 modules IA pour automatiser le parcours académique. Les modèles sont chargés automatiquement au démarrage du serveur grâce au système de `lifespan`.

### État des modèles
- **4 Modèles ML Entraînés** : AntiPlagiat (82% acc), Approval (Approbation), Submission (Readiness), Archive (Clustering).
- **3 Moteurs de Logique** : Recommandation (Sémantique), Assignment (Scoring), Scheduler (Optimisation).

### Structure IA
- `ia_models/` : Centralise tous les fichiers modèles (`.pkl`) et les métadonnées de performance (`.json`).
- `app/services/ia/` : Services Python assurant l'interface entre l'API et les modèles IA.
- `scripts_ia/` : Scripts sources pour **re-générer les données ou ré-entraîner** les modèles en cas de mise à jour.

### Utilisation (API)
Toutes les fonctionnalités sont exposées via les nouvelles routes dans `app/api/v1/` :
- `POST /memoires/{id}/analyser-plagiat` : Détection de fraude sémantique.
- `POST /sujets/analyser` : Prédiction de la probabilité d'approbation d'un thème.
- `POST /soutenances/generer-planning` : Optimisation automatique des créneaux de soutenance.

---

## 📂 Dépôt & Versionnement des Mémoires (Nouveau)

Ce module gère le cycle de vie physique des documents de mémoire et assure la traçabilité des corrections.

### Fonctionnalités
- **Incrémentation de Version** : Chaque dépôt crée une nouvelle version (v1, v2...) sans écraser l'historique.
- **Stockage Sécurisé** : Les PDF sont stockés dans le dossier local `uploads/memoires/`.
- **Statuts Dynamiques** : Le système bascule automatiquement le mémoire en `en_attente` dès qu'un étudiant soumet une correction.

### 🧪 Tests Automatisés
Deux scripts ont été ajoutés pour valider l'installation et le fonctionnement :
1.  **Initialisation** : `python setup_test_db.py` (Crée un utilisateur et un étudiant de test).
2.  **Scénarios** : `python test_scenarios.py` (Exécute 5 scénarios : dépôt v1, v2, blocage non-PDF, téléchargement).

⚠️ **Important pour l'équipe** :
1.  Relancez `pip install -r requirements.txt` pour installer les librairies de Machine Learning et de Test.
2.  Le dossier `uploads/` est ignoré par Git pour ne pas encombrer le dépôt avec des fichiers de test.

---
**Bon développement à tous pour la suite du projet !**

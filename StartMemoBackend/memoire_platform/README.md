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
**Bon développement à tous pour le Jour 2 !**

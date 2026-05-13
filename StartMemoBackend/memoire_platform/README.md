# Plateforme Intelligente de Gestion du Parcours Mémoire – IPNET
**Backend FastAPI — v2.0 : Authentification, Sécurité & UUID**

Ce dépôt contient le backend FastAPI de la plateforme SmartMemo (IPNET). Il intègre désormais un système complet d'authentification JWT, une gestion des accès par rôle (RBAC), un système de réinitialisation de mot de passe par OTP et une base de données entièrement basée sur des identifiants UUID.

---

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
   ```bash
   pip install -r requirements.txt
   ```
   > ⚠️ **Important** : Assurez-vous que `bcrypt==4.0.1` est bien installé. Les versions supérieures sont incompatibles avec `passlib 1.7.4`.

4. **Configurer les variables d'environnement** :
   Le fichier `.env` contient les configurations suivantes. Mettez à jour les valeurs SMTP avec vos propres identifiants :
   ```env
   DATABASE_URL=...
   SECRET_KEY=votre_cle_secrete_tres_longue
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # Configuration SMTP (Gmail recommandé)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=votre_email@gmail.com
   SMTP_PASSWORD=votre_mot_de_passe_application  # Sans espaces !
   SMTP_FROM_EMAIL=votre_email@gmail.com
   ```
   > 💡 Pour Gmail : activez la validation en 2 étapes, puis créez un **mot de passe d'application** dans les paramètres de sécurité de votre compte Google.

5. **Lancer le serveur de développement** :
   ```bash
   uvicorn app.main:app --reload
   ```
   - API : [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - Documentation Swagger : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🔐 Authentification & Sécurité

Le système d'authentification est entièrement opérationnel et basé sur les standards industriels.

### Endpoints d'authentification (tous sous `/api/v1/auth/`)

| Méthode | Route | Accès | Description |
|---------|-------|-------|-------------|
| `POST` | `/register` | Public | Inscription d'un nouvel utilisateur |
| `POST` | `/login` | Public | Connexion et récupération du token JWT |
| `POST` | `/change-password` | 🔒 Protégé | Changer son mot de passe (token requis) |
| `POST` | `/forgot-password` | Public | Demander un code OTP par email |
| `POST` | `/reset-password` | Public | Réinitialiser le mot de passe via OTP |

### Comment utiliser le token dans Swagger

1. Appelez `POST /api/v1/auth/login` avec votre email et mot de passe.
2. Copiez la valeur `access_token` dans la réponse.
3. Cliquez sur le bouton **Authorize** (🔓) en haut de la page Swagger.
4. Collez uniquement le token (sans le mot "Bearer") et cliquez **Authorize**.

### Rôles disponibles

| Rôle | Description |
|------|-------------|
| `etudiant` | Dépose et consulte ses propres mémoires |
| `encadreur` | Consulte, valide et commente les mémoires |
| `jury` | Consulte les mémoires et leurs versions |
| `admin` | Accès complet à toutes les fonctionnalités |

---

## 🗄️ Base de données (Supabase / PostgreSQL)

- **SGBD** : PostgreSQL hébergé sur Supabase.
- **Identifiants** : Tous les enregistrements utilisent des **UUID** (format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), non prédictibles et sécurisés.
- **URL de connexion** : Configurée dans le `.env` sous `DATABASE_URL`.
- **ORM** : SQLAlchemy 2.x avec Alembic pour les migrations.

> ⚠️ **Important** : Le fichier `.env` est inclus dans le dépôt pour faciliter le travail de l'équipe. Ne le partagez pas publiquement.

**Injecter une session DB dans une route :**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db

@router.get("/exemple")
def ma_route(db: Session = Depends(get_db)):
    # db est votre session SQLAlchemy
    pass
```

---

## 🏗️ Structure des Modèles (SQLAlchemy)

Tous les modèles sont disponibles à l'import depuis `app.models` :

- `User` : Utilisateurs (auth, rôles, OTP).
- `Etudiant` : Profils étudiants (relié à User).
- `Encadreur` : Profils encadreurs (relié à User).
- `MembreJury` : Membres du jury (relié à User).
- `Sujet` : Sujets de mémoire proposés et leurs statuts.
- `Memoire` : Table pivot liant un étudiant et un encadreur.
- `VersionMemoire` : Dépôts successifs de fichiers pour un mémoire.
- `Commentaire` : Retours des encadreurs sur les versions.
- `Affectation` : Assignation officielle étudiant ↔ encadreur.
- `Soutenance` : Planification, salle, jury et notes.
- `Archive` : Catalogue public des mémoires validés.

---

## 🔒 Gestion des Accès par Rôle (RBAC)

Pour protéger une route, utilisez la dépendance `RoleChecker` :

```python
from app.api.deps import RoleChecker
from app.models.user import User
from fastapi import Depends

@router.get("/ma-route-protegee")
def ma_route(current_user: User = Depends(RoleChecker(["admin", "encadreur"]))):
    return {"message": f"Bonjour {current_user.prenom}"}
```

---

## 🧠 Modules d'Intelligence Artificielle

Le projet intègre une suite de 7 modules IA chargés automatiquement au démarrage :

- **4 Modèles ML** : AntiPlagiat, Approval (Approbation), Submission (Readiness), Archive (Clustering).
- **3 Moteurs de Logique** : Recommandation, Assignment (Scoring), Scheduler.

### Routes IA disponibles
- `POST /api/v1/memoires/{id}/analyser-plagiat` : Détection de plagiat.
- `POST /api/v1/sujets/analyser` : Probabilité d'approbation d'un sujet.
- `POST /api/v1/soutenances/generer-planning` : Optimisation des créneaux.

---

## 📂 Dépôt & Versionnement des Mémoires

- **Incrémentation automatique** : Chaque dépôt crée une nouvelle version (v1, v2...) sans écraser l'historique.
- **Stockage** : Les PDF sont stockés dans `uploads/memoires/` (ignoré par Git).
- **Statuts dynamiques** : Le mémoire passe automatiquement en `en_attente` à chaque nouveau dépôt.

---

## 📁 Structure du Projet

```
memoire_platform/
├── app/
│   ├── api/
│   │   ├── deps.py              # Dépendances (JWT, RoleChecker)
│   │   └── v1/
│   │       ├── routes_auth.py   # Authentification
│   │       ├── routes_memoire.py
│   │       ├── routes_sujet.py
│   │       └── routes_soutenance.py
│   ├── core/
│   │   ├── security.py          # Hachage, JWT, OTP
│   │   └── email.py             # Envoi d'emails SMTP
│   ├── models/                  # Modèles SQLAlchemy (UUID)
│   ├── schemas/                 # Schémas Pydantic
│   ├── services/                # Logique métier & IA
│   ├── config.py
│   ├── database.py
│   └── main.py
├── alembic/                     # Migrations de base de données
├── ia_models/                   # Fichiers modèles .pkl
├── scripts_ia/                  # Scripts d'entraînement
├── reset_db.py                  # Utilitaire de réinitialisation du schéma
├── requirements.txt
└── .env
```

---

**Bon développement à tous !** 🚀

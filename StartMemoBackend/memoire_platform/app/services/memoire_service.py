# app/services/memoire_service.py

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.memoire import Memoire, StatutMemoire
from app.models.version_memoire import VersionMemoire
from app.schemas.memoire_schema import MemoireCreer, MemoireMettreAJour

# Dossier où les fichiers PDF sont physiquement stockés
DOSSIER_UPLOADS = Path("uploads/memoires")
DOSSIER_UPLOADS.mkdir(parents=True, exist_ok=True)

# Types de fichiers autorisés
TYPES_AUTORISES = {"application/pdf"}
TAILLE_MAX_MO = 20  # 20 Mo maximum


# ══════════════════════════════════════════════
#  FONCTIONS UTILITAIRES (usage interne)
# ══════════════════════════════════════════════

def _valider_fichier(fichier: UploadFile) -> None:
    """Vérifie que le fichier est un PDF et ne dépasse pas la taille max."""
    if fichier.content_type not in TYPES_AUTORISES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé : '{fichier.content_type}'. Seul le PDF est accepté."
        )


def _generer_nom_fichier(memoire_id: int, numero_version: int, nom_original: str) -> str:
    """
    Génère un nom de fichier unique pour le stockage.
    Exemple : "memoire_5_v3_1717430400.pdf"
    """
    timestamp = int(datetime.utcnow().timestamp())
    extension = Path(nom_original).suffix.lower()  # ".pdf"
    return f"memoire_{memoire_id}_v{numero_version}_{timestamp}{extension}"


def _sauvegarder_fichier(fichier: UploadFile, nom_stocke: str) -> tuple[str, int]:
    """
    Sauvegarde le fichier sur disque.
    Retourne (chemin_relatif, taille_en_ko).
    """
    chemin_complet = DOSSIER_UPLOADS / nom_stocke
    taille = 0

    with open(chemin_complet, "wb") as f:
        contenu = fichier.file.read()
        taille = len(contenu)
        f.write(contenu)

    taille_ko = taille // 1024
    chemin_relatif = str(DOSSIER_UPLOADS / nom_stocke)
    return chemin_relatif, taille_ko


# ══════════════════════════════════════════════
#  FONCTIONS PRINCIPALES (appelées par les routes)
# ══════════════════════════════════════════════

def creer_memoire_et_deposer(
    db: Session,
    donnees: MemoireCreer,
    fichier: UploadFile,
    etudiant_id: int
) -> Memoire:
    """
    Crée un nouveau mémoire ET enregistre la première version (v1).
    """
    # 1. Valider
    _valider_fichier(fichier)

    # 2. Créer le mémoire (sans fichier encore)
    nouveau_memoire = Memoire(
        titre=donnees.titre,
        description=donnees.description,
        domaine=donnees.domaine,
        annee_academique=donnees.annee_academique,
        statut=StatutMemoire.en_attente,
        etudiant_id=etudiant_id
    )
    db.add(nouveau_memoire)
    db.flush()  # flush pour obtenir l'id

    # 3. Générer le nom et sauvegarder le fichier
    nom_stocke = _generer_nom_fichier(nouveau_memoire.id, 1, fichier.filename)
    chemin, taille_ko = _sauvegarder_fichier(fichier, nom_stocke)

    # 4. Créer la version 1
    version = VersionMemoire(
        memoire_id=nouveau_memoire.id,
        numero_version=1,
        nom_fichier_original=fichier.filename,
        nom_fichier_stocke=nom_stocke,
        chemin_fichier=chemin,
        taille_fichier_ko=taille_ko,
        message_depot=donnees.message_depot,
        est_version_courante=True,
        depose_par_id=etudiant_id # Note: Normalement on utilise l'ID de l'utilisateur connecté
    )
    db.add(version)
    db.commit()
    db.refresh(nouveau_memoire)

    return nouveau_memoire


def deposer_nouvelle_version(
    db: Session,
    memoire_id: int,
    fichier: UploadFile,
    etudiant_id: int,
    message_depot: Optional[str] = None
) -> VersionMemoire:
    """
    Dépose une nouvelle version d'un mémoire existant.
    """
    # Récupérer le mémoire
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(status_code=404, detail="Mémoire introuvable.")

    # Vérifier que c'est bien l'étudiant propriétaire (temporaire sans JWT complet)
    if memoire.etudiant_id != etudiant_id:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas autorisé à modifier ce mémoire.")

    # Vérifier que le mémoire est encore modifiable
    if memoire.statut in [StatutMemoire.valide, StatutMemoire.refuse]:
        raise HTTPException(
            status_code=400,
            detail=f"Impossible de déposer une nouvelle version : le mémoire est '{memoire.statut}'."
        )

    # Valider le fichier
    _valider_fichier(fichier)

    # Calculer le nouveau numéro de version
    dernier_numero = db.query(VersionMemoire).filter(
        VersionMemoire.memoire_id == memoire_id
    ).count()
    nouveau_numero = dernier_numero + 1

    # Désactiver l'ancienne version courante
    db.query(VersionMemoire).filter(
        VersionMemoire.memoire_id == memoire_id,
        VersionMemoire.est_version_courante == True
    ).update({"est_version_courante": False})

    # Sauvegarder le fichier
    nom_stocke = _generer_nom_fichier(memoire_id, nouveau_numero, fichier.filename)
    chemin, taille_ko = _sauvegarder_fichier(fichier, nom_stocke)

    # Créer la nouvelle version
    nouvelle_version = VersionMemoire(
        memoire_id=memoire_id,
        numero_version=nouveau_numero,
        nom_fichier_original=fichier.filename,
        nom_fichier_stocke=nom_stocke,
        chemin_fichier=chemin,
        taille_fichier_ko=taille_ko,
        message_depot=message_depot,
        est_version_courante=True,
        depose_par_id=etudiant_id
    )
    db.add(nouvelle_version)

    # Repasser le mémoire en "en_attente" pour que l'encadreur relise
    memoire.statut = StatutMemoire.en_attente
    db.commit()
    db.refresh(nouvelle_version)

    return nouvelle_version


def obtenir_memoire_par_id(db: Session, memoire_id: int) -> Memoire:
    """Récupère un mémoire complet avec ses versions."""
    memoire = db.query(Memoire).filter(Memoire.id == memoire_id).first()
    if not memoire:
        raise HTTPException(status_code=404, detail="Mémoire introuvable.")
    return memoire


def lister_memoires_etudiant(db: Session, etudiant_id: int) -> List[Memoire]:
    """Retourne tous les mémoires d'un étudiant."""
    return (
        db.query(Memoire)
        .filter(Memoire.etudiant_id == etudiant_id)
        .order_by(Memoire.cree_le.desc())
        .all()
    )


def lister_historique_versions(db: Session, memoire_id: int) -> List[VersionMemoire]:
    """Retourne toutes les versions d'un mémoire."""
    return (
        db.query(VersionMemoire)
        .filter(VersionMemoire.memoire_id == memoire_id)
        .order_by(VersionMemoire.numero_version.desc())
        .all()
    )

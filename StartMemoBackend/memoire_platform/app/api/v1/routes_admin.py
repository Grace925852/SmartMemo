import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import RoleChecker
from app.models.user import User
from app.models.memoire import Memoire, StatutMemoire
from app.models.sujet import Sujet, StatutSujet
from app.models.encadreur import Encadreur
from app.models.soutenance import Soutenance, StatutSoutenance
from app.models.version_memoire import VersionMemoire

router = APIRouter(prefix="/admin", tags=["Administrateur"])

require_admin = RoleChecker(["admin"])


# ──────────────────────────────────────────────────────────────
#  SCHÉMAS PYDANTIC
# ──────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    totalMemoires: int
    enCours: int
    valides: int
    plagiatPotentiel: int
    encadreursDispo: int
    soutenancesPlannifiees: int
    tauxReussite: int


class EtudiantInfo(BaseModel):
    nom: str
    prenom: str


class SujetPendingResponse(BaseModel):
    id: uuid.UUID
    etudiant: EtudiantInfo
    titre: str
    dateProposition: Optional[str]
    scoreIA: Optional[float]
    scoreSimilarite: Optional[float]
    scoreCoherence: Optional[float]
    scoreFaisabilite: Optional[float]
    statut: str
    motsCles: List[str]


class EnseignantResponse(BaseModel):
    id: uuid.UUID
    nom: str
    prenom: str
    titre: str
    specialite: str
    charge: int
    maxCharge: int
    disponible: bool


class SoutenanceAdminResponse(BaseModel):
    id: uuid.UUID
    etudiant: str
    titre: str
    date: Optional[str]
    heure: Optional[str]
    salle: Optional[str]
    jury: List[str]
    statut: str


class ActiviteResponse(BaseModel):
    id: str
    type: str
    message: str
    temps: str
    icon: str


class ValiderSujetRequest(BaseModel):
    commentaire: Optional[str] = None


class RejeterSujetRequest(BaseModel):
    motif: str


class ValiderSujetResponse(BaseModel):
    sujet_id: uuid.UUID
    statut: str
    message: str


class RejeterSujetResponse(BaseModel):
    sujet_id: uuid.UUID
    statut: str
    motif: str
    message: str


# ──────────────────────────────────────────────────────────────
#  UTILITAIRES
# ──────────────────────────────────────────────────────────────

def _format_temps(dt: Optional[datetime]) -> str:
    if not dt:
        return "date inconnue"
    now = datetime.utcnow()
    # Normalise les datetimes timezone-aware en naive UTC
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    delta = now - dt
    total_sec = int(delta.total_seconds())
    if total_sec < 0:
        return "à l'instant"
    if total_sec < 60:
        return "à l'instant"
    if total_sec < 3600:
        m = total_sec // 60
        return f"il y a {m} minute{'s' if m > 1 else ''}"
    if total_sec < 86400:
        h = total_sec // 3600
        return f"il y a {h} heure{'s' if h > 1 else ''}"
    if delta.days == 1:
        return "hier"
    return f"il y a {delta.days} jours"


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ──────────────────────────────────────────────────────────────
#  GET /admin/stats
# ──────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Statistiques agrégées de la plateforme pour le tableau de bord admin."""
    total = db.query(func.count(Memoire.id)).scalar() or 0

    en_cours = db.query(func.count(Memoire.id)).filter(
        Memoire.statut.in_([StatutMemoire.en_attente, StatutMemoire.en_correction])
    ).scalar() or 0

    valides = db.query(func.count(Memoire.id)).filter(
        Memoire.statut == StatutMemoire.valide
    ).scalar() or 0

    # Proxy : sujets avec un score de similarité élevé (> 75 %)
    plagiat = db.query(func.count(Sujet.id)).filter(
        Sujet.score_similarite.isnot(None),
        Sujet.score_similarite > 0.75
    ).scalar() or 0

    encadreurs_dispo = db.query(func.count(Encadreur.id)).filter(
        Encadreur.disponible == True
    ).scalar() or 0

    soutenances_planif = db.query(func.count(Soutenance.id)).filter(
        Soutenance.statut == StatutSoutenance.planifiee
    ).scalar() or 0

    taux = int(valides / total * 100) if total > 0 else 0

    return StatsResponse(
        totalMemoires=total,
        enCours=en_cours,
        valides=valides,
        plagiatPotentiel=plagiat,
        encadreursDispo=encadreurs_dispo,
        soutenancesPlannifiees=soutenances_planif,
        tauxReussite=taux
    )


# ──────────────────────────────────────────────────────────────
#  GET /admin/sujets/pending
# ──────────────────────────────────────────────────────────────

@router.get("/sujets/pending", response_model=List[SujetPendingResponse])
def get_sujets_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Sujets en attente de validation (propose ou en_evaluation) avec scores IA."""
    sujets = (
        db.query(Sujet)
        .filter(Sujet.statut.in_([StatutSujet.propose, StatutSujet.en_evaluation]))
        .order_by(Sujet.created_at.asc())
        .all()
    )

    result = []
    for sujet in sujets:
        etudiant = sujet.etudiant
        user = etudiant.user if etudiant else None

        score_ia = (
            round(sujet.score_faisabilite * 100, 1)
            if sujet.score_faisabilite is not None else None
        )
        score_sim = (
            round(sujet.score_similarite * 100, 1)
            if sujet.score_similarite is not None else None
        )
        score_fais = (
            round(sujet.score_faisabilite * 100, 1)
            if sujet.score_faisabilite is not None else None
        )

        result.append(SujetPendingResponse(
            id=sujet.id,
            etudiant=EtudiantInfo(
                nom=user.nom if user else "",
                prenom=user.prenom if user else ""
            ),
            titre=sujet.titre,
            dateProposition=(
                sujet.created_at.strftime("%Y-%m-%d")
                if sujet.created_at else None
            ),
            scoreIA=score_ia,
            scoreSimilarite=score_sim,
            scoreCoherence=None,
            scoreFaisabilite=score_fais,
            statut=sujet.statut.value,
            motsCles=[]
        ))

    return result


# ──────────────────────────────────────────────────────────────
#  GET /admin/enseignants
# ──────────────────────────────────────────────────────────────

@router.get("/enseignants", response_model=List[EnseignantResponse])
def get_enseignants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste des encadreurs avec leur charge de travail calculée dynamiquement."""
    encadreurs = db.query(Encadreur).all()

    result = []
    for enc in encadreurs:
        user = enc.user
        if not user:
            continue

        # Charge dynamique : mémoires actifs assignés à cet encadreur
        charge = db.query(func.count(Memoire.id)).filter(
            Memoire.encadreur_id == user.id,
            Memoire.statut.notin_([StatutMemoire.valide, StatutMemoire.refuse])
        ).scalar() or 0

        max_charge = _safe_int(enc.max_etudiants, default=5)
        disponible = charge < max_charge

        specialites_raw = enc.specialites or ""
        specialite_principale = (
            specialites_raw.split(",")[0].strip() if specialites_raw else ""
        )

        result.append(EnseignantResponse(
            id=enc.id,
            nom=user.nom or "",
            prenom=user.prenom or "",
            titre=enc.grade or "",
            specialite=specialite_principale,
            charge=charge,
            maxCharge=max_charge,
            disponible=disponible
        ))

    # Disponibles en premier, puis ordre alphabétique
    result.sort(key=lambda x: (not x.disponible, x.nom))
    return result


# ──────────────────────────────────────────────────────────────
#  GET /admin/soutenances
# ──────────────────────────────────────────────────────────────

@router.get("/soutenances", response_model=List[SoutenanceAdminResponse])
def get_soutenances(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Liste de toutes les soutenances avec jury et étudiant associés."""
    soutenances = (
        db.query(Soutenance)
        .order_by(Soutenance.date_soutenance.asc())
        .all()
    )

    result = []
    for s in soutenances:
        memoire = s.memoire
        if not memoire:
            continue

        etudiant = memoire.etudiant
        etudiant_user = etudiant.user if etudiant else None
        etudiant_nom = (
            f"{etudiant_user.prenom} {etudiant_user.nom.upper()}"
            if etudiant_user else ""
        )

        date_str = (
            s.date_soutenance.strftime("%Y-%m-%d") if s.date_soutenance else None
        )
        heure_str = (
            s.date_soutenance.strftime("%H:%M") if s.date_soutenance else None
        )

        jury_noms: List[str] = []
        if s.president_jury and s.president_jury.user:
            pj = s.president_jury.user
            jury_noms.append(f"{pj.prenom} {pj.nom}")
        if s.examinateur and s.examinateur.user:
            ex = s.examinateur.user
            jury_noms.append(f"{ex.prenom} {ex.nom}")

        result.append(SoutenanceAdminResponse(
            id=s.id,
            etudiant=etudiant_nom,
            titre=memoire.titre,
            date=date_str,
            heure=heure_str,
            salle=s.salle,
            jury=jury_noms,
            statut=s.statut.value
        ))

    return result


# ──────────────────────────────────────────────────────────────
#  GET /admin/activite
# ──────────────────────────────────────────────────────────────

@router.get("/activite", response_model=List[ActiviteResponse])
def get_activite(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Fil d'activité récente agrégé depuis dépôts, sujets et soutenances."""
    activites: List[Dict[str, Any]] = []

    # Derniers dépôts de versions
    versions = (
        db.query(VersionMemoire)
        .order_by(VersionMemoire.depose_le.desc())
        .limit(10)
        .all()
    )
    for v in versions:
        memoire = v.memoire
        titre = memoire.titre if memoire else "Mémoire inconnu"
        activites.append({
            "id": str(v.id),
            "type": "depot",
            "message": f"Nouveau dépôt : {titre} (v{v.numero_version})",
            "ts": v.depose_le,
            "icon": "file-upload"
        })

    # Sujets récemment traités (validés ou refusés)
    sujets = (
        db.query(Sujet)
        .filter(Sujet.statut.in_([StatutSujet.valide, StatutSujet.rejete]))
        .order_by(Sujet.updated_at.desc())
        .limit(5)
        .all()
    )
    for sujet in sujets:
        est_valide = sujet.statut == StatutSujet.valide
        activites.append({
            "id": str(sujet.id) + "-statut",
            "type": "statut",
            "message": f"Sujet {'validé' if est_valide else 'refusé'} : {sujet.titre[:60]}",
            "ts": sujet.updated_at,
            "icon": "check-circle" if est_valide else "alert-triangle"
        })

    # Nouvelles soutenances planifiées
    soutenances = (
        db.query(Soutenance)
        .order_by(Soutenance.created_at.desc())
        .limit(5)
        .all()
    )
    for s in soutenances:
        memoire = s.memoire
        titre = memoire.titre if memoire else "Soutenance"
        activites.append({
            "id": str(s.id) + "-soutenance",
            "type": "soutenance",
            "message": f"Soutenance planifiée : {titre}",
            "ts": s.created_at,
            "icon": "calendar"
        })

    def _to_naive(dt: Optional[datetime]) -> datetime:
        if dt is None:
            return datetime.min
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    activites.sort(key=lambda x: _to_naive(x["ts"]), reverse=True)

    return [
        ActiviteResponse(
            id=a["id"],
            type=a["type"],
            message=a["message"],
            temps=_format_temps(a["ts"]),
            icon=a["icon"]
        )
        for a in activites[:20]
    ]


# ──────────────────────────────────────────────────────────────
#  POST /admin/sujets/{id}/valider
# ──────────────────────────────────────────────────────────────

@router.post("/sujets/{sujet_id}/valider", response_model=ValiderSujetResponse)
def valider_sujet(
    sujet_id: uuid.UUID,
    body: ValiderSujetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Valider un sujet de mémoire proposé par un étudiant."""
    sujet = db.query(Sujet).filter(Sujet.id == sujet_id).first()
    if not sujet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sujet introuvable"
        )

    if sujet.statut in [StatutSujet.valide, StatutSujet.rejete]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce sujet a déjà été traité (validé ou refusé)"
        )

    sujet.statut = StatutSujet.valide
    sujet.commentaire_validation = body.commentaire
    sujet.valide_par = current_user.id
    db.commit()

    return ValiderSujetResponse(
        sujet_id=sujet.id,
        statut="valide",
        message="Sujet validé avec succès."
    )


# ──────────────────────────────────────────────────────────────
#  POST /admin/sujets/{id}/rejeter
# ──────────────────────────────────────────────────────────────

@router.post("/sujets/{sujet_id}/rejeter", response_model=RejeterSujetResponse)
def rejeter_sujet(
    sujet_id: uuid.UUID,
    body: RejeterSujetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Rejeter un sujet de mémoire avec un motif obligatoire."""
    if not body.motif or not body.motif.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le champ 'motif' est obligatoire et ne peut pas être vide"
        )

    sujet = db.query(Sujet).filter(Sujet.id == sujet_id).first()
    if not sujet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sujet introuvable"
        )

    if sujet.statut in [StatutSujet.valide, StatutSujet.rejete]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce sujet a déjà été traité (validé ou refusé)"
        )

    sujet.statut = StatutSujet.rejete
    sujet.commentaire_validation = body.motif
    db.commit()

    return RejeterSujetResponse(
        sujet_id=sujet.id,
        statut="rejete",
        motif=body.motif,
        message="Sujet refusé."
    )

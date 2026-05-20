from datetime import date, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import RoleChecker
from app.models.etudiant import Etudiant
from app.models.memoire import Memoire, StatutMemoire
from app.models.version_memoire import VersionMemoire
from app.models.user import User
from app.models.encadreur import Encadreur

router = APIRouter(prefix="/etudiant", tags=["Étudiant"])

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

ETAPES_DEFINITION = [
    {"id": "sujet",          "label": "Sujet validé"},
    {"id": "depot_initial",  "label": "Dépôt initial"},
    {"id": "redaction",      "label": "Rédaction"},
    {"id": "correction",     "label": "Corrections"},
    {"id": "validation",     "label": "Validation encadreur"},
    {"id": "soutenance",     "label": "Soutenance"},
]


def _calculer_etapes(memoire: Memoire) -> tuple[list[dict], str, int]:
    """Retourne (etapes, etapeActuelle, progression)."""
    nb_versions = len(memoire.versions)
    statut = memoire.statut

    if nb_versions == 0:
        etapes = [
            {**e, "statut": "a_venir", "date": None}
            for e in ETAPES_DEFINITION
        ]
        return etapes, "depot_initial", 0

    # Détermination des statuts par étape
    statuts_map = {
        "sujet":         "valide",
        "depot_initial": "valide",
        "redaction":     "valide" if nb_versions > 1 else ("en_cours" if statut == StatutMemoire.en_attente else "valide"),
        "correction":    "valide" if statut == StatutMemoire.valide else ("en_cours" if statut == StatutMemoire.en_correction else "a_venir"),
        "validation":    "valide" if statut == StatutMemoire.valide else "a_venir",
        "soutenance":    "a_venir",
    }

    premiere_version = memoire.versions[-1] if memoire.versions else None
    dates_map: dict[str, Optional[date]] = {
        "sujet":         premiere_version.depose_le.date() if premiere_version else None,
        "depot_initial": premiere_version.depose_le.date() if premiere_version else None,
        "redaction":     None,
        "correction":    None,
        "validation":    memoire.mis_a_jour_le.date() if statut == StatutMemoire.valide and memoire.mis_a_jour_le else None,
        "soutenance":    None,
    }

    etapes = [
        {
            **e,
            "statut": statuts_map[e["id"]],
            "date":   str(dates_map[e["id"]]) if dates_map[e["id"]] else None,
        }
        for e in ETAPES_DEFINITION
    ]

    etape_actuelle_map = {
        StatutMemoire.en_attente:    "redaction",
        StatutMemoire.en_correction: "correction",
        StatutMemoire.valide:        "soutenance",
        StatutMemoire.refuse:        "correction",
    }
    etape_actuelle = etape_actuelle_map.get(statut, "redaction")

    progression_map = {
        StatutMemoire.en_attente:    25,
        StatutMemoire.en_correction: 50,
        StatutMemoire.valide:        100,
        StatutMemoire.refuse:        10,
    }
    progression = progression_map.get(statut, 25)

    return etapes, etape_actuelle, progression


def _prochaine_echeance(memoire: Memoire) -> tuple[Optional[str], Optional[str]]:
    """Retourne (date ISO, label) de la prochaine échéance estimée."""
    if not memoire.versions:
        return None, None

    premiere = memoire.versions[-1].depose_le
    if memoire.statut == StatutMemoire.en_correction:
        d = premiere.date() + timedelta(days=30)
        return str(d), "Dépôt version corrigée"
    if memoire.statut == StatutMemoire.en_attente:
        d = premiere.date() + timedelta(days=14)
        return str(d), "Retour encadreur attendu"
    return None, None


# ──────────────────────────────────────────────
# GET /etudiant/memoire/me
# ──────────────────────────────────────────────

@router.get(
    "/memoire/me",
    summary="Mon mémoire (tableau de bord étudiant)",
    description="Retourne le mémoire de l'étudiant connecté avec progression, étapes et encadreur.",
)
def get_mon_memoire(
    current_user: User = Depends(RoleChecker(["etudiant"])),
    db: Session = Depends(get_db),
) -> Any:
    etudiant = db.query(Etudiant).filter(Etudiant.user_id == current_user.id).first()
    if not etudiant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil étudiant introuvable.")
    memoire = (
        db.query(Memoire)
        .filter(Memoire.etudiant_id == etudiant.id)
        .order_by(Memoire.cree_le.desc())
        .first()
    )
    if not memoire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun mémoire trouvé pour cet étudiant.")

    etapes, etape_actuelle, progression = _calculer_etapes(memoire)
    prochaine_date, prochaine_label = _prochaine_echeance(memoire)

    encadreur_data = None
    if memoire.encadreur_id:
        enc_user = db.query(User).filter(User.id == memoire.encadreur_id).first()
        enc_profile = db.query(Encadreur).filter(Encadreur.user_id == memoire.encadreur_id).first()
        if enc_user:
            encadreur_data = {
                "id":         enc_user.id,
                "nom":        enc_user.nom,
                "prenom":     enc_user.prenom,
                "titre":      enc_profile.grade if enc_profile else "Dr.",
                "specialite": enc_profile.specialites if enc_profile else "",
            }

    return {
        "id":                    memoire.id,
        "titre":                 memoire.titre,
        "statut":                memoire.statut.value,
        "progression":           progression,
        "etapeActuelle":         etape_actuelle,
        "etapes":                etapes,
        "encadreur":             encadreur_data,
        "prochaineEcheance":     prochaine_date,
        "prochaineEcheanceLabel": prochaine_label,
    }


# ──────────────────────────────────────────────
# GET /etudiant/memoire/jalons
# ──────────────────────────────────────────────

@router.get(
    "/memoire/jalons",
    summary="Jalons du mémoire de l'étudiant connecté",
    description="Retourne la chronologie des jalons avec leur statut (done / in_progress / upcoming).",
)
def get_jalons(
    current_user: User = Depends(RoleChecker(["etudiant"])),
    db: Session = Depends(get_db),
) -> Any:
    etudiant = db.query(Etudiant).filter(Etudiant.user_id == current_user.id).first()
    if not etudiant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil étudiant introuvable.")
    memoire = (
        db.query(Memoire)
        .filter(Memoire.etudiant_id == etudiant.id)
        .order_by(Memoire.cree_le.desc())
        .first()
    )
    if not memoire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun mémoire trouvé.")

    nb_versions = len(memoire.versions)
    statut = memoire.statut
    premiere = memoire.versions[-1] if memoire.versions else None

    STATUT_MAP = {"valide": "done", "en_cours": "in_progress", "a_venir": "upcoming"}

    raw_statuts = {
        "sujet":         "done" if nb_versions > 0 else "upcoming",
        "depot_initial": "done" if nb_versions > 0 else "in_progress",
        "redaction":     "done" if nb_versions > 1 else ("in_progress" if nb_versions == 1 and statut == StatutMemoire.en_attente else "upcoming"),
        "correction":    "done" if statut == StatutMemoire.valide else ("in_progress" if statut == StatutMemoire.en_correction else "upcoming"),
        "validation":    "done" if statut == StatutMemoire.valide else "upcoming",
        "soutenance":    "upcoming",
    }

    jalons = []
    for idx, etape in enumerate(ETAPES_DEFINITION):
        etape_statut = raw_statuts[etape["id"]]
        # Derive a date: use version deposit date for early milestones
        if etape["id"] in ("sujet", "depot_initial") and premiere:
            date_val = str(premiere.depose_le.date())
        elif etape["id"] == "correction" and statut == StatutMemoire.en_correction and memoire.mis_a_jour_le:
            date_val = str(memoire.mis_a_jour_le.date())
        elif etape["id"] == "validation" and statut == StatutMemoire.valide and memoire.mis_a_jour_le:
            date_val = str(memoire.mis_a_jour_le.date())
        else:
            date_val = None

        jalons.append({
            "id":     f"jalon_{idx + 1}",
            "label":  etape["label"],
            "date":   date_val,
            "statut": etape_statut,
        })

    return jalons


# ──────────────────────────────────────────────
# GET /etudiant/suggestions
# ──────────────────────────────────────────────

class SuggestionOut(BaseModel):
    titre: str
    description: str
    pertinence: float
    domaine: str
    difficulte: str
    dureeEstimee: str
    motsCles: list[str]


@router.get(
    "/suggestions",
    response_model=list[SuggestionOut],
    summary="Suggestions de sujets IA pour l'étudiant connecté",
    description="Génère 5 suggestions de sujets via le service IA de recommandation.",
)
def get_suggestions(
    current_user: User = Depends(RoleChecker(["etudiant"])),
    db: Session = Depends(get_db),
) -> list[SuggestionOut]:
    from app.services.ia.recommandation_service import suggerer_sujets

    etudiant = db.query(Etudiant).filter(Etudiant.user_id == current_user.id).first()
    if not etudiant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil étudiant introuvable.")
    domaine = etudiant.centres_interet or etudiant.filiere or "Informatique"
    mots_cles = [k.strip() for k in (etudiant.competences or "").split(",") if k.strip()]
    niveau = etudiant.niveau or "Master"

    resultat = suggerer_sujets(domaine=domaine, mots_cles=mots_cles, niveau=niveau, top_n=5)
    suggestions_brutes = resultat.get("suggestions", [])

    # Map service output → frontend schema
    suggestions: list[SuggestionOut] = []
    for s in suggestions_brutes:
        suggestions.append(
            SuggestionOut(
                titre=s.get("titre", ""),
                description=f"Sujet issu de la base de données pour le domaine {s.get('domaine', domaine)}.",
                pertinence=s.get("score_pertinence", 0.0),
                domaine=s.get("domaine", domaine),
                difficulte="Intermédiaire",
                dureeEstimee="6 mois",
                motsCles=mots_cles[:3] if mots_cles else [domaine],
            )
        )

    # Fallback si le service IA n'a pas de données
    if not suggestions:
        suggestions = [
            SuggestionOut(
                titre=f"Sujet proposé en {domaine} ({i + 1})",
                description=f"Proposition générée automatiquement pour le niveau {niveau} en {domaine}.",
                pertinence=round(80 - i * 5, 1),
                domaine=domaine,
                difficulte="Intermédiaire",
                dureeEstimee="6 mois",
                motsCles=mots_cles[:3] if mots_cles else [domaine],
            )
            for i in range(5)
        ]

    return suggestions

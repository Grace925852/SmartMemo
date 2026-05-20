from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/integration", tags=["Intégration frontend - ATTA"])


@router.get("/frontend-map")
def frontend_map():
    """Résumé des routes utiles pour connecter le frontend déjà réalisé."""
    return {
        "base_url": "http://127.0.0.1:8000",
        "module": "Dépôt mémoire, commentaires et validation",
        "routes": {
            "creer_memoire": "POST /api/v1/memoires",
            "lister_memoires": "GET /api/v1/memoires",
            "detail_memoire": "GET /api/v1/memoires/{memoire_id}",
            "changer_statut_memoire": "PUT /api/v1/memoires/{memoire_id}/statut",
            "deposer_version": "POST /api/v1/memoires/{memoire_id}/versions/upload",
            "historique_versions": "GET /api/v1/memoires/{memoire_id}/versions",
            "changer_statut_version": "PUT /api/v1/memoires/versions/{version_id}/statut",
            "ajouter_commentaire": "POST /api/v1/commentaires",
            "commentaires_version": "GET /api/v1/commentaires/version/{version_id}",
            "commentaires_memoire": "GET /api/v1/commentaires/memoire/{memoire_id}",
        },
        "statuts_memoire": ["en_cours", "en_attente", "en_correction", "valide", "refuse", "soutenu"],
        "statuts_version": ["en_attente", "en_correction", "valide", "refuse"],
    }

from datetime import datetime, timedelta
from typing import Optional

def planifier_soutenances(
    etudiants: list[dict],
    salles_disponibles: list[str],
    professeurs_disponibles: list[dict],
    date_debut: datetime,
    duree_soutenance_minutes: int = 45
) -> dict:
    """
    Algorithme Greedy pour planifier les soutenances sans conflits.
    """
    planning = []
    conflits = []
    
    # Table de disponibilité
    occupation_profs = {p["id"]: [] for p in professeurs_disponibles}
    occupation_salles = {salle: [] for salle in salles_disponibles}
    
    delta = timedelta(minutes=duree_soutenance_minutes + 15) # +15min de pause
    heure_courante = date_debut
    
    # On trie les étudiants par nombre de membres du jury (les plus contraints d'abord)
    etudiants_tries = sorted(etudiants, key=lambda x: len(x.get("jury_ids", [])), reverse=True)
    
    for etudiant in etudiants_tries:
        creneau_trouve = False
        
        # On cherche sur 5 jours max (8h par jour)
        for jour in range(5):
            base_time = date_debut.replace(hour=8, minute=0, second=0) + timedelta(days=jour)
            for slot in range(10): # 10 créneaux par jour
                test_start = base_time + timedelta(minutes=slot * (duree_soutenance_minutes + 15))
                test_end = test_start + timedelta(minutes=duree_soutenance_minutes)
                
                # Vérifier jury
                jury_ids = etudiant.get("jury_ids", [])
                jury_disponible = True
                for jid in jury_ids:
                    # Vérifier si déjà occupé sur ce créneau
                    for occ in occupation_profs.get(jid, []):
                        if (test_start < occ['end'] and test_end > occ['start']):
                            jury_disponible = False
                            break
                    if not jury_disponible: break
                
                if not jury_disponible: continue
                
                # Vérifier salle
                salle_choisie = None
                for salle in salles_disponibles:
                    salle_libre = True
                    for occ in occupation_salles[salle]:
                        if (test_start < occ['end'] and test_end > occ['start']):
                            salle_libre = False
                            break
                    if salle_libre:
                        salle_choisie = salle
                        break
                
                if jury_disponible and salle_choisie:
                    # Bloquer le créneau
                    for jid in jury_ids:
                        occupation_profs[jid].append({'start': test_start, 'end': test_end})
                    occupation_salles[salle_choisie].append({'start': test_start, 'end': test_end})
                    
                    planning.append({
                        "etudiant_id": etudiant["id"],
                        "etudiant_nom": etudiant.get("nom", "Inconnu"),
                        "debut": test_start.isoformat(),
                        "fin": test_end.isoformat(),
                        "salle": salle_choisie,
                        "jury": jury_ids
                    })
                    creneau_trouve = True
                    break
            if creneau_trouve: break
            
        if not creneau_trouve:
            conflits.append({
                "etudiant_id": etudiant["id"],
                "raison": "Aucun créneau compatible trouvé pour le jury"
            })
    
    total = len(etudiants)
    taux = round((len(planning) / total * 100), 1) if total > 0 else 0
    
    return {
        "planning": planning,
        "taux_planification": taux,
        "nb_planifies": len(planning),
        "nb_conflits": len(conflits),
        "conflits_detectes": conflits
    }

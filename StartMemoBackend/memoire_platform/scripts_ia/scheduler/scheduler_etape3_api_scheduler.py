"""
=============================================================
MODULE DEFENCE SCHEDULER
TAPE 3  API FASTAPI + REPLANIFICATION + CALENDRIER
=============================================================

FONCTIONNALITS DE L'API :
----------------------------
  POST /planifier               Lance la planification complte
  GET  /planning                Retourne le planning actuel
  GET  /planning/calendrier     Vue calendrier (jour par jour)
  POST /replanifier/{id}        Replanifie 1 tudiant (annulation/report)
  GET  /disponibilites/{prof}   Crneaux libres d'un professeur
  GET  /conflits                Liste des conflits dtects
  GET  /statistiques            Tableau de bord du planning

SCNARIO DE REPLANIFICATION :
-------------------------------
Un professeur tombe malade la veille  l'admin dclenche
une replanification  le systme trouve automatiquement
un nouveau crneau valide pour l'tudiant concern.

PORT : 8006
"""

import pandas as pd
import numpy as np
import json
from collections import defaultdict
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

#  CHARGEMENT 

df_creneaux    = pd.read_csv("data/creneaux.csv")
df_salles      = pd.read_csv("data/salles.csv")
df_professeurs = pd.read_csv("data/professeurs.csv")
df_etudiants   = pd.read_csv("data/etudiants.csv")

with open("modeles/meta_modele.json", encoding="utf-8") as f:
    meta = json.load(f)

CRENEAUX  = df_creneaux.to_dict("records")
SALLES    = df_salles.to_dict("records")
PROFS     = {p["id_prof"]: p for p in df_professeurs.to_dict("records")}
ETUDIANTS = df_etudiants.to_dict("records")
ETUDIANTS_MAP = {e["id_etudiant"]: e for e in ETUDIANTS}


def parse_indispos(chaine) -> set:
    if pd.isna(chaine) or str(chaine).strip() == "":
        return set()
    return set(str(chaine).split("|"))


def get_jury_ids(etudiant: dict) -> list:
    return [etudiant["directeur_id"],
            etudiant["examinateur_id"],
            etudiant["jury3_id"]]


#  TAT GLOBAL DU PLANNING 

class EtatPlanning:
    """Maintient l'tat courant du planning en mmoire."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.planning       = []                # liste des assignations confirmes
        self.salle_creneau  = {}                # (salle_id, creneau_id)  etudiant_id
        self.prof_creneau   = defaultdict(list) # (prof_id, creneau_id)  [etudiant_ids]
        self.prof_jour      = defaultdict(int)  # (prof_id, index_jour)  nb_jurys

    def peut_assigner(self, etudiant, salle, creneau) -> tuple:
        id_s = salle["id_salle"]
        id_c = creneau["id_creneau"]
        id_j = creneau["index_jour"]

        if not etudiant["paiement_valide"]:
            return False, "Paiement non valid"
        if not etudiant["pre_soutenance_ok"]:
            return False, "Pr-soutenance non valide"
        if self.salle_creneau.get((id_s, id_c)):
            return False, f"Salle {salle['nom']} occupe"
        if id_c in parse_indispos(salle.get("creneaux_indispos","")):
            return False, f"Salle {salle['nom']} indisponible"
        if id_c in parse_indispos(etudiant.get("creneaux_indispos","")):
            return False, "tudiant indisponible"

        for prof_id in get_jury_ids(etudiant):
            prof = PROFS.get(prof_id, {})
            if id_c in parse_indispos(prof.get("creneaux_indispos","")):
                return False, f"{prof.get('nom','Prof')} indisponible"
            if self.prof_creneau.get((prof_id, id_c)):
                return False, f"{prof.get('nom','Prof')} dj planifi"
            max_j = prof.get("max_jurys_par_jour", 2)
            if self.prof_jour.get((prof_id, id_j), 0) >= max_j:
                return False, f"{prof.get('nom','Prof')} max jurys/jour atteint"
        return True, None

    def assigner(self, etudiant, salle, creneau) -> dict:
        id_e = etudiant["id_etudiant"]
        id_s = salle["id_salle"]
        id_c = creneau["id_creneau"]
        id_j = creneau["index_jour"]

        self.salle_creneau[(id_s, id_c)] = id_e
        for prof_id in get_jury_ids(etudiant):
            self.prof_creneau[(prof_id, id_c)].append(id_e)
            self.prof_jour[(prof_id, id_j)] = \
                self.prof_jour.get((prof_id, id_j), 0) + 1

        jury_ids = get_jury_ids(etudiant)
        entree = {
            "id_etudiant":    id_e,
            "nom_etudiant":   etudiant["nom"],
            "domaine":        etudiant["domaine"],
            "titre":          etudiant["titre_memoire"][:50],
            "salle":          salle["nom"],
            "id_salle":       id_s,
            "jour":           creneau["jour"],
            "horaire":        creneau["horaire"],
            "id_creneau":     id_c,
            "directeur":      PROFS.get(etudiant["directeur_id"],{}).get("nom","?"),
            "examinateur":    PROFS.get(etudiant["examinateur_id"],{}).get("nom","?"),
            "jury3":          PROFS.get(etudiant["jury3_id"],{}).get("nom","?"),
            "statut":         "CONFIRME",
        }
        self.planning.append(entree)
        return entree

    def annuler(self, id_etudiant: str) -> bool:
        """Retire un tudiant du planning et libre ses ressources."""
        entree = next((p for p in self.planning
                       if p["id_etudiant"] == id_etudiant), None)
        if not entree:
            return False

        id_s = entree["id_salle"]
        id_c = entree["id_creneau"]
        etudiant = ETUDIANTS_MAP.get(id_etudiant, {})
        id_j = next((c["index_jour"] for c in CRENEAUX
                     if c["id_creneau"] == id_c), 0)

        self.salle_creneau.pop((id_s, id_c), None)
        for prof_id in get_jury_ids(etudiant):
            lst = self.prof_creneau.get((prof_id, id_c), [])
            if id_etudiant in lst:
                lst.remove(id_etudiant)
            if (prof_id, id_j) in self.prof_jour:
                self.prof_jour[(prof_id, id_j)] = \
                    max(0, self.prof_jour[(prof_id, id_j)] - 1)

        self.planning = [p for p in self.planning if p["id_etudiant"] != id_etudiant]
        return True

    def score_preference(self, etudiant, salle, creneau) -> float:
        score = 100.0
        if creneau["index_heure"] == 3: score -= 15
        if creneau["index_heure"] == 0: score += 10
        if "Vendredi" in creneau["jour"] and creneau["index_heure"] >= 2:
            score -= 20
        domaine = etudiant.get("domaine","")
        if domaine in ["IA","Web","Cloud","Cyber"] and "Lab" in salle["nom"]:
            score += 15
        nb_equip = len(str(salle.get("equipements","")).split("|"))
        score += nb_equip * 3
        score += np.random.uniform(0, 1)
        return score

    def planifier_un(self, etudiant) -> dict:
        """Planifie un seul tudiant (utilis pour la replanification)."""
        meilleur_score   = -999
        meilleure_option = None

        for creneau in CRENEAUX:
            for salle in SALLES:
                ok, _ = self.peut_assigner(etudiant, salle, creneau)
                if not ok:
                    continue
                score = self.score_preference(etudiant, salle, creneau)
                if score > meilleur_score:
                    meilleur_score   = score
                    meilleure_option = (salle, creneau)

        if meilleure_option:
            salle, creneau = meilleure_option
            return self.assigner(etudiant, salle, creneau)
        return None

    def calendrier(self) -> dict:
        """Organise le planning sous forme de calendrier jour par jour."""
        cal = defaultdict(list)
        for p in self.planning:
            cal[p["jour"]].append({
                "horaire":     p["horaire"],
                "etudiant":    p["nom_etudiant"],
                "domaine":     p["domaine"],
                "salle":       p["salle"],
                "directeur":   p["directeur"],
                "jury":        f"{p['examinateur']}, {p['jury3']}",
            })
        return dict(sorted(cal.items()))

    def verifier_conflits(self) -> list:
        """Vrifie l'intgrit du planning et retourne les conflits."""
        conflits = []
        sc_check = {}
        for p in self.planning:
            key = (p["id_salle"], p["id_creneau"])
            if key in sc_check:
                conflits.append({
                    "type": "SALLE",
                    "detail": f"{p['salle']} doublement rserve  {p['horaire']} le {p['jour']}"
                })
            sc_check[key] = p["id_etudiant"]

        pc_check = defaultdict(list)
        for p in self.planning:
            for role in ["directeur","examinateur","jury3"]:
                pc_check[(p[role], p["id_creneau"])].append(p["nom_etudiant"])
        for (prof, cr), etuds in pc_check.items():
            if len(etuds) > 1:
                conflits.append({
                    "type": "PROFESSEUR",
                    "detail": f"{prof} planifi pour {len(etuds)} soutenances simultanes"
                })
        return conflits

    def statistiques(self) -> dict:
        """Tableau de bord complet du planning."""
        nb_planifies = len(self.planning)
        nb_eligibles = sum(1 for e in ETUDIANTS
                           if e["paiement_valide"] and e["pre_soutenance_ok"])

        salle_counts = defaultdict(int)
        prof_jurys   = defaultdict(int)
        jour_counts  = defaultdict(int)

        for p in self.planning:
            salle_counts[p["salle"]] += 1
            jour_counts[p["jour"]]   += 1
            for role in ["directeur","examinateur","jury3"]:
                prof_jurys[p[role]] += 1

        return {
            "nb_planifies":       nb_planifies,
            "nb_eligibles":       nb_eligibles,
            "nb_total_etudiants": len(ETUDIANTS),
            "taux_planification": round(nb_planifies/max(nb_eligibles,1)*100,1),
            "nb_conflits":        len(self.verifier_conflits()),
            "repartition_salles": dict(salle_counts),
            "repartition_jours":  dict(jour_counts),
            "top_profs_jurys":    dict(sorted(
                prof_jurys.items(), key=lambda x:-x[1])[:5]),
        }


#  INITIALISATION ET PLANIFICATION INITIALE 

etat = EtatPlanning()

def planification_initiale():
    """Lance la planification de tous les tudiants ligibles."""
    etat.reset()
    eligibles = [e for e in ETUDIANTS
                 if e["paiement_valide"] and e["pre_soutenance_ok"]]

    def nb_creneaux_dispo(e):
        indispos_e = parse_indispos(e.get("creneaux_indispos",""))
        dispo = 0
        for c in CRENEAUX:
            if c["id_creneau"] in indispos_e: continue
            jury_ids = get_jury_ids(e)
            ok = all(c["id_creneau"] not in
                     parse_indispos(PROFS.get(p,{}).get("creneaux_indispos",""))
                     for p in jury_ids if p in PROFS)
            if ok: dispo += 1
        return dispo

    for etudiant in sorted(eligibles, key=nb_creneaux_dispo):
        etat.planifier_un(etudiant)

planification_initiale()


#  DMONSTRATION 

print("=" * 65)
print("MODULE DEFENCE SCHEDULER  DMONSTRATION API")
print("=" * 65)

stats = etat.statistiques()
print(f"\n STATISTIQUES DU PLANNING INITIAL :")
print(f"   Planifis       : {stats['nb_planifies']}/{stats['nb_eligibles']} ligibles")
print(f"   Taux russite   : {stats['taux_planification']}%")
print(f"   Conflits        : {stats['nb_conflits']}")

print(f"\n CALENDRIER DES SOUTENANCES :")
print("" * 65)
cal = etat.calendrier()
for jour, seances in list(cal.items())[:3]:
    print(f"\n   {jour}")
    for s in seances:
        print(f"    {s['horaire']}  {s['salle']:<18}  "
              f"{s['etudiant']:<15}  ({s['domaine']})")
        print(f"              Dir: {s['directeur'][:25]}  "
              f"Jury: {s['jury'][:30]}")

print(f"\n    ... ({len(cal)} jours planifis au total)")

#  Scnario de replanification 
print(f"\n{''*65}")
print(f"SCNARIO : Replanification d'urgence")
print(""*65)

if etat.planning:
    etudiant_a_reporter = etat.planning[0]
    id_e = etudiant_a_reporter["id_etudiant"]

    print(f"\n    Le Prof. {etudiant_a_reporter['directeur'][:25]} est absent.")
    print(f"     Soutenance de {etudiant_a_reporter['nom_etudiant']} "
          f"({etudiant_a_reporter['jour']}, {etudiant_a_reporter['horaire']}) annule.")

    # Annulation
    etat.annuler(id_e)
    print(f"\n   Recherche d'un nouveau crneau...")

    # Replanification
    etudiant_obj = ETUDIANTS_MAP.get(id_e)
    if etudiant_obj:
        nouveau = etat.planifier_un(etudiant_obj)
        if nouveau:
            print(f"   Replanifi : {nouveau['jour']}  {nouveau['horaire']}  "
                  f" {nouveau['salle']}")
        else:
            print(f"   Impossible de replanifier  aucun crneau disponible.")

conflits_finaux = etat.verifier_conflits()
print(f"\n  Vrification finale : "
      f"{' Aucun conflit' if not conflits_finaux else f' {len(conflits_finaux)} conflits'}")

print("\n" + "="*65)
print("  MODULE DEFENCE SCHEDULER OPRATIONNEL ")
print("="*65)

#  API FASTAPI 

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="API Defence Scheduler  Plateforme Mmoire",
        version="1.0.0",
        description="Planification intelligente des soutenances sans conflit"
    )
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])

    class ReplanifierRequest(BaseModel):
        id_etudiant: str
        raison:      str = "Annulation"

    @app.get("/sante", tags=["Systme"])
    def sante():
        s = etat.statistiques()
        return {"statut":"ok", "module":"Defence Scheduler",
                "planifies": s["nb_planifies"], "conflits": s["nb_conflits"]}

    @app.post("/planifier", tags=["Planification"])
    def planifier():
        """Lance/relance la planification complte de toutes les soutenances."""
        planification_initiale()
        return {
            "message": "Planification termine",
            **etat.statistiques(),
        }

    @app.get("/planning", tags=["Planification"])
    def get_planning():
        """Retourne le planning complet avec tous les dtails."""
        return {
            "nb_entrees": len(etat.planning),
            "planning":   etat.planning,
        }

    @app.get("/planning/calendrier", tags=["Planification"])
    def get_calendrier():
        """Vue calendrier organise par jour  pour affichage React."""
        return {"calendrier": etat.calendrier()}

    @app.post("/replanifier", tags=["Planification"])
    def replanifier(req: ReplanifierRequest):
        """
        Replanifie un tudiant suite  une annulation de dernire minute.
        Le systme trouve automatiquement le prochain crneau valide.
        """
        ancien = next((p for p in etat.planning
                       if p["id_etudiant"] == req.id_etudiant), None)
        if not ancien:
            raise HTTPException(404, f"tudiant {req.id_etudiant} non trouv dans le planning")

        etat.annuler(req.id_etudiant)
        etudiant = ETUDIANTS_MAP.get(req.id_etudiant)
        if not etudiant:
            raise HTTPException(404, f"Donnes tudiant {req.id_etudiant} introuvables")

        nouveau = etat.planifier_un(etudiant)
        if nouveau:
            return {
                "message":    "Replanification russie",
                "ancien":     ancien,
                "nouveau":    nouveau,
                "raison":     req.raison,
            }
        raise HTTPException(409,
            "Aucun crneau disponible pour la replanification. "
            "Vrifiez les disponibilits des professeurs.")

    @app.get("/conflits", tags=["Vrification"])
    def get_conflits():
        """Vrifie l'intgrit du planning actuel."""
        conflits = etat.verifier_conflits()
        return {
            "nb_conflits": len(conflits),
            "planning_ok": len(conflits) == 0,
            "conflits":    conflits,
        }

    @app.get("/statistiques", tags=["Tableau de bord"])
    def get_statistiques():
        """Tableau de bord complet du planning."""
        return etat.statistiques()

    @app.get("/disponibilites/{id_prof}", tags=["Professeurs"])
    def disponibilites_prof(id_prof: str):
        """Crneaux encore libres pour un professeur donn."""
        prof = PROFS.get(id_prof)
        if not prof:
            raise HTTPException(404, f"Professeur {id_prof} introuvable")

        indispos = parse_indispos(prof.get("creneaux_indispos",""))
        occupes  = {id_c for (pid, id_c), lst in etat.prof_creneau.items()
                    if pid == id_prof and lst}
        libres   = [c for c in CRENEAUX
                    if c["id_creneau"] not in indispos
                    and c["id_creneau"] not in occupes]

        return {
            "id_prof":          id_prof,
            "nom":              prof["nom"],
            "nb_creneaux_libres": len(libres),
            "creneaux_libres":  libres[:10],
        }

    @app.get("/etudiants/non-planifies", tags=["tudiants"])
    def etudiants_non_planifies():
        """Liste des tudiants ligibles non encore planifis."""
        planifies_ids = {p["id_etudiant"] for p in etat.planning}
        non_planifies = [
            e for e in ETUDIANTS
            if e["paiement_valide"] and e["pre_soutenance_ok"]
            and e["id_etudiant"] not in planifies_ids
        ]
        return {
            "nb": len(non_planifies),
            "etudiants": non_planifies,
        }

    print("\n API Defence Scheduler prte.")
    print("   Lancer : uvicorn etape3_api_scheduler:app --reload --port 8006")
    print("   Docs   : http://localhost:8006/docs")

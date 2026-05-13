import requests
import os

BASE_URL = "http://127.0.0.1:8003/api/v1"

def run_tests():
    print("=== DÉMARRAGE DES TESTS DU MODULE MÉMOIRE ===\n")
    
    # 1. Préparer des fichiers de test
    with open("test_v1.pdf", "w") as f: f.write("%PDF-1.4 test content v1")
    with open("test_v2.pdf", "w") as f: f.write("%PDF-1.4 test content v2")
    with open("fake.txt", "w") as f: f.write("Ceci n'est pas un PDF")

    try:
        # --- TEST 1: Dépôt initial (Succès attendu) ---
        print("[TEST 1] Dépôt initial du mémoire (v1)...")
        with open('test_v1.pdf', 'rb') as f_v1:
            files = {'fichier': ('mon_memoire.pdf', f_v1, 'application/pdf')}
            data = {
                'titre': 'IA et Agriculture en Afrique',
                'description': 'Étude sur l\'impact des drones',
                'domaine': 'Agri-Tech',
                'annee_academique': '2024-2025',
                'etudiant_id': 1
            }
            res = requests.post(f"{BASE_URL}/memoires/", data=data, files=files)
            print(f"Statut: {res.status_code}")
            if res.status_code == 201:
                memoire_id = res.json()['id']
                print(f"[OK] Succès ! Mémoire créé avec ID: {memoire_id}")
            else:
                print(f"[FAIL] Échec: {res.text}")
                return

        # --- TEST 2: Sécurité type de fichier (Erreur attendue) ---
        print("\n[TEST 2] Tentative d'envoi d'un fichier TXT au lieu de PDF...")
        with open('fake.txt', 'rb') as f_fake:
            files = {'fichier': ('fake.txt', f_fake, 'text/plain')}
            res = requests.post(f"{BASE_URL}/memoires/{memoire_id}/versions", data={'etudiant_id': 1}, files=files)
            print(f"Statut (attendu 400): {res.status_code}")
            if res.status_code == 400:
                print("[OK] Succès ! Le système a bien bloqué le fichier non-PDF.")
            else:
                print("[FAIL] Erreur: Le système aurait dû bloquer ce fichier.")

        # --- TEST 3: Nouvelle version (Succès attendu) ---
        print("\n[TEST 3] Envoi de la version 2 (v2)...")
        with open('test_v2.pdf', 'rb') as f_v2:
            files = {'fichier': ('mon_memoire_corrige.pdf', f_v2, 'application/pdf')}
            data = {'message_depot': 'Correction du chapitre 1', 'etudiant_id': 1}
            res = requests.post(f"{BASE_URL}/memoires/{memoire_id}/versions", data=data, files=files)
            print(f"Statut: {res.status_code}")
            if res.status_code == 201:
                version_id = res.json()['id']
                print(f"[OK] Succès ! Version 2 enregistrée (ID: {version_id})")
            else:
                print(f"[FAIL] Échec: {res.text}")

        # --- TEST 4: Lecture détails et historique ---
        print("\n[TEST 4] Lecture du mémoire et historique...")
        res = requests.get(f"{BASE_URL}/memoires/{memoire_id}")
        if res.status_code == 200:
            data = res.json()
            print(f"Titre: {data['titre']}")
            print(f"Nombre de versions trouvées: {len(data['versions'])}")
            print(f"Statut courant: {data['statut']}")
            if len(data['versions']) == 2:
                print("[OK] Succès ! L'historique contient bien les 2 versions.")
            else:
                print("[FAIL] Erreur dans l'historique.")

        # --- TEST 5: Téléchargement ---
        print("\n[TEST 5] Test du téléchargement de la v2...")
        res = requests.get(f"{BASE_URL}/memoires/{memoire_id}/versions/{version_id}/telecharger")
        print(f"Statut: {res.status_code}")
        if res.status_code == 200:
            print(f"[OK] Succès ! Fichier reçu ({len(res.content)} octets).")
        else:
            print(f"[FAIL] Échec du téléchargement.")

    finally:
        # Nettoyage
        for f in ["test_v1.pdf", "test_v2.pdf", "fake.txt"]:
            if os.path.exists(f): 
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    run_tests()

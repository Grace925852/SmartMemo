from app.database import SessionLocal
from app.models import User, Etudiant

def setup_test_data():
    db = SessionLocal()
    # Créer un utilisateur de test
    user = db.query(User).filter(User.email == "etudiant@test.com").first()
    if not user:
        user = User(
            email="etudiant@test.com",
            nom="Test",
            prenom="Etudiant",
            role="etudiant",
            hashed_password="fakehashedpassword"
        )
        db.add(user)
        db.flush()
    
    # Créer un étudiant lié
    etudiant = db.query(Etudiant).filter(Etudiant.user_id == user.id).first()
    if not etudiant:
        etudiant = Etudiant(
            user_id=user.id,
            numero_etudiant="IPNET-2024-001",
            filiere="Informatique",
            niveau="Master 2"
        )
        db.add(etudiant)
    
    db.commit()
    print(f"✅ Données de test prêtes : Étudiant ID = {etudiant.id}")
    db.close()

if __name__ == "__main__":
    setup_test_data()

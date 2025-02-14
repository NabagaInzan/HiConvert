from supabase import create_client
import os
import logging
from pathlib import Path

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Supabase
SUPABASE_URL = "https://rjksrjvidvoizpawozha.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqa3NyanZpZHZvaXpwYXdvemhhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNzEwNzQyMCwiZXhwIjoyMDUyNjgzNDIwfQ.Igsskf2JWe0ZVwg8oQ_vOiSE5VSt_1gEKXJLeSVmCik"

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Connexion à Supabase établie avec succès")
except Exception as e:
    logger.error(f"Erreur de connexion à Supabase: {str(e)}")
    raise

def create_superadmin(email, password, first_name, last_name, phone_number):
    """Crée un compte super administrateur"""
    try:
        # 1. Créer l'utilisateur dans auth.users
        user_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        user = user_response.user
        
        if not user:
            logger.error("Erreur lors de la création de l'utilisateur")
            return False
            
        # 2. Récupérer l'ID du rôle superadmin
        role_response = supabase.table('roles').select('id').eq('name', 'superadmin').execute()
        if not role_response.data:
            logger.error("Rôle superadmin introuvable")
            return False
            
        superadmin_role_id = role_response.data[0]['id']
        
        # 3. Créer le profil utilisateur
        profile_data = {
            'id': user.id,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone_number,
            'role_id': superadmin_role_id,
            'status': 'active'
        }
        
        profile_response = supabase.table('user_profiles').insert(profile_data).execute()
        
        if not profile_response.data:
            logger.error("Erreur lors de la création du profil utilisateur")
            # TODO: Supprimer l'utilisateur auth.users créé
            return False
            
        logger.info(f"Super administrateur créé avec succès : {email}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du super administrateur : {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # Créer le super admin par défaut
        if create_superadmin(
            email="admin@hiconvert.com",
            password="Admin@2024",
            first_name="Super",
            last_name="Admin",
            phone_number="+237123456789"
        ):
            logger.info("Super administrateur créé avec succès")
        else:
            logger.error("Erreur lors de la création du super administrateur")
    except Exception as e:
        logger.error(f"Erreur : {str(e)}")
        raise

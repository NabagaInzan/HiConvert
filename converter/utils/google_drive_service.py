from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive.file']
        self.service = None
        self.initialize_service()

    def initialize_service(self):
        """Initialise le service Google Drive"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_DRIVE_SETTINGS['service_account_file'],
                scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Service Google Drive initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du service Google Drive: {str(e)}")
            raise

    def upload_file(self, file_path, mime_type):
        """Upload un fichier sur Google Drive"""
        try:
            file_metadata = {'name': os.path.basename(file_path)}
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            # Créer le fichier sur Google Drive
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # Définir les permissions pour rendre le fichier accessible via un lien
            self.service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            # Obtenir les liens de partage
            file_id = file.get('id')
            download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
            view_link = f"https://drive.google.com/file/d/{file_id}/view"
            
            logger.info(f"Fichier uploadé avec succès. ID: {file_id}")
            return {
                'file_id': file_id,
                'download_link': download_link,
                'view_link': view_link
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de l'upload du fichier {file_path}: {str(e)}")
            raise

    def delete_file(self, file_id):
        """Supprime un fichier de Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Fichier {file_id} supprimé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier {file_id}: {str(e)}")
            return False

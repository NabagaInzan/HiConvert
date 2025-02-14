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

    def get_file_url(self, file_id):
        """Obtient l'URL de visualisation d'un fichier"""
        try:
            # Vérifier que le fichier existe et est accessible
            file = self.service.files().get(
                fileId=file_id,
                fields='id, mimeType'
            ).execute()
            
            # Retourner l'URL de prévisualisation Google Drive
            return f"https://drive.google.com/file/d/{file_id}/preview"
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'URL du fichier {file_id}: {str(e)}")
            raise

    def get_download_url(self, file_id):
        """Obtient l'URL de téléchargement d'un fichier"""
        try:
            # Vérifier que le fichier existe et est accessible
            file = self.service.files().get(
                fileId=file_id,
                fields='id'
            ).execute()
            
            # Retourner l'URL de téléchargement direct
            return f"https://drive.google.com/uc?export=download&id={file_id}"
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'URL de téléchargement du fichier {file_id}: {str(e)}")
            raise

    def get_file_metadata(self, file_id):
        """Obtient les métadonnées d'un fichier"""
        try:
            return self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, webViewLink, webContentLink'
            ).execute()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métadonnées du fichier {file_id}: {str(e)}")
            raise

    def list_files(self, page_size=10, page_token=None):
        """Liste les fichiers du Drive"""
        try:
            results = self.service.files().list(
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, webContentLink)",
                pageToken=page_token
            ).execute()
            
            return {
                'files': results.get('files', []),
                'next_page_token': results.get('nextPageToken')
            }
        except Exception as e:
            logger.error(f"Erreur lors de la liste des fichiers: {str(e)}")
            raise

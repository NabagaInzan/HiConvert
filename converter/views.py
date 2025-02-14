from django.shortcuts import render
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .utils.pdf_processor import PDFProcessor
import os
import logging
from pathlib import Path
from werkzeug.utils import secure_filename
import time

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'converter/index.html')

@csrf_exempt
def process_files(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    if not request.FILES.getlist('files[]'):
        return JsonResponse({'error': 'Aucun fichier fourni'}, status=400)

    files = request.FILES.getlist('files[]')
    results = []
    processor = PDFProcessor()
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)

    # Filtrer uniquement les fichiers nommés "plan.pdf"
    plan_files = [f for f in files if f.name.lower() == 'plan.pdf']
    
    if not plan_files:
        return JsonResponse({
            'results': [{
                'file': 'Aucun fichier',
                'message': "Aucun fichier 'plan.pdf' trouvé dans la sélection",
                'status': 'error'
            }]
        })

    start_time = time.time()
    processed_files = 0

    for file in plan_files:
        start_file_time = time.time()
        
        try:
            # Construire le chemin complet du fichier
            filename = secure_filename(file.name)
            filepath = os.path.join(settings.UPLOAD_FOLDER, filename)
            
            # Sauvegarder le fichier
            with open(filepath, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Traiter le fichier
            csv_path = processor.process_pdf(filepath)
            processing_time = time.time() - start_file_time
            
            results.append({
                'file': file.name,
                'message': f'Traité en {processing_time:.2f} secondes',
                'csv_path': os.path.basename(csv_path),
                'status': 'success'
            })
            processed_files += 1

        except Exception as e:
            logger.error(f'Erreur lors du traitement de {file.name}: {str(e)}')
            results.append({
                'file': file.name,
                'message': f'Erreur lors du traitement: {str(e)}',
                'status': 'error'
            })

    total_time = time.time() - start_time
    logger.info(f"Terminé. Temps total: {total_time:.2f} secondes, Fichiers traités: {processed_files}/{len(plan_files)}")

    return JsonResponse({'results': results})

def download_file(request, filename):
    filepath = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return JsonResponse({'error': 'Fichier non trouvé'}, status=404)
    
    return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)

def allowed_file(filename):
    """Vérifie si le fichier est nommé exactement 'plan.pdf'"""
    return filename.lower() == 'plan.pdf'

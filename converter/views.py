from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import os
import pandas as pd
import logging
from .utils.google_drive_service import GoogleDriveService
from .utils.pdf_processor import PDFProcessor
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)
drive_service = GoogleDriveService()
pdf_processor = PDFProcessor()

def index(request):
    return render(request, 'converter/index.html')

@csrf_exempt
def process_files(request):
    """Traite les fichiers du dossier sélectionné et les upload sur Google Drive"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    if 'folder' not in request.FILES:
        return JsonResponse({'error': 'Aucun dossier fourni'}, status=400)

    results = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_dir = os.path.join(settings.TEMP_UPLOAD_FOLDER, timestamp)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Parcourir les fichiers uploadés
        for file in request.FILES.getlist('folder'):
            if file.name.lower() == 'plan.pdf':
                # Sauvegarder le PDF temporairement
                pdf_path = os.path.join(temp_dir, file.name)
                with open(pdf_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                # Traiter le PDF et générer le CSV
                coordinates = pdf_processor.extract_coordinates(pdf_path)
                csv_filename = os.path.splitext(file.name)[0] + '.csv'
                csv_path = os.path.join(temp_dir, csv_filename)
                pd.DataFrame(coordinates).to_csv(csv_path, index=False)

                # Upload les fichiers sur Google Drive
                pdf_drive = drive_service.upload_file(pdf_path, 'application/pdf')
                csv_drive = drive_service.upload_file(csv_path, 'text/csv')

                results.append({
                    'pdf': {
                        'name': file.name,
                        'download_url': pdf_drive['download_link'],
                        'view_url': pdf_drive['view_link'],
                        'file_id': pdf_drive['file_id']
                    },
                    'csv': {
                        'name': csv_filename,
                        'download_url': csv_drive['download_link'],
                        'view_url': csv_drive['view_link'],
                        'file_id': csv_drive['file_id']
                    }
                })

        # Nettoyer les fichiers temporaires
        shutil.rmtree(temp_dir)

        if not results:
            return JsonResponse({'error': 'Aucun fichier plan.pdf trouvé dans le dossier'}, status=400)

        return JsonResponse({
            'success': True,
            'message': 'Fichiers traités et uploadés avec succès',
            'results': results
        })

    except Exception as e:
        logger.error(f"Erreur lors du traitement des fichiers: {str(e)}")
        # Nettoyer en cas d'erreur
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return JsonResponse({'error': str(e)}, status=500)

def view_file(request, file_id):
    """Vue pour afficher un fichier depuis Google Drive"""
    try:
        file_url = drive_service.get_file_url(file_id)
        return HttpResponse(f'<iframe src="{file_url}" width="100%" height="100%" frameborder="0"></iframe>')
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du fichier: {str(e)}")
        return JsonResponse({'error': 'Fichier non trouvé'}, status=404)

def download_file(request, file_id):
    """Télécharger un fichier depuis Google Drive"""
    try:
        download_url = drive_service.get_download_url(file_id)
        return HttpResponse(download_url)
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier: {str(e)}")
        return JsonResponse({'error': 'Fichier non trouvé'}, status=404)

def download_both(request, csv_path):
    """Télécharger les deux fichiers dans un zip"""
    import zipfile
    from io import BytesIO
    
    csv_filepath = os.path.join(settings.UPLOAD_FOLDER, csv_path)
    pdf_filepath = os.path.join(settings.UPLOAD_FOLDER, os.path.dirname(csv_path), 'plan.pdf')
    
    if not os.path.exists(csv_filepath) or not os.path.exists(pdf_filepath):
        return JsonResponse({'error': 'Fichiers non trouvés'}, status=404)
    
    try:
        # Créer un fichier ZIP en mémoire
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Ajouter les fichiers au ZIP avec des noms de base
            zf.write(pdf_filepath, 'plan.pdf')
            zf.write(csv_filepath, os.path.basename(csv_filepath))
        
        # Préparer la réponse
        memory_file.seek(0)
        response = HttpResponse(memory_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename=plan_et_coordonnees.zip'
        
        return response
    except Exception as e:
        logger.error(f"Erreur lors de la création du ZIP: {str(e)}")
        return JsonResponse({'error': 'Erreur lors de la création du ZIP'}, status=500)

def view_csv(request, filename):
    """Vue pour afficher le contenu du CSV dans le navigateur"""
    filepath = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return JsonResponse({'error': 'Fichier non trouvé'}, status=404)
    
    try:
        import pandas as pd
        # Lire le CSV avec pandas
        df = pd.read_csv(filepath, sep=';')
        # Convertir en HTML avec style Bootstrap
        html_table = df.to_html(
            classes=['table', 'table-striped', 'table-hover', 'table-bordered'],
            float_format=lambda x: '{:.3f}'.format(x),
            index=False
        )
        
        context = {
            'filename': os.path.basename(filename),
            'table': html_table,
            'total_rows': len(df)
        }
        return render(request, 'converter/view_csv.html', context)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du CSV {filename}: {str(e)}")
        return JsonResponse({'error': 'Erreur lors de la lecture du fichier'}, status=500)

def view_both(request, csv_path):
    """Vue pour afficher à la fois le PDF et le CSV"""
    csv_filepath = os.path.join(settings.UPLOAD_FOLDER, csv_path)
    pdf_filepath = os.path.join(settings.UPLOAD_FOLDER, os.path.dirname(csv_path), 'plan.pdf')
    
    if not os.path.exists(csv_filepath) or not os.path.exists(pdf_filepath):
        return JsonResponse({'error': 'Fichiers non trouvés'}, status=404)
    
    try:
        import pandas as pd
        # Lire le CSV avec pandas
        df = pd.read_csv(csv_filepath, sep=';')
        # Convertir en HTML avec style Bootstrap
        html_table = df.to_html(
            classes=['table', 'table-striped', 'table-hover', 'table-bordered'],
            float_format=lambda x: '{:.3f}'.format(x),
            index=False
        )
        
        context = {
            'csv_filename': os.path.basename(csv_filepath),
            'pdf_filename': 'plan.pdf',
            'table': html_table,
            'total_rows': len(df),
            'pdf_path': os.path.dirname(csv_path) + '/plan.pdf',
            'csv_path': csv_path
        }
        return render(request, 'converter/view_both.html', context)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture des fichiers: {str(e)}")
        return JsonResponse({'error': 'Erreur lors de la lecture des fichiers'}, status=500)

def view_pdf(request, filename):
    """Vue pour afficher le PDF dans le navigateur"""
    filepath = os.path.join(settings.UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return JsonResponse({'error': 'Fichier non trouvé'}, status=404)
    
    try:
        with open(filepath, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(filename)
            return response
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du PDF {filename}: {str(e)}")
        return JsonResponse({'error': 'Erreur lors de la lecture du fichier'}, status=500)

def generate_report(request, csv_path):
    """Générer un rapport PDF avec statistiques"""
    import pandas as pd
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    import matplotlib.pyplot as plt
    import seaborn as sns
    from datetime import datetime
    
    csv_filepath = os.path.join(settings.UPLOAD_FOLDER, csv_path)
    if not os.path.exists(csv_filepath):
        return JsonResponse({'error': 'Fichier CSV non trouvé'}, status=404)
    
    try:
        # Lire les données
        df = pd.read_csv(csv_filepath, sep=';')
        
        # Créer un buffer pour le PDF
        buffer = BytesIO()
        
        # Créer le document PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Titre
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph("Rapport d'Analyse des Coordonnées", title_style))
        story.append(Spacer(1, 12))
        
        # Informations générales
        story.append(Paragraph(f"Date du rapport : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        story.append(Paragraph(f"Fichier source : {os.path.basename(csv_filepath)}", styles['Normal']))
        story.append(Paragraph(f"Nombre total de points : {len(df)}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Statistiques descriptives
        story.append(Paragraph("Statistiques Descriptives", styles['Heading2']))
        stats_df = df.describe()
        stats_table = Table([
            ['Statistique', 'Coordonnée X', 'Coordonnée Y']
        ] + [
            [index, f"{row['X']:.2f}", f"{row['Y']:.2f}"]
            for index, row in stats_df.iterrows()
        ])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Graphique de dispersion
        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=df, x='X', y='Y', alpha=0.6)
        plt.title('Distribution des Points')
        plt.xlabel('Coordonnée X')
        plt.ylabel('Coordonnée Y')
        
        # Sauvegarder le graphique
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        # Ajouter le graphique au PDF
        story.append(Paragraph("Distribution des Points", styles['Heading2']))
        img = Image(img_buffer, width=6*inch, height=4*inch)
        story.append(img)
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        # Retourner le PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=rapport_coordonnees_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
        return JsonResponse({'error': 'Erreur lors de la génération du rapport'}, status=500)

def allowed_file(filename):
    """Vérifie si le fichier est nommé exactement 'plan.pdf'"""
    return filename.lower() == 'plan.pdf'

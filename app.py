from flask import Flask, render_template, request, send_file, jsonify, make_response
from utils.pdf_processor import PDFProcessor
from utils.logger import app_logger
import os
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.utils import secure_filename
import gc
from werkzeug.middleware.proxy_fix import ProxyFix
import json

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Créer le dossier uploads s'il n'existe pas
upload_dir = Path(app.config['UPLOAD_FOLDER'])
upload_dir.mkdir(parents=True, exist_ok=True)

@app.before_request
def before_request():
    gc.collect()

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    # Vérifier que c'est un PDF et que le nom contient "plan"
    return filename.lower().endswith('.pdf') and 'plan' in filename.lower()

@app.route('/process', methods=['POST'])
def process_files():
    try:
        if 'files[]' not in request.files:
            return make_response(jsonify({'error': 'Aucun fichier fourni'}), 400)
        
        files = request.files.getlist('files[]')
        if not files:
            return make_response(jsonify({'error': 'Aucun fichier sélectionné'}), 400)

        results = []
        processor = PDFProcessor()
        
        for file in files:
            filename = file.filename
            if not filename or not allowed_file(filename):
                results.append({
                    'file': filename,
                    'message': "Ignoré : Ce n'est pas un fichier plan.pdf",
                    'csv_path': None
                })
                continue

            try:
                # Sécuriser le nom du fichier
                filename = secure_filename(filename)
                
                # Créer un dossier pour ce fichier
                file_dir = upload_dir / Path(filename).stem
                file_dir.mkdir(parents=True, exist_ok=True)
                
                # Sauvegarder le fichier PDF
                pdf_path = file_dir / filename
                file.save(str(pdf_path))
                
                try:
                    # Traiter le fichier
                    csv_path, message = processor.process_file(pdf_path)
                    
                    results.append({
                        'file': filename,
                        'message': message,
                        'csv_path': f"{Path(filename).stem}/{csv_path}"
                    })
                except Exception as e:
                    app_logger.error(f"Erreur lors du traitement du fichier {filename}: {str(e)}")
                    results.append({
                        'file': filename,
                        'message': f"Erreur: {str(e)}",
                        'csv_path': None
                    })
                finally:
                    gc.collect()
                    
            except Exception as e:
                app_logger.error(f"Erreur lors de la sauvegarde du fichier {filename}: {str(e)}")
                results.append({
                    'file': filename,
                    'message': f"Erreur: {str(e)}",
                    'csv_path': None
                })

        # Vérifier si au moins un fichier plan a été traité
        processed_plans = [r for r in results if r['csv_path'] is not None]
        if not processed_plans:
            return make_response(jsonify({
                'status': 'warning',
                'message': 'Aucun fichier plan.pdf trouvé parmi les fichiers sélectionnés',
                'results': results
            }), 200)

        return make_response(jsonify({
            'status': 'success',
            'message': f"{len(processed_plans)} fichier(s) plan.pdf traité(s)",
            'results': results
        }), 200)
        
    except Exception as e:
        app_logger.error(f"Erreur générale: {str(e)}")
        return make_response(jsonify({'error': 'Une erreur inattendue est survenue'}), 500)

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        # Construire le chemin complet
        file_path = upload_dir / filename
        
        if not file_path.is_file():
            raise FileNotFoundError(f"Le fichier {filename} n'existe pas")
        
        return send_file(
            str(file_path),
            mimetype='text/csv',
            as_attachment=True,
            download_name=file_path.name
        )
    except Exception as e:
        app_logger.error(f"Erreur lors du téléchargement du fichier: {str(e)}")
        return make_response(jsonify({'error': str(e)}), 404)

@app.errorhandler(404)
def not_found_error(error):
    return make_response(jsonify({'error': 'Page non trouvée'}), 404)

@app.errorhandler(413)
def request_entity_too_large(error):
    return make_response(jsonify({'error': 'La taille du fichier dépasse la limite autorisée'}), 413)

@app.errorhandler(500)
def internal_server_error(error):
    return make_response(jsonify({'error': 'Une erreur interne est survenue'}), 500)

@app.errorhandler(502)
def bad_gateway_error(error):
    return make_response(jsonify({'error': 'Erreur de passerelle'}), 502)

@app.errorhandler(Exception)
def handle_exception(error):
    app_logger.error(f"Erreur non gérée: {str(error)}")
    return make_response(jsonify({'error': 'Une erreur inattendue est survenue'}), 500)

if __name__ == '__main__':
    app_logger.info("Démarrage de l'application Hi Convert")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)

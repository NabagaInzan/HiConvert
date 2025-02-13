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
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))  # 20MB
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure upload folder exists
upload_dir = Path(app.config['UPLOAD_FOLDER'])
upload_dir.mkdir(parents=True, exist_ok=True)

@app.before_request
def before_request():
    # Nettoyer la mémoire avant chaque requête
    gc.collect()

@app.after_request
def after_request(response):
    # Ajouter des headers pour éviter les problèmes de cache et CORS
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Assurer que la réponse JSON est valide
    if response.mimetype == 'application/json':
        try:
            json.loads(response.get_data().decode('utf-8'))
        except json.JSONDecodeError:
            return make_response(jsonify({'error': 'Invalid JSON response'}), 500)
    
    return response

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return filename.lower().endswith('.pdf')

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
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    
                    # Créer un dossier temporaire pour ce fichier
                    temp_dir = upload_dir / Path(filename).stem
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Sauvegarder le fichier
                    file_path = temp_dir / "plan.pdf"
                    file.save(str(file_path))
                    
                    try:
                        # Traiter le fichier
                        csv_path, message = processor.process_file(str(file_path), temp_dir.name)
                        results.append({
                            'file': filename,
                            'message': message,
                            'csv_path': str(csv_path) if csv_path else None
                        })
                    except Exception as e:
                        app_logger.error(f"Erreur lors du traitement du fichier {filename}: {str(e)}")
                        results.append({
                            'file': filename,
                            'message': f"Erreur: {str(e)}",
                            'csv_path': None
                        })
                    finally:
                        # Nettoyer la mémoire après chaque fichier
                        gc.collect()
                        
                except Exception as e:
                    app_logger.error(f"Erreur lors de la sauvegarde du fichier {filename}: {str(e)}")
                    results.append({
                        'file': filename,
                        'message': f"Erreur: {str(e)}",
                        'csv_path': None
                    })

        if not results:
            return make_response(jsonify({'error': 'Aucun fichier PDF valide trouvé'}), 400)

        response_data = {
            'status': 'success',
            'message': f"{len(results)} fichiers traités",
            'results': results
        }
        
        return make_response(jsonify(response_data), 200)
        
    except Exception as e:
        app_logger.error(f"Erreur générale: {str(e)}")
        return make_response(jsonify({'error': 'Une erreur inattendue est survenue'}), 500)

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        file_path = Path(filename)
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

@app.errorhandler(413)
def request_entity_too_large(error):
    return make_response(jsonify({'error': 'La taille du fichier dépasse la limite autorisée'}), 413)

@app.errorhandler(500)
def internal_server_error(error):
    return make_response(jsonify({'error': 'Une erreur interne est survenue'}), 500)

@app.errorhandler(502)
def bad_gateway_error(error):
    return make_response(jsonify({'error': 'Erreur de passerelle'}), 502)

if __name__ == '__main__':
    app_logger.info("Démarrage de l'application Hi Convert")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

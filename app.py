from flask import Flask, render_template, request, send_file, jsonify, make_response, Response
from utils.pdf_processor import PDFProcessor
from utils.logger import app_logger
import os
import sys
import traceback
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.utils import secure_filename
import gc
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
import logging

# Configuration des logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration de base
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configuration du proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

# Créer le dossier uploads s'il n'existe pas
upload_dir = Path(app.config['UPLOAD_FOLDER'])
upload_dir.mkdir(parents=True, exist_ok=True)

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Method: %s, Path: %s', request.method, request.path)
    logger.debug('Client IP: %s', request.remote_addr)
    
    # Vérifier si la requête attend du JSON
    if request.path != '/' and not request.path.startswith('/static/'):
        logger.debug('Checking Accept header for JSON')
        if 'application/json' not in request.accept_mimetypes:
            logger.warning('Request does not accept JSON')
            return make_response(jsonify({'error': 'Ce point de terminaison nécessite Accept: application/json'}), 406)
    gc.collect()

@app.after_request
def after_request(response):
    # Log de la réponse
    logger.debug('Response Status: %s', response.status)
    logger.debug('Response Headers: %s', response.headers)
    
    # Ne pas modifier les réponses de fichiers statiques
    if not request.path.startswith('/static/'):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.errorhandler(400)
def bad_request_error(error):
    logger.error('Bad Request: %s', error)
    return make_response(jsonify({'error': str(error)}), 400)

@app.errorhandler(404)
def not_found_error(error):
    logger.error('Not Found: %s', error)
    return make_response(jsonify({'error': 'Page non trouvée'}), 404)

@app.errorhandler(405)
def method_not_allowed_error(error):
    logger.error('Method Not Allowed: %s', error)
    return make_response(jsonify({'error': 'Méthode non autorisée'}), 405)

@app.errorhandler(413)
def request_entity_too_large(error):
    logger.error('Request Entity Too Large: %s', error)
    return make_response(jsonify({'error': 'La taille du fichier dépasse la limite autorisée'}), 413)

@app.errorhandler(500)
def internal_server_error(error):
    logger.error('Server Error: %s\n%s', error, traceback.format_exc())
    return make_response(jsonify({'error': 'Une erreur interne est survenue'}), 500)

@app.errorhandler(502)
def bad_gateway_error(error):
    logger.error('Bad Gateway: %s', error)
    return make_response(jsonify({'error': 'Erreur de passerelle'}), 502)

@app.errorhandler(HTTPException)
def handle_http_exception(error):
    logger.error('HTTP Exception: %s', error)
    response = error.get_response()
    response.data = jsonify({
        "code": error.code,
        "name": error.name,
        "description": error.description,
    }).get_data()
    response.content_type = "application/json"
    return response

@app.errorhandler(Exception)
def handle_exception(error):
    logger.error('Unhandled Exception: %s\n%s', error, traceback.format_exc())
    return make_response(jsonify({
        'error': 'Une erreur inattendue est survenue',
        'details': str(error) if app.debug else None
    }), 500)

@app.route('/')
def index():
    try:
        logger.info('Serving index page')
        return render_template('index.html')
    except Exception as e:
        logger.error('Error rendering index: %s\n%s', e, traceback.format_exc())
        return make_response(jsonify({'error': 'Erreur lors du chargement de la page'}), 500)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    ALLOWED_MIMETYPES = {'application/pdf'}
    
    # Vérifier l'extension
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False
        
    # Si c'est une requête avec un fichier, vérifier le type MIME
    if request.method == 'POST' and 'files[]' in request.files:
        file = request.files['files[]']
        if file.content_type not in ALLOWED_MIMETYPES:
            return False
            
    return True

@app.route('/process', methods=['POST'])
def process_files():
    try:
        logger.debug('Starting process_files')
        logger.debug('Request Content-Type: %s', request.content_type)
        logger.debug('Request Content-Length: %s', request.content_length)
        
        # Vérifier la taille du contenu
        if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
            logger.warning('File size exceeds limit: %s > %s', request.content_length, app.config['MAX_CONTENT_LENGTH'])
            return make_response(jsonify({
                'error': 'La taille du fichier dépasse la limite autorisée',
                'max_size': app.config['MAX_CONTENT_LENGTH']
            }), 413)

        if 'files[]' not in request.files:
            logger.warning('No files in request')
            return make_response(jsonify({'error': 'Aucun fichier fourni'}), 400)

        files = request.files.getlist('files[]')
        logger.debug('Number of files received: %d', len(files))
        
        if not files:
            logger.warning('Empty files list')
            return make_response(jsonify({'error': 'Aucun fichier sélectionné'}), 400)

        results = []
        processor = PDFProcessor()

        for file in files:
            logger.debug('Processing file: %s', file.filename if file else 'None')
            
            if not file or not file.filename:
                logger.warning('Invalid file object or empty filename')
                continue

            if not allowed_file(file.filename):
                logger.warning('File type not allowed: %s', file.filename)
                results.append({
                    'file': file.filename,
                    'message': "Ignoré : Ce n'est pas un fichier PDF valide",
                    'csv_path': None,
                    'status': 'error'
                })
                continue

            try:
                filename = secure_filename(file.filename)
                logger.debug('Secured filename: %s', filename)
                
                file_dir = upload_dir / Path(filename).stem
                logger.debug('Creating directory: %s', file_dir)
                file_dir.mkdir(parents=True, exist_ok=True)
                
                pdf_path = file_dir / filename
                logger.debug('Saving file to: %s', pdf_path)
                file.save(str(pdf_path))

                logger.debug('Processing PDF with PDFProcessor')
                csv_path, message = processor.process_file(pdf_path)
                logger.debug('PDF processed successfully: %s', csv_path)
                
                results.append({
                    'file': filename,
                    'message': message,
                    'csv_path': f"{Path(filename).stem}/{csv_path}",
                    'status': 'success'
                })

            except Exception as e:
                error_msg = str(e)
                logger.error('Error processing file %s: %s\n%s', filename, error_msg, traceback.format_exc())
                results.append({
                    'file': filename,
                    'message': f"Erreur: {error_msg}",
                    'csv_path': None,
                    'status': 'error'
                })
                
            finally:
                logger.debug('Cleaning up memory')
                gc.collect()

        logger.debug('Preparing response with %d results', len(results))
        response_data = {
            'status': 'success',
            'message': f"{len(results)} fichier(s) traité(s)",
            'results': results
        }
        
        # Vérifier que la réponse est valide
        try:
            logger.debug('Validating JSON response')
            jsonify(response_data)
        except Exception as e:
            logger.error('Error creating JSON response: %s\n%s', str(e), traceback.format_exc())
            return make_response(jsonify({'error': 'Erreur lors de la création de la réponse'}), 500)

        logger.debug('Sending successful response')
        return make_response(jsonify(response_data), 200)

    except Exception as e:
        error_msg = str(e)
        logger.error('General error in process_files: %s\n%s', error_msg, traceback.format_exc())
        return make_response(jsonify({
            'error': 'Une erreur inattendue est survenue',
            'details': error_msg
        }), 500)

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
        logger.error('Error downloading file: %s\n%s', e, traceback.format_exc())
        return make_response(jsonify({'error': str(e)}), 404)

if __name__ == '__main__':
    logger.info("Démarrage de l'application Hi Convert")
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Démarrage sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

from flask import Flask, render_template, request, send_file, jsonify
from utils.pdf_processor import PDFProcessor
from utils.logger import app_logger
import os
from dotenv import load_dotenv
from pathlib import Path

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

# Ensure upload folder exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_directory():
    if 'directory' not in request.form:
        return jsonify({'error': 'Aucun chemin de dossier fourni'}), 400
    
    directory_path = Path(request.form['directory'])
    
    if not directory_path.exists():
        return jsonify({'error': 'Chemin de dossier invalide'}), 400

    try:
        processor = PDFProcessor()
        results, summary = processor.process_directory(str(directory_path))
        
        return jsonify({
            'status': 'success',
            'message': summary,
            'results': results
        })
    except Exception as e:
        app_logger.error(f"Erreur lors du traitement du dossier: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        filename = Path(filename)
        return send_file(str(filename),
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=filename.name)
    except Exception as e:
        app_logger.error(f"Erreur lors du téléchargement du fichier: {str(e)}")
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app_logger.info("Démarrage de l'application Hi Convert")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

from flask import Flask, render_template, request, send_file, jsonify
from utils.pdf_processor import PDFProcessor
from utils.logger import app_logger
import os
from dotenv import load_dotenv
from pathlib import Path
from werkzeug.utils import secure_filename
import gc

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

# Ensure upload folder exists
upload_dir = Path(app.config['UPLOAD_FOLDER'])
upload_dir.mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return filename.lower().endswith('.pdf')

@app.route('/process', methods=['POST'])
def process_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    files = request.files.getlist('files[]')
    if not files:
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

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
                        'csv_path': csv_path if csv_path else None
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
        return jsonify({'error': 'Aucun fichier PDF valide trouvé'}), 400

    return jsonify({
        'status': 'success',
        'message': f"{len(results)} fichiers traités",
        'results': results
    })

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
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app_logger.info("Démarrage de l'application Hi Convert")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

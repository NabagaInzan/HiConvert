import os
import time
import pandas as pd
from pdf2image import convert_from_path
import easyocr
import numpy as np
import re
from .logger import app_logger
from pathlib import Path
import gc
from PIL import Image

class PDFProcessor:
    def __init__(self):
        self.reader = None
        self.poppler_path = os.getenv('POPPLER_PATH')
        self.logger = app_logger
        self.zoom_factor = 1.5  # Réduit de 3 à 1.5

    def get_reader(self):
        if self.reader is None:
            self.reader = easyocr.Reader(['fr'])
        return self.reader

    def zoom_image(self, img):
        width, height = img.size
        new_width = int(width * self.zoom_factor)
        new_height = int(height * self.zoom_factor)
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def process_file(self, pdf_path):
        """
        Traite un fichier PDF et retourne le chemin du CSV généré
        """
        try:
            self.logger.info(f"Début du traitement du fichier : {pdf_path}")
            pdf_path = Path(pdf_path)
            if not pdf_path.is_file():
                raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")

            start_time = time.time()
            
            # Créer le dossier de sortie s'il n'existe pas
            output_dir = pdf_path.parent / 'results'
            output_dir.mkdir(exist_ok=True)
            
            # Définir le chemin du fichier CSV de sortie
            output_csv = output_dir / f"{pdf_path.stem}.csv"
            
            # Convertir le PDF en images
            self.logger.debug("Conversion du PDF en images...")
            try:
                images = convert_from_path(
                    str(pdf_path),
                    poppler_path=self.poppler_path,
                    dpi=120,
                    thread_count=1,
                    single_file=True
                )
            except Exception as e:
                self.logger.error(f"Erreur lors de la conversion PDF : {str(e)}")
                raise RuntimeError(f"Erreur lors de la conversion du PDF : {str(e)}")
            
            if not images:
                raise ValueError("Aucune page trouvée dans le PDF")

            # Extraire le texte
            all_text = []
            reader = self.get_reader()
            
            self.logger.debug(f"Traitement de {len(images)} pages...")
            for i, img in enumerate(images, 1):
                self.logger.debug(f"Traitement de la page {i}/{len(images)}")
                try:
                    zoomed_img = self.zoom_image(img)
                    img_array = np.array(zoomed_img.convert('L'))
                    result = reader.readtext(img_array)
                    text = ' '.join([t[1] for t in result])
                    all_text.append(text)
                except Exception as e:
                    self.logger.error(f"Erreur lors du traitement de la page {i}: {str(e)}")
                    raise RuntimeError(f"Erreur lors du traitement de la page {i}: {str(e)}")
                finally:
                    del img_array
                    del zoomed_img
                    gc.collect()

            del images
            gc.collect()

            # Créer et sauvegarder le CSV
            try:
                self.logger.debug("Sauvegarde des résultats dans le CSV...")
                df = pd.DataFrame({
                    'page': range(1, len(all_text) + 1),
                    'texte': all_text
                })
                
                df.to_csv(str(output_csv), index=False, encoding='utf-8')
            except Exception as e:
                self.logger.error(f"Erreur lors de la création du CSV : {str(e)}")
                raise RuntimeError(f"Erreur lors de la création du CSV : {str(e)}")

            del df
            del all_text
            gc.collect()

            processing_time = time.time() - start_time
            message = f"Traité en {processing_time:.2f} secondes"
            self.logger.info(f"Traitement terminé : {message}")
            
            # Retourner le chemin relatif du CSV
            return str(output_csv.relative_to(pdf_path.parent.parent)), message

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du fichier {pdf_path}: {str(e)}")
            raise

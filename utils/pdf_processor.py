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
        self.reader = None  # Initialisation tardive
        self.poppler_path = os.getenv('POPPLER_PATH')
        self.logger = app_logger
        self.zoom_factor = 3  # Facteur de zoom

    def get_reader(self):
        if self.reader is None:
            self.reader = easyocr.Reader(['fr'])
        return self.reader

    def zoom_image(self, img):
        """
        Zoomer l'image avec le facteur spécifié
        """
        width, height = img.size
        new_width = int(width * self.zoom_factor)
        new_height = int(height * self.zoom_factor)
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def process_file(self, pdf_path, output_name):
        """
        Traite un seul fichier PDF
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.is_file():
                raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")

            start_time = time.time()
            
            # Convertir le PDF en images avec une résolution plus basse pour économiser la mémoire
            images = convert_from_path(
                str(pdf_path),
                poppler_path=self.poppler_path,
                dpi=150,  # Résolution de base
                thread_count=1  # Limiter l'utilisation des threads
            )
            
            if not images:
                raise ValueError("Aucune page trouvée dans le PDF")

            # Extraire le texte de chaque page
            all_text = []
            reader = self.get_reader()
            
            for img in images:
                # Zoomer l'image
                zoomed_img = self.zoom_image(img)
                
                # Convertir l'image en niveau de gris pour réduire la mémoire
                img_array = np.array(zoomed_img.convert('L'))
                
                # Extraire le texte
                result = reader.readtext(img_array)
                text = ' '.join([t[1] for t in result])
                all_text.append(text)
                
                # Libérer la mémoire
                del img_array
                del zoomed_img
                gc.collect()

            # Libérer la mémoire des images
            del images
            gc.collect()

            # Créer le DataFrame
            df = pd.DataFrame({
                'page': range(1, len(all_text) + 1),
                'texte': all_text
            })

            # Créer le fichier CSV
            csv_path = pdf_path.parent / f"{output_name}.csv"
            df.to_csv(str(csv_path), index=False, encoding='utf-8')

            # Libérer la mémoire
            del df
            del all_text
            gc.collect()

            processing_time = time.time() - start_time
            message = f"Traité en {processing_time:.2f} secondes"
            
            return str(csv_path), message

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du fichier {pdf_path}: {str(e)}")
            raise

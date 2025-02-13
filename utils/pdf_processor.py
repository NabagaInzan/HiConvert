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
            pdf_path = Path(pdf_path)
            if not pdf_path.is_file():
                raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")

            start_time = time.time()
            
            # Créer le dossier de sortie s'il n'existe pas
            output_dir = pdf_path.parent / 'results'
            output_dir.mkdir(exist_ok=True)
            
            # Définir le chemin du fichier CSV de sortie
            output_csv = output_dir / f"{pdf_path.stem}.csv"
            
            # Traiter les pages une par une
            all_text = []
            reader = self.get_reader()
            
            # Convertir et traiter une page à la fois
            images = convert_from_path(
                str(pdf_path),
                poppler_path=self.poppler_path,
                dpi=120,  # Réduit de 150 à 120
                thread_count=1,
                single_file=True
            )
            
            if not images:
                raise ValueError("Aucune page trouvée dans le PDF")

            for i, img in enumerate(images, 1):
                # Traiter une seule page
                zoomed_img = self.zoom_image(img)
                img_array = np.array(zoomed_img.convert('L'))
                result = reader.readtext(img_array)
                text = ' '.join([t[1] for t in result])
                all_text.append(text)
                
                # Libérer la mémoire immédiatement
                del img
                del img_array
                del zoomed_img
                del result
                gc.collect()
                
                # Sauvegarder progressivement dans le CSV
                if i % 5 == 0 or i == len(images):
                    df = pd.DataFrame({
                        'page': range(len(all_text) - len(all_text)%5 + 1, len(all_text) + 1),
                        'texte': all_text[-5:]
                    })
                    mode = 'a' if i > 5 else 'w'
                    df.to_csv(str(output_csv), mode=mode, header=(mode=='w'), index=False, encoding='utf-8')
                    del df
                    gc.collect()

            processing_time = time.time() - start_time
            message = f"Traité en {processing_time:.2f} secondes"
            
            # Retourner le chemin relatif du CSV
            return str(output_csv.relative_to(pdf_path.parent.parent)), message

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du fichier {pdf_path}: {str(e)}")
            raise

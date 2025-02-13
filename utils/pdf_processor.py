import os
import time
import pandas as pd
from pdf2image import convert_from_path
import easyocr
import numpy as np
import re
from .logger import app_logger
from pathlib import Path

class PDFProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['fr'])
        self.poppler_path = os.getenv('POPPLER_PATH')
        self.logger = app_logger

    def process_file(self, pdf_path, output_name):
        """
        Traite un seul fichier PDF
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.is_file():
                raise FileNotFoundError(f"Le fichier {pdf_path} n'existe pas")

            start_time = time.time()
            
            # Convertir le PDF en images
            images = convert_from_path(str(pdf_path), poppler_path=self.poppler_path)
            
            if not images:
                raise ValueError("Aucune page trouvée dans le PDF")

            # Extraire le texte de chaque page
            all_text = []
            for img in images:
                result = self.reader.readtext(np.array(img))
                text = ' '.join([t[1] for t in result])
                all_text.append(text)

            # Créer le DataFrame
            df = pd.DataFrame({
                'page': range(1, len(all_text) + 1),
                'texte': all_text
            })

            # Créer le fichier CSV
            csv_path = pdf_path.parent / f"{output_name}.csv"
            df.to_csv(str(csv_path), index=False, encoding='utf-8')

            processing_time = time.time() - start_time
            message = f"Traité en {processing_time:.2f} secondes"
            
            return str(csv_path), message

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du fichier {pdf_path}: {str(e)}")
            raise

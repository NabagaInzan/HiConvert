import os
import cv2
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import easyocr
import logging
import torch
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.reader = easyocr.Reader(['fr'])
        
    def process_pdf(self, pdf_path):
        """
        Traite un fichier PDF et extrait le texte en utilisant EasyOCR.
        Retourne le chemin du fichier CSV généré.
        """
        try:
            logger.info(f"Début du traitement du fichier PDF: {pdf_path}")
            
            # Convertir le PDF en images
            images = convert_from_path(pdf_path)
            logger.info(f"PDF converti en {len(images)} images")
            
            numbers = []
            
            for i, image in enumerate(images):
                # Convertir l'image PIL en tableau numpy
                image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Extraire le texte
                results = self.reader.readtext(image_np)
                logger.info(f"Page {i+1}: {len(results)} zones de texte détectées")
                
                # Extraction des nombres
                for result in results:
                    text = result[1]
                    extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
                    valid_numbers = [float(num.replace(',', '.')) for num in extracted_numbers if float(num.replace(',', '.')) > 100000]
                    numbers.extend(valid_numbers)
                    for num in valid_numbers:
                        logger.info(f"Nombre extrait: {num} (confiance: {result[2]:.2f}, page: {i+1})")
            
            # Diviser la liste en coordonnées X et Y
            X = numbers[::2]  # Nombres pairs (0, 2, 4, ...)
            Y = numbers[1::2]  # Nombres impairs (1, 3, 5, ...)
            
            # Créer un DataFrame avec les coordonnées
            df = pd.DataFrame(list(zip(X, Y)), columns=['X', 'Y'])
            
            # Générer le nom du fichier CSV (même nom que le PDF)
            csv_path = os.path.splitext(pdf_path)[0] + '.csv'
            
            # Sauvegarder en CSV
            df.to_csv(csv_path, index=False, sep=';')
            
            logger.info(f"Fichier CSV créé : {csv_path} avec {len(X)} paires de coordonnées")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du PDF: {str(e)}")
            raise

    def extract_coordinates(self, pdf_path):
        """
        Extrait les coordonnées X et Y d'un fichier PDF.
        Retourne une liste de dictionnaires avec les coordonnées.
        """
        try:
            logger.info(f"Extraction des coordonnées depuis: {pdf_path}")
            
            # Utiliser la méthode process_pdf existante
            numbers = []
            images = convert_from_path(pdf_path)
            
            for i, image in enumerate(images):
                # Convertir l'image PIL en tableau numpy
                image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Extraire le texte
                results = self.reader.readtext(image_np)
                
                # Extraction des nombres
                for result in results:
                    text = result[1]
                    extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
                    valid_numbers = [float(num.replace(',', '.')) for num in extracted_numbers if float(num.replace(',', '.')) > 100000]
                    numbers.extend(valid_numbers)
            
            # Diviser la liste en coordonnées X et Y
            coordinates = []
            for i in range(0, len(numbers)-1, 2):
                coordinates.append({
                    'X': numbers[i],
                    'Y': numbers[i+1]
                })
            
            logger.info(f"Extraction terminée. {len(coordinates)} paires de coordonnées trouvées.")
            return coordinates
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des coordonnées: {str(e)}")
            raise

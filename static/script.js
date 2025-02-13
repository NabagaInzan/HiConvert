document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('processForm');
    const progressArea = document.getElementById('progressArea');
    const progressBar = document.querySelector('.progress-bar');
    const processingStatus = document.getElementById('processingStatus');
    const resultsArea = document.getElementById('resultsArea');
    const resultsContent = document.getElementById('resultsContent');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const fileInput = document.getElementById('pdfFiles');
        const files = fileInput.files;
        
        if (files.length === 0) {
            alert('Veuillez sélectionner au moins un fichier PDF.');
            return;
        }

        // Créer un FormData pour l'upload
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files[]', files[i]);
        }

        // Afficher la barre de progression
        progressArea.classList.remove('d-none');
        progressBar.style.width = '0%';
        processingStatus.textContent = 'Upload des fichiers en cours...';

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                progressBar.style.width = '100%';
                processingStatus.textContent = 'Traitement terminé !';
                
                // Afficher les résultats
                resultsArea.classList.remove('d-none');
                if (result.results && result.results.length > 0) {
                    const resultsList = result.results.map(r => `
                        <div class="alert alert-success">
                            <strong>${r.file}</strong>
                            <p>${r.message}</p>
                            ${r.csv_path ? `<a href="/download/${encodeURIComponent(r.csv_path)}" class="btn btn-primary btn-sm">Télécharger CSV</a>` : ''}
                        </div>
                    `).join('');
                    resultsContent.innerHTML = resultsList;
                } else {
                    resultsContent.innerHTML = `<div class="alert alert-info">${result.message}</div>`;
                }
            } else {
                throw new Error(result.error || 'Une erreur est survenue');
            }
        } catch (error) {
            progressBar.classList.add('bg-danger');
            processingStatus.textContent = `Erreur: ${error.message}`;
            console.error('Erreur:', error);
        }
    });
});

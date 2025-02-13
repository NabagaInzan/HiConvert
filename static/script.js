document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('processForm');
    const progressArea = document.getElementById('progressArea');
    const progressBar = document.querySelector('.progress-bar');
    const processingStatus = document.getElementById('processingStatus');
    const resultsArea = document.getElementById('resultsArea');
    const resultsContent = document.getElementById('resultsContent');
    const fileInput = document.getElementById('pdfFiles');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const files = fileInput.files;
        if (files.length === 0) {
            alert('Veuillez sélectionner au moins un fichier PDF.');
            return;
        }

        // Vérifier que tous les fichiers sont des PDF
        for (let file of files) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                alert(`Le fichier ${file.name} n'est pas un PDF`);
                return;
            }
        }

        // Créer un FormData pour l'upload
        const formData = new FormData();
        for (let file of files) {
            formData.append('files[]', file);
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

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("La réponse du serveur n'est pas au format JSON");
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Afficher les résultats
            resultsArea.classList.remove('d-none');
            if (data.results && data.results.length > 0) {
                const resultsList = data.results.map(r => `
                    <div class="alert alert-success">
                        <strong>${r.file}</strong>
                        <p>${r.message}</p>
                        ${r.csv_path ? `<a href="/download/${encodeURIComponent(r.csv_path)}" class="btn btn-primary btn-sm">Télécharger CSV</a>` : ''}
                    </div>
                `).join('');
                resultsContent.innerHTML = resultsList;
            } else {
                resultsContent.innerHTML = `<div class="alert alert-info">${data.message}</div>`;
            }
        } catch (error) {
            progressBar.classList.add('bg-danger');
            processingStatus.textContent = `Erreur: ${error.message}`;
            console.error('Erreur:', error);
        } finally {
            progressBar.style.width = '100%';
            processingStatus.textContent = 'Traitement terminé !';
        }
    });
});

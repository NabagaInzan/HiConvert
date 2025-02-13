document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const submitButton = document.getElementById('submit-button');
    const progressDiv = document.getElementById('progress');
    const resultDiv = document.getElementById('result');
    const dropZone = document.getElementById('drop-zone');

    // Mettre à jour le texte pour indiquer que seuls les fichiers plan.pdf sont acceptés
    dropZone.textContent = 'Glissez vos fichiers plan.pdf ici ou cliquez pour sélectionner';

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);

    function preventDefaults (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('highlight');
    }

    function unhighlight(e) {
        dropZone.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        updateFileCount();
    }

    fileInput.addEventListener('change', updateFileCount);

    function updateFileCount() {
        const files = fileInput.files;
        const planFiles = Array.from(files).filter(file => file.name.toLowerCase().includes('plan'));
        const totalFiles = files.length;
        const planCount = planFiles.length;

        if (totalFiles > 0) {
            if (planCount > 0) {
                dropZone.innerHTML = `${planCount} fichier(s) plan.pdf sélectionné(s)<br><small>${totalFiles - planCount} autres fichiers seront ignorés</small>`;
            } else {
                dropZone.innerHTML = `Attention : Aucun fichier plan.pdf sélectionné<br><small>${totalFiles} fichier(s) seront ignorés</small>`;
            }
        } else {
            dropZone.textContent = 'Glissez vos fichiers plan.pdf ici ou cliquez pour sélectionner';
        }
    }

    form.onsubmit = async function(e) {
        e.preventDefault();
        
        const files = fileInput.files;
        if (files.length === 0) {
            showError("Veuillez sélectionner au moins un fichier PDF");
            return;
        }

        // Vérifier s'il y a au moins un fichier plan.pdf
        const planFiles = Array.from(files).filter(file => 
            file.name.toLowerCase().includes('plan') && file.name.toLowerCase().endsWith('.pdf')
        );

        if (planFiles.length === 0) {
            showError("Aucun fichier plan.pdf trouvé parmi les fichiers sélectionnés");
            return;
        }

        submitButton.disabled = true;
        progressDiv.style.display = 'block';
        progressDiv.innerHTML = 'Traitement en cours...';
        resultDiv.innerHTML = '';

        const formData = new FormData();
        for (let file of files) {
            formData.append('files[]', file);
        }

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            let data;
            const contentType = response.headers.get("content-type");
            
            try {
                // Essayer de parser la réponse comme JSON
                data = await response.json();
            } catch (e) {
                // Si ce n'est pas du JSON, lire le texte brut
                const text = await response.text();
                console.error('Réponse non-JSON reçue:', text);
                throw new Error("Le serveur a renvoyé une réponse invalide. Veuillez réessayer.");
            }

            if (!response.ok) {
                throw new Error(data.error || `Erreur HTTP: ${response.status}`);
            }

            if (data.error) {
                throw new Error(data.error);
            }

            showSuccess(data);
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message || "Une erreur est survenue lors du traitement");
        } finally {
            submitButton.disabled = false;
            progressDiv.style.display = 'none';
            fileInput.value = '';
            updateFileCount();
        }
    };

    function showError(message) {
        resultDiv.innerHTML = `<div class="error">${message}</div>`;
        progressDiv.style.display = 'none';
    }

    function showSuccess(data) {
        let html = '<div class="success">';
        html += `<p>${data.message}</p>`;
        if (data.results && data.results.length > 0) {
            html += '<ul>';
            data.results.forEach(result => {
                html += '<li>';
                html += `<strong>${result.file}</strong>: ${result.message}`;
                if (result.csv_path) {
                    const encodedPath = result.csv_path.split('/').map(part => encodeURIComponent(part)).join('/');
                    html += ` <a href="/download/${encodedPath}" class="download-link">Télécharger CSV</a>`;
                }
                html += '</li>';
            });
            html += '</ul>';
        }
        html += '</div>';
        resultDiv.innerHTML = html;
    }
});

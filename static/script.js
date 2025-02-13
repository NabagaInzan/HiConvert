document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const submitButton = document.getElementById('submit-button');
    const progressDiv = document.getElementById('progress');
    const resultDiv = document.getElementById('result');
    const dropZone = document.getElementById('drop-zone');

    dropZone.textContent = 'Glissez vos fichiers plan.pdf ici ou cliquez pour sélectionner';

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
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
        const planFiles = Array.from(files).filter(file => 
            file.name.toLowerCase().includes('plan') && file.name.toLowerCase().endsWith('.pdf')
        );
        if (files.length > 0) {
            if (planFiles.length > 0) {
                dropZone.innerHTML = `${planFiles.length} fichier(s) plan.pdf sélectionné(s)<br><small>${files.length - planFiles.length} autres fichiers seront ignorés</small>`;
            } else {
                dropZone.innerHTML = `Attention : Aucun fichier plan.pdf sélectionné<br><small>${files.length} fichier(s) seront ignorés</small>`;
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
                headers: {
                    'Accept': 'application/json'
                },
                body: formData
            });

            let data;
            try {
                data = await response.json();
            } catch (e) {
                console.error('Erreur lors du parsing JSON:', e);
                const text = await response.text();
                console.error('Réponse brute:', text);
                throw new Error("Erreur lors de la lecture de la réponse du serveur");
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

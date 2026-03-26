document.addEventListener('DOMContentLoaded', () => {
    // ---- Elements ----
    const navItems = document.querySelectorAll('.nav-links li');
    const tabContents = document.querySelectorAll('.tab-content');
    const loadingOverlay = document.getElementById('loading');

    // ---- Tab Switching ----
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            item.classList.add('active');
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }

            if(tabId === 'dashboard') {
                loadDashboard();
            }
        });
    });

    // ---- Loading Overlay Helpers ----
    const showLoading = (text = 'Analyzing medical data...') => {
        if (!loadingOverlay) return;
        const p = loadingOverlay.querySelector('p');
        if(p) p.textContent = text;
        loadingOverlay.style.display = 'flex';
    };
    
    const hideLoading = () => {
        if (!loadingOverlay) return;
        loadingOverlay.style.display = 'none';
    };

    // ---- Dashboard (Timeline) ----
    const loadDashboard = async () => {
        const timelineContainer = document.getElementById('timeline-container');
        if (!timelineContainer) return;
        
        try {
            const res = await fetch('/api/prescriptions');
            const data = await res.json();
            if(data.prescriptions) {
                timelineContainer.innerHTML = '';
                if(data.prescriptions.length === 0) {
                    timelineContainer.innerHTML = '<p>No prescriptions found. Scan one to get started!</p>';
                    return;
                }
                data.prescriptions.forEach(p => {
                    const div = document.createElement('div');
                    div.className = 'timeline-item';
                    
                    let medsHtml = '';
                    if (Array.isArray(p.extracted_data)) {
                        medsHtml = p.extracted_data.map(med => {
                            if(med.error) return `<li>${med.error}</li>`;
                            return `<li><strong>${med.medicine_name || 'Unknown'}</strong> - ${med.dosage || 'N/A'} | ${med.frequency || 'N/A'} | ${med.duration || 'N/A'}</li>`;
                        }).join('');
                    } else if (p.extracted_data && p.extracted_data.error) {
                        medsHtml = `<li>${p.extracted_data.error}</li>`;
                    }

                    div.innerHTML = `
                        <div class="date">${p.date}</div>
                        <div class="content">
                            <h4>Prescription #${p.id}</h4>
                            <ul>${medsHtml}</ul>
                        </div>
                    `;
                    timelineContainer.appendChild(div);
                });
            }
        } catch(e) {
            console.error('Error loading dashboard:', e);
            timelineContainer.innerHTML = '<p>Error loading prescription history.</p>';
        }
    };

    // Load dashboard initially
    loadDashboard();

    // ---- Scanner ----
    const uploadArea = document.getElementById('upload-area');
    const prescriptionUpload = document.getElementById('prescription-upload');
    const analysisResults = document.getElementById('analysis-results');
    const medicinesList = document.getElementById('medicines-list');

    if (uploadArea && prescriptionUpload) {
        uploadArea.addEventListener('click', () => prescriptionUpload.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#4f46e5';
        });
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.2)';
            if(e.dataTransfer.files && e.dataTransfer.files[0]) {
                handlePrescriptionUpload(e.dataTransfer.files[0]);
            }
        });
        prescriptionUpload.addEventListener('change', (e) => {
            if(e.target.files && e.target.files[0]) {
                handlePrescriptionUpload(e.target.files[0]);
            }
        });
    }

    const handlePrescriptionUpload = (file) => {
        if (!medicinesList || !analysisResults) return;
        
        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64Data = e.target.result;
            showLoading('Analyzing prescription image...');
            try {
                const res = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: base64Data,
                        image_type: file.type
                    })
                });
                const data = await res.json();
                hideLoading();
                
                if(data.error) {
                    alert('Error: ' + data.error);
                } else if(data.medicines) {
                    medicinesList.innerHTML = '';
                    let medsArray = Array.isArray(data.medicines) ? data.medicines : [data.medicines];
                    
                    medsArray.forEach(med => {
                        if(med.error) {
                            medicinesList.innerHTML += `<div class="card error"><p>${med.error}</p></div>`;
                        } else {
                            medicinesList.innerHTML += `
                                <div class="card medicine-card" style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(255, 255, 255, 0.1);">
                                    <h4 style="margin-top:0; color:#4f46e5;"><i class="fa-solid fa-pills"></i> ${med.medicine_name || 'Unknown'}</h4>
                                    <p><strong>Dosage:</strong> ${med.dosage || 'N/A'}</p>
                                    <p><strong>Frequency:</strong> ${med.frequency || 'N/A'}</p>
                                    <p><strong>Duration:</strong> ${med.duration || 'N/A'}</p>
                                </div>
                            `;
                        }
                    });
                    analysisResults.style.display = 'block';
                    loadDashboard(); // Refresh timeline
                }
            } catch(error) {
                hideLoading();
                alert('An error occurred during scanning.');
                console.error(error);
            }
        };
        reader.readAsDataURL(file);
    };

    // ---- Symptom Checker ----
    const predictBtn = document.getElementById('predict-btn');
    const symptomInput = document.getElementById('symptom-input');
    const diseasePrediction = document.getElementById('disease-prediction');

    if (predictBtn && symptomInput) {
        predictBtn.addEventListener('click', async () => {
            const text = symptomInput.value.trim();
            if(!text) return;
            
            const symptoms = text.split(',').map(s => s.trim()).filter(s => s);
            
            showLoading('Analyzing symptoms...');
            try {
                const res = await fetch('/api/predict-disease', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symptoms })
                });
                const data = await res.json();
                hideLoading();
                
                diseasePrediction.style.display = 'block';
                diseasePrediction.innerHTML = `
                    <h3>Predicted Condition: <span class="highlight" style="color:#4f46e5;">${data.disease}</span></h3>
                    <p><strong>Recommendations:</strong></p>
                    <p>${data.recommendations || 'No recommendations available.'}</p>
                `;
            } catch(error) {
                hideLoading();
                alert('Failed to predict disease.');
                console.error(error);
            }
        });
    }

    // ---- Pharmacy Intel ----
    const searchMedBtn = document.getElementById('search-med-btn');
    const medicineSearch = document.getElementById('medicine-search');
    const medInfoResult = document.getElementById('med-info-result');

    if (searchMedBtn && medicineSearch) {
        searchMedBtn.addEventListener('click', async () => {
            const medicine = medicineSearch.value.trim();
            if(!medicine) return;
            
            showLoading('Fetching medicine info...');
            try {
                const [infoRes, altRes] = await Promise.all([
                    fetch('/api/medicine-info', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ medicine })
                    }),
                    fetch('/api/alternative', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ medicine })
                    })
                ]);
                
                const infoData = await infoRes.json();
                const altData = await altRes.json();
                hideLoading();
                
                let html = '';
                if(infoData.error) {
                    html += `<p class="error" style="color: #ef4444;">${infoData.error}</p>`;
                } else {
                    html += `
                        <h4 style="color: #4f46e5;">${infoData.medicine_name || medicine}</h4>
                        <p><strong>Formula:</strong> ${infoData.chemical_formula || 'Unknown'}</p>
                        <p><strong>Purpose:</strong> ${infoData.purpose || 'Unknown'}</p>
                        <p><strong>Dosage:</strong> ${infoData.dosage_guidelines || 'Unknown'}</p>
                        <p><strong>Side Effects:</strong> ${(infoData.side_effects || []).join(', ')}</p>
                    `;
                }
                
                if(altData.alternatives && altData.alternatives.length > 0) {
                    html += `<div class="alternatives mt-3" style="margin-top: 15px;">
                        <strong>Alternatives:</strong>
                        <ul style="padding-left: 20px;">${altData.alternatives.map(a => `<li>${a}</li>`).join('')}</ul>
                    </div>`;
                }
                
                medInfoResult.innerHTML = html;
                medInfoResult.style.padding = '15px';
                medInfoResult.style.marginTop = '15px';
                medInfoResult.style.background = 'rgba(255,255,255,0.05)';
                medInfoResult.style.borderRadius = '8px';
            } catch(error) {
                hideLoading();
                alert('Server error fetching medicine info.');
                console.error(error);
            }
        });
    }

    const checkInteractionBtn = document.getElementById('check-interaction-btn');
    const interactionInput = document.getElementById('interaction-input');
    const interactionResult = document.getElementById('interaction-result');

    if (checkInteractionBtn && interactionInput) {
        checkInteractionBtn.addEventListener('click', async () => {
            const text = interactionInput.value.trim();
            if(!text) return;
            
            const medicines = text.split(',').map(m => m.trim()).filter(m => m);
            if(medicines.length < 2) {
                alert('Please enter at least 2 medicines separated by a comma.');
                return;
            }
            
            showLoading('Checking interactions...');
            try {
                const res = await fetch('/api/interactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ medicines })
                });
                const data = await res.json();
                hideLoading();
                
                interactionResult.innerHTML = `<p>${data.interactions || data.error}</p>`;
                interactionResult.style.padding = '15px';
                interactionResult.style.marginTop = '15px';
                interactionResult.style.background = 'rgba(255,255,255,0.05)';
                interactionResult.style.borderRadius = '8px';
            } catch(error) {
                hideLoading();
                alert('Failed to check interactions.');
                console.error(error);
            }
        });
    }

    // ---- Chat ----
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const chatMessages = document.getElementById('chat-messages');

    const appendMessage = (text, sender) => {
        if (!chatMessages) return;
        const div = document.createElement('div');
        div.className = `message ${sender}`;
        
        // Match CSS classes/structure implicitly
        div.style.display = 'flex';
        div.style.gap = '15px';
        div.style.marginBottom = '20px';
        if (sender === 'bot') {
            div.style.flexDirection = 'row';
        } else {
            div.style.flexDirection = 'row-reverse';
        }

        const icon = sender === 'bot' ? '<i class="fa-solid fa-robot"></i>' : '<i class="fa-solid fa-user"></i>';
        const bg = sender === 'bot' ? 'rgba(79, 70, 229, 0.2)' : '#4f46e5';
        
        div.innerHTML = `
            <div class="avatar" style="width: 40px; height: 40px; background: rgba(255,255,255,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center;">${icon}</div>
            <div class="bubble" style="background: ${bg}; padding: 12px 18px; border-radius: 12px; max-width: 70%;">${text}</div>
        `;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const sendMessage = async () => {
        if (!chatInput) return;
        const text = chatInput.value.trim();
        if(!text) return;
        
        appendMessage(text, 'user');
        chatInput.value = '';
        
        // Add fake typing element
        const loadingId = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.className = 'message bot';
        div.id = loadingId;
        div.style.display = 'flex';
        div.style.gap = '15px';
        div.style.marginBottom = '20px';
        div.innerHTML = `
            <div class="avatar" style="width: 40px; height: 40px; background: rgba(255,255,255,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center;"><i class="fa-solid fa-robot"></i></div>
            <div class="bubble" style="background: rgba(79, 70, 229, 0.2); padding: 12px 18px; border-radius: 12px; max-width: 70%;">Thinking...</div>
        `;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            
            const typingEl = document.getElementById(loadingId);
            if(typingEl) chatMessages.removeChild(typingEl);
            
            if(data.reply) {
                appendMessage(data.reply, 'bot');
            } else if(data.error) {
                appendMessage('Sorry, an error occurred: ' + data.error, 'bot');
            }
        } catch(error) {
            const typingEl = document.getElementById(loadingId);
            if(typingEl) chatMessages.removeChild(typingEl);
            appendMessage('Network error communicating with Copilot.', 'bot');
            console.error(error);
        }
    };

    if (sendChatBtn && chatInput) {
        sendChatBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if(e.key === 'Enter') sendMessage();
        });
    }

});

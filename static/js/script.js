document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const fileUpload = document.getElementById('fileUpload');
    const uploadLabel = document.getElementById('uploadLabel');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const newChatBtn = document.getElementById('newChatBtn');
    const historyList = document.getElementById('historyList');
    const optionsMenu = document.getElementById('optionsMenu');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const saveToHistoryBtn = document.getElementById('saveToHistoryBtn');
    const mainContent = document.querySelector('.main-content');
    const overlay = document.createElement('div');
    
    overlay.className = 'overlay';
    document.body.appendChild(overlay);

    let currentSummary = null;
    let currentJargon = null;
    let currentFileName = '';
    let currentSummaryContent = '';

    loadHistory();

    // Sidebar toggle
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        mainContent.classList.toggle('sidebar-open');
        overlay.classList.toggle('active');
    });

    overlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        mainContent.classList.remove('sidebar-open');
        overlay.classList.remove('active');
    });

    // New chat button
    newChatBtn.addEventListener('click', () => {
        clearChat();
        hideOptionsMenu();
    });

    fileUpload.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        currentFileName = file.name;
        addMessage(`Processing: ${file.name}`, true);
        
        uploadLabel.innerHTML = '<div class="spinner"></div> Processing...';
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/summarize', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Processing failed');
            
            const data = await response.json();
            currentSummary = data.summary;
            currentJargon = data.jargon;
            
            // Add summary
            const summaryContent = currentSummary.join('<br><br>');
            currentSummaryContent = `<strong>Summary</strong><br><br>${summaryContent}`;
            const summaryId = addMessage(summaryContent, false, 'Summary');
            
            // Add options toggle to the summary tile
            addOptionsToggle(summaryId);
            
            if (Object.keys(currentJargon).length) {
                const jargonText = Object.entries(currentJargon)
                    .map(([term, meaning]) => 
                        `<span class="jargon-term">${term}</span>: ${meaning}`
                    ).join('<br>');
                addMessage(jargonText, false, 'Legal Terms Explained');
            }
            
        } catch (error) {
            addMessage('Error processing document: ' + error.message, false);
        } finally {
            uploadLabel.innerHTML = '<i class="fas fa-file-upload"></i><span>Upload Document</span>';
            fileUpload.value = '';
        }
    });
    
    function addMessage(text, isUser, title = '') {
        const messageDiv = document.createElement('div');
        const messageId = 'message-' + Date.now();
        messageDiv.id = messageId;
        messageDiv.className = isUser ? 'message user-message' : 'summary-tile';
        
        if (title) {
            messageDiv.innerHTML = `<strong>${title}</strong><br><br>${text}`;
        } else {
            messageDiv.textContent = text;
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageId;
    }
    
    function addOptionsToggle(messageId) {
        const messageDiv = document.getElementById(messageId);
        const optionsBtn = document.createElement('button');
        optionsBtn.className = 'options-toggle';
        optionsBtn.innerHTML = '<i class="fas fa-ellipsis-h"></i>';
        
        optionsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            showOptionsMenu(e.target, messageId);
        });
        
        messageDiv.appendChild(optionsBtn);
    }
    
    function showOptionsMenu(target, messageId) {
        const rect = target.getBoundingClientRect();
        optionsMenu.style.top = (rect.bottom + window.scrollY) + 'px';
        optionsMenu.style.left = (rect.left + window.scrollX - 150) + 'px';
        optionsMenu.classList.add('active');
        
        // Set up event listeners
        downloadPdfBtn.onclick = () => downloadAsPdf(messageId);
        saveToHistoryBtn.onclick = () => saveToHistory(messageId);
        
        // Hide menu when clicking elsewhere
        const clickHandler = (e) => {
            if (!optionsMenu.contains(e.target) && e.target !== target) {
                optionsMenu.classList.remove('active');
                document.removeEventListener('click', clickHandler);
            }
        };
        
        setTimeout(() => {
            document.addEventListener('click', clickHandler);
        }, 0);
    }
    
    function hideOptionsMenu() {
        optionsMenu.classList.remove('active');
    }
    
    function downloadAsPdf(messageId) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        const messageDiv = document.getElementById(messageId);
        const title = messageDiv.querySelector('strong').textContent;
        const content = messageDiv.textContent.replace(title, '').trim();
        
        doc.setFontSize(18);
        doc.text(title, 10, 10);
        doc.setFontSize(12);
        
        const splitText = doc.splitTextToSize(content, 180);
        doc.text(splitText, 10, 20);
        
        const fileName = `summary_${formatDateForFilename(new Date())}.pdf`;
        doc.save(fileName);
        hideOptionsMenu();
    }
    
    async function saveToHistory(messageId) {
        // Check if user is logged in
        const isGuest = document.body.querySelector('[data-guest]') !== null;
        if (isGuest) {
            alert('Please log in to save summaries to your history.');
            hideOptionsMenu();
            return;
        }
        
        const messageDiv = document.getElementById(messageId);
        const title = currentFileName || `Summary ${formatDate(new Date())}`;
        
        try {
            const response = await fetch('/save_summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    filename: currentFileName,
                    content: currentSummaryContent,
                    summary: currentSummary,
                    jargon: currentJargon
                })
            });
            
            if (!response.ok) throw new Error('Failed to save summary');
            
            const result = await response.json();
            
            // Reload history to show the new item
            loadHistory();
            hideOptionsMenu();
            
            alert('Summary saved to history!');
        } catch (error) {
            console.error('Error saving summary:', error);
            alert('Failed to save summary. Please try again.');
        }
    }
    
    async function loadHistory() {
        // Check if user is logged in
        const isGuest = document.body.querySelector('[data-guest]') !== null;
        if (isGuest) {
            historyList.innerHTML = '<div class="history-empty">Log in to save and view history</div>';
            return;
        }
        
        try {
            const response = await fetch('/get_summaries');
            if (!response.ok) throw new Error('Failed to load history');
            
            const summaries = await response.json();
            historyList.innerHTML = '';
            
            if (summaries.length === 0) {
                historyList.innerHTML = '<div class="history-empty">No saved summaries yet</div>';
                return;
            }
            
            summaries.forEach(item => {
                addHistoryItem(item);
            });
        } catch (error) {
            console.error('Error loading history:', error);
            historyList.innerHTML = '<div class="history-empty">Error loading history</div>';
        }
    }
    
    function addHistoryItem(item) {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.dataset.id = item._id;
        
        historyItem.innerHTML = `
            <div class="history-item-title">${item.title}</div>
            <div class="history-item-filename">${item.filename}</div>
            <div class="history-item-date">${item.created_at}</div>
        `;
        
        historyItem.addEventListener('click', () => {
            loadHistoryItem(item._id);
        });
        
        historyList.appendChild(historyItem);
    }
    
    async function loadHistoryItem(summaryId) {
        try {
            const response = await fetch(`/get_summary/${summaryId}`);
            if (!response.ok) throw new Error('Failed to load summary');
            
            const item = await response.json();
            clearChat();
            
            // Add the saved summary
            const summaryIdElement = addMessage(item.content.replace('<strong>Summary</strong><br><br>', ''), false, 'Summary');
            addOptionsToggle(summaryIdElement);
            
            if (item.jargon && Object.keys(item.jargon).length > 0) {
                const jargonText = Object.entries(item.jargon)
                    .map(([term, meaning]) => 
                        `<span class="jargon-term">${term}</span>: ${meaning}`
                    ).join('<br>');
                addMessage(jargonText, false, 'Legal Terms Explained');
            }
            
            // Update current data
            currentSummary = item.summary;
            currentJargon = item.jargon;
            currentFileName = item.filename;
            currentSummaryContent = item.content;
            
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                mainContent.classList.remove('sidebar-open');
                overlay.classList.remove('active');
            }
        } catch (error) {
            console.error('Error loading summary:', error);
            alert('Failed to load summary. Please try again.');
        }
    }
    
    function clearChat() {
        chatContainer.innerHTML = '';
        addMessage('Upload a legal document (PDF, DOCX, TXT, Image) to get a simplified summary and explanation of legal terms.', false);
        
        currentSummary = null;
        currentJargon = null;
        currentFileName = '';
        currentSummaryContent = '';
    }
    
    function formatDate(date) {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    
    function formatDateForFilename(date) {
        return date.toISOString().slice(0, 10) + '_' + date.toTimeString().slice(0, 8).replace(/:/g, '-');
    }


function addHistoryDeleteButton(historyItem, itemId) {
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'history-delete-btn';
    deleteBtn.innerHTML = '<i class="fas fa-ellipsis-v"></i>';
    
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation(); 
        showHistoryOptionsMenu(e.target, itemId);
    });
    
    historyItem.appendChild(deleteBtn);
}


function showHistoryOptionsMenu(target, itemId) {
    let historyOptionsMenu = document.getElementById('historyOptionsMenu');
    if (!historyOptionsMenu) {
        historyOptionsMenu = document.createElement('div');
        historyOptionsMenu.id = 'historyOptionsMenu';
        historyOptionsMenu.className = 'history-options-menu';
        historyOptionsMenu.innerHTML = `
            <button class="history-option-btn delete-history-btn">
                <i class="fas fa-trash"></i> Delete
            </button>
        `;
        document.body.appendChild(historyOptionsMenu);
        
        historyOptionsMenu.querySelector('.delete-history-btn').addEventListener('click', () => {
            deleteHistoryItem(itemId);
            historyOptionsMenu.classList.remove('active');
        });
    }
    
    const rect = target.getBoundingClientRect();
    historyOptionsMenu.style.top = (rect.bottom + window.scrollY) + 'px';
    historyOptionsMenu.style.left = (rect.left + window.scrollX - 100) + 'px';
    historyOptionsMenu.classList.add('active');
    
    const clickHandler = (e) => {
        if (!historyOptionsMenu.contains(e.target) && e.target !== target) {
            historyOptionsMenu.classList.remove('active');
            document.removeEventListener('click', clickHandler);
        }
    };
    
    setTimeout(() => {
        document.addEventListener('click', clickHandler);
    }, 0);
}


async function deleteHistoryItem(itemId) {
    try {
        const response = await fetch(`/delete_summary/${itemId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to delete summary');
        
        const historyItem = document.querySelector(`.history-item[data-id="${itemId}"]`);
        if (historyItem) {
            historyItem.remove();
        }
        
        if (document.querySelectorAll('.history-item').length === 0) {
            historyList.innerHTML = '<div class="history-empty">No saved summaries yet</div>';
        }
    } catch (error) {
        console.error('Error deleting summary:', error);
        alert('Failed to delete summary. Please try again.');
    }
}

function addHistoryItem(item) {
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.dataset.id = item._id;
    
    historyItem.innerHTML = `
        <div class="history-item-content">
            <div class="history-item-title">${item.title}</div>
            <div class="history-item-filename">${item.filename}</div>
            <div class="history-item-date">${item.created_at}</div>
        </div>
    `;
    
    historyItem.addEventListener('click', (e) => {
        if (!e.target.closest('.history-delete-btn')) {
            loadHistoryItem(item._id);
        }
    });
    
    addHistoryDeleteButton(historyItem, item._id);
    
    historyList.appendChild(historyItem);
}






});


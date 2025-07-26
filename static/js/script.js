document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const fileUpload = document.getElementById('fileUpload');
    const uploadLabel = document.getElementById('uploadLabel');
    
    fileUpload.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        addMessage(file.name, true);
        
        // Show loading state
        uploadLabel.innerHTML = '<div class="spinner"></div> Processing...';
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/summarize', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Processing failed');
            
            const { summary, jargon } = await response.json();
            
            // Add summary
            addMessage(summary.join('<br><br>'), false, 'Summary');
            
            // Add jargon explanations
            if (Object.keys(jargon).length) {
                const jargonText = Object.entries(jargon)
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
        messageDiv.className = `message ${isUser ? 'user-message' : ''}`;
        
        if (title) {
            messageDiv.innerHTML = `<strong>${title}</strong><br><br>${text}`;
        } else {
            messageDiv.textContent = text;
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});
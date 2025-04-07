document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const chatHistory = [];
    
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const message = chatInput.value.trim();
            
            if (message) {
                // Add user message to chat
                addMessageToChat('user', message);
                
                // Clear input
                chatInput.value = '';
                
                // Show typing indicator
                showTypingIndicator();
                
                // Send message to API
                sendMessageToAPI(message);
            }
        });
    }
    
    function addMessageToChat(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `${sender}-message`, 'mb-3', 'p-3');
        
        // Different styling based on sender
        if (sender === 'user') {
            messageElement.classList.add('bg-primary', 'text-white', 'rounded-3', 'ms-auto');
            chatHistory.push({
                "role": "user",
                "content": message
            });
        } else {
            messageElement.classList.add('bg-light', 'rounded-3');
            chatHistory.push({
                "role": "assistant",
                "content": message
            });
        }
        
        messageElement.style.maxWidth = '75%';
        messageElement.innerHTML = `<p class="mb-0">${message}</p>`;
        
        chatMessages.appendChild(messageElement);
        
        // Scroll to bottom of chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function showTypingIndicator() {
        const typingElement = document.createElement('div');
        typingElement.id = 'typing-indicator';
        typingElement.classList.add('chat-message', 'assistant-message', 'bg-light', 'rounded-3', 'mb-3', 'p-3');
        typingElement.style.maxWidth = '75%';
        typingElement.innerHTML = `
            <div class="typing-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
            </div>
        `;
        
        chatMessages.appendChild(typingElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    function sendMessageToAPI(message) {
        fetch('/dashboard/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: chatHistory
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove typing indicator
            removeTypingIndicator();
            
            // Add AI response to chat
            if (data.response) {
                addMessageToChat('assistant', data.response);
            } else if (data.error) {
                addMessageToChat('assistant', `Error: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Remove typing indicator
            removeTypingIndicator();
            
            // Add error message to chat
            addMessageToChat('assistant', 'Sorry, there was an error processing your request. Please try again later.');
        });
    }
    
    // Add initial greeting message
    if (chatMessages && chatMessages.children.length === 0) {
        setTimeout(() => {
            addMessageToChat('assistant', 'Hello! I\'m your AI assistant. How can I help you with your studies today?');
        }, 500);
    }
});

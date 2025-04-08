document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    const chatForm = document.getElementById('chat-form');
    console.log('Chat form element:', chatForm);
    
    const chatInput = document.getElementById('chat-input');
    console.log('Chat input element:', chatInput);
    
    const chatMessages = document.getElementById('chat-messages');
    console.log('Chat messages element:', chatMessages);
    
    const chatHistory = [];
    let currentModel = 'openai'; // Default model
    
    // Handle AI model selection
    const openAiBtn = document.getElementById('openai-model-btn');
    const grokBtn = document.getElementById('grok-model-btn');
    
    if (openAiBtn && grokBtn) {
        openAiBtn.addEventListener('click', function() {
            setActiveModel('openai');
        });
        
        grokBtn.addEventListener('click', function() {
            setActiveModel('grok');
        });
    }
    
    function setActiveModel(model) {
        currentModel = model;
        const modelBadge = document.getElementById('current-model-badge');
        
        // Update UI for buttons
        if (model === 'openai') {
            openAiBtn.classList.add('active');
            grokBtn.classList.remove('active');
            if (modelBadge) {
                modelBadge.textContent = 'Currently using: OpenAI (GPT-4o)';
                modelBadge.className = 'badge bg-primary mb-2';
            }
            // Add animation for transition
            chatMessages.classList.add('fade-transition');
            setTimeout(() => {
                addMessageToChat('assistant', 'Switched to OpenAI model. How can I help you with your studies?');
                chatMessages.classList.remove('fade-transition');
            }, 300);
        } else {
            grokBtn.classList.add('active');
            openAiBtn.classList.remove('active');
            if (modelBadge) {
                modelBadge.textContent = 'Currently using: xAI (Grok-2)';
                modelBadge.className = 'badge bg-warning text-dark mb-2';
            }
            // Add animation for transition
            chatMessages.classList.add('fade-transition');
            setTimeout(() => {
                addMessageToChat('assistant', 'Switched to Grok model. I\'m ready to assist with your educational questions!');
                chatMessages.classList.remove('fade-transition');
            }, 300);
        }
    }
    
    // Add fade transition style
    const style = document.createElement('style');
    style.textContent = `
        .fade-transition {
            opacity: 0.5;
            transition: opacity 0.3s ease-in-out;
        }
        .active {
            background-color: #0d6efd !important;
            color: white !important;
        }
    `;
    document.head.appendChild(style);
    
    // Handle suggestion buttons
    const suggestionButtons = document.querySelectorAll('.suggestion-btn');
    if (suggestionButtons) {
        suggestionButtons.forEach(button => {
            button.addEventListener('click', function() {
                const suggestion = this.getAttribute('data-suggestion');
                if (suggestion) {
                    chatInput.value = suggestion;
                    // Focus the input
                    chatInput.focus();
                }
            });
        });
    }
    
    if (chatForm) {
        console.log('Adding submit event listener to chat form');
        chatForm.addEventListener('submit', function(e) {
            console.log('Form submitted!');
            e.preventDefault();
            
            const message = chatInput.value.trim();
            console.log('Message:', message);
            
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
    } else {
        console.error('Chat form element not found!');
    }
    
    // Add a click event listener to the send button as a fallback
    const sendButton = document.getElementById('send-button');
    if (sendButton) {
        console.log('Adding click event listener to send button');
        sendButton.addEventListener('click', function() {
            console.log('Send button clicked!');
            
            const message = chatInput.value.trim();
            console.log('Message:', message);
            
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
    } else {
        console.error('Send button element not found!');
    }
    
    function addMessageToChat(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', `${sender}-message`, 'mb-3', 'p-3');
        
        // Different styling based on sender
        if (sender === 'user') {
            messageElement.classList.add('bg-primary', 'text-white', 'rounded-3', 'ms-auto');
            chatHistory.push({
                "user": message
            });
        } else {
            messageElement.classList.add('bg-light', 'rounded-3');
            chatHistory.push({
                "assistant": message
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
        
        // Add typing animation with CSS
        const style = document.createElement('style');
        style.textContent = `
            .typing-dots {
                display: flex;
                align-items: center;
                justify-content: flex-start;
            }
            .dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                margin-right: 4px;
                background-color: #333;
                border-radius: 50%;
                opacity: 0.6;
                animation: dot-pulse 1.5s infinite ease-in-out;
            }
            .dot:nth-child(1) { animation-delay: 0s; }
            .dot:nth-child(2) { animation-delay: 0.2s; }
            .dot:nth-child(3) { animation-delay: 0.4s; }
            
            @keyframes dot-pulse {
                0%, 100% { transform: scale(1); opacity: 0.6; }
                50% { transform: scale(1.5); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
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
                history: chatHistory,
                model: currentModel
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
            addMessageToChat('assistant', 'Hello! I\'m your SmartEdu AI educational assistant. I can help with study techniques, subject-specific questions, exam preparation, or educational resources. What would you like help with today?');
        }, 500);
    }
});

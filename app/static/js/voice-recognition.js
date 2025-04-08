/**
 * Voice-to-text functionality for educational chat assistant
 * Uses the Web Speech API for voice recognition
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Voice recognition script loaded');
    const voiceButton = document.getElementById('voice-button');
    const voiceStatus = document.getElementById('voice-status');
    const voiceStatusText = document.getElementById('voice-status-text');
    const chatInput = document.getElementById('chat-input');
    
    // Check if browser supports the Web Speech API
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.error('Speech recognition not supported in this browser');
        if (voiceButton) {
            voiceButton.classList.add('disabled');
            voiceButton.title = 'Voice input not supported in this browser';
            
            // Add click handler to show error message
            voiceButton.addEventListener('click', function() {
                // Create toast notification
                const toastContainer = document.createElement('div');
                toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
                toastContainer.style.zIndex = '5';
                
                const toastContent = `
                    <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                        <div class="toast-header bg-danger text-white">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            <strong class="me-auto">Voice Input Not Available</strong>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                        </div>
                        <div class="toast-body">
                            Your browser doesn't support the Web Speech API required for voice input. 
                            Please try using a different browser like Chrome, Edge, or Safari.
                        </div>
                    </div>
                `;
                
                toastContainer.innerHTML = toastContent;
                document.body.appendChild(toastContainer);
                
                // Add close button functionality
                const closeButton = toastContainer.querySelector('.btn-close');
                if (closeButton) {
                    closeButton.addEventListener('click', function() {
                        document.body.removeChild(toastContainer);
                    });
                    
                    // Auto-remove after 5 seconds
                    setTimeout(() => {
                        if (document.body.contains(toastContainer)) {
                            document.body.removeChild(toastContainer);
                        }
                    }, 5000);
                }
            });
        }
        return;
    }
    
    // Create speech recognition object
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    // Configure speech recognition
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US'; // Default language
    
    let isRecording = false;
    
    // Handle voice button click
    if (voiceButton) {
        voiceButton.addEventListener('click', function() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
    }
    
    // Start voice recording
    function startRecording() {
        try {
            recognition.start();
            isRecording = true;
            
            // Update UI
            if (voiceButton) {
                voiceButton.classList.add('active');
                voiceButton.title = 'Stop voice input (Alt+V)';
            }
            
            if (voiceStatus) {
                voiceStatus.classList.remove('d-none');
                voiceStatusText.textContent = 'Listening...';
            }
            
            console.log('Voice recording started');
        } catch (error) {
            console.error('Error starting voice recognition:', error);
        }
    }
    
    // Stop voice recording
    function stopRecording() {
        try {
            recognition.stop();
            isRecording = false;
            
            // Update UI
            if (voiceButton) {
                voiceButton.classList.remove('active');
                voiceButton.title = 'Use voice input (Alt+V)';
            }
            
            if (voiceStatus) {
                voiceStatus.classList.add('d-none');
                // Reset the status text for next time
                if (voiceStatusText) {
                    voiceStatusText.textContent = 'Listening...';
                }
            }
            
            console.log('Voice recording stopped');
        } catch (error) {
            console.error('Error stopping voice recognition:', error);
        }
    }
    
    // Handle results from voice recognition
    recognition.onresult = function(event) {
        const results = event.results;
        let finalTranscript = '';
        let interimTranscript = '';
        
        // Loop through all results to handle multiple recognition segments
        for (let i = 0; i < results.length; i++) {
            const transcript = results[i][0].transcript;
            
            if (results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Use final transcript if available, otherwise use interim
        const transcriptToUse = finalTranscript || interimTranscript;
        
        if (chatInput && transcriptToUse) {
            const currentText = chatInput.value.trim();
            
            // Only add spaces between words if needed
            if (currentText && !currentText.endsWith(' ')) {
                chatInput.value = currentText + ' ' + transcriptToUse;
            } else {
                chatInput.value = currentText + transcriptToUse;
            }
            
            // Focus the input
            chatInput.focus();
            
            if (voiceStatusText) {
                if (finalTranscript) {
                    voiceStatusText.textContent = 'Recognized: ' + finalTranscript;
                } else {
                    voiceStatusText.textContent = 'Hearing: ' + interimTranscript;
                }
            }
            
            console.log('Voice recognized:', transcriptToUse);
        }
    };
    
    // Handle errors
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        
        if (voiceStatusText) {
            voiceStatusText.textContent = 'Error: ' + event.error;
        }
        
        // Stop recording on error
        stopRecording();
    };
    
    // Handle end of recognition
    recognition.onend = function() {
        console.log('Voice recognition ended');
        
        // Auto-stop when recognition ends
        stopRecording();
    };
    
    // Add keyboard shortcut (Alt+V) for voice input
    document.addEventListener('keydown', function(e) {
        // Alt+V key combination (or Option+V on Mac)
        if (e.altKey && e.code === 'KeyV') {
            e.preventDefault();
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
    });
    
    // Expose functions to global scope for debugging
    window.startVoiceRecognition = startRecording;
    window.stopVoiceRecognition = stopRecording;
});
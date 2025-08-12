/**
 * Main Application Logic
 * Handles chat interface, user interactions, and results display
 */

class CarbonCalculatorApp {
    constructor() {
        this.sessionManager = null;
        this.isTyping = false;
        this.init();
    }

    /**
     * Initialize the application
     */
    async init() {
        // Initialize session manager
        this.sessionManager = new SessionManager();
        
        // Wait for session to be ready
        await this.waitForSession();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Display welcome message
        this.displayWelcomeMessage();
        
        console.log('Carbon Calculator App initialized');
    }

    /**
     * Wait for session to be ready
     */
    async waitForSession() {
        // Give session manager time to initialize
        let attempts = 0;
        const maxAttempts = 10;
        
        while (!this.sessionManager.getSessionData() && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (attempts >= maxAttempts) {
            console.warn('Session initialization took longer than expected');
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Chat input
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        
        // Enable send button when input has content
        userInput.addEventListener('input', () => {
            const hasContent = userInput.value.trim().length > 0;
            sendButton.disabled = !hasContent;
        });
        
        // Send message on Enter key
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !sendButton.disabled) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Send button click
        sendButton.addEventListener('click', () => {
            if (!sendButton.disabled) {
                this.sendMessage();
            }
        });
        
        // Error toast close
        const toastClose = document.getElementById('toast-close');
        if (toastClose) {
            toastClose.addEventListener('click', () => {
                document.getElementById('error-toast').style.display = 'none';
            });
        }
        
        // View Recommendations button
        const viewRecommendationsButton = document.getElementById('view-recommendations-button');
        if (viewRecommendationsButton) {
            viewRecommendationsButton.addEventListener('click', () => {
                window.location.href = 'recommendations.html';
            });
        }
        
        // Mobile keyboard handling
        this.setupMobileKeyboardHandling(userInput);
    }

    /**
     * Setup mobile keyboard handling to prevent input from being covered
     */
    setupMobileKeyboardHandling(userInput) {
        // Handle input focus with chat scrolling
        userInput.addEventListener('focusin', () => {
            // Scroll chat to bottom
            setTimeout(() => {
                const chatMessages = document.querySelector('.chat-messages');
                if (chatMessages) {
                    chatMessages.scrollTo({
                        top: chatMessages.scrollHeight,
                        behavior: 'smooth'
                    });
                }
            }, 300);
        });
        
        // Visual Viewport API for accurate keyboard detection (no positioning, just class management)
        if (window.visualViewport) {
            let initialHeight = window.visualViewport.height;
            
            window.visualViewport.addEventListener('resize', () => {
                const currentHeight = window.visualViewport.height;
                
                // If viewport is smaller than initial, keyboard is probably open
                if (currentHeight < initialHeight) {
                    document.body.classList.add('keyboard-detected');
                    
                    // Give the reclaimed space to chat-container (exact progress bar dimensions)
                    const chatContainer = document.querySelector('.chat-container');
                    if (chatContainer) {
                        // Progress bar: 1rem top + 0.5rem bottom + 8px bar + 8px margin + 1px border
                        chatContainer.style.maxHeight = `calc(100vh - 200px + 1.5rem + 17px)`;
                    }
                } else {
                    document.body.classList.remove('keyboard-detected');
                    
                    // Reset chat container max height
                    const chatContainer = document.querySelector('.chat-container');
                    if (chatContainer) {
                        chatContainer.style.maxHeight = 'calc(100vh - 200px)';
                    }
                }
            });
        }
    }


    /**
     * Display welcome message
     */
    displayWelcomeMessage() {
        // Get current session data to determine what to ask
        const sessionData = this.sessionManager.getSessionData();
        
        if (!sessionData || (!sessionData.user_name && sessionData.progress_pct === 0)) {
            // New user - ask for name
            const welcomeMessage = `Hello! I'm Carbon Coach, your personal carbon footprint calculator and advisory tool. 

I'll guide you through a short conversation to calculate your carbon emissions and provide personalized recommendations for reducing your environmental impact, including relevant government incentives and tax programs.

This should take about 5-10 minutes. Let's start by getting to know you better.

What's your name?`;
            
            this.addMessage('assistant', welcomeMessage);
        } else if (sessionData.progress_pct >= 100 || !sessionData.next_missing_field) {
            // Session complete - show completion message and trigger results
            const greeting = sessionData.user_name ? `Welcome back, ${sessionData.user_name}!` : 'Welcome back!';
            const completionMessage = `${greeting} You've completed your carbon footprint assessment. Let me show you your results.`;
            this.addMessage('assistant', completionMessage);
            
            // Trigger results display
            setTimeout(() => {
                this.calculateAndShowResults();
            }, 1000);
        } else {
            // Returning user with incomplete assessment - generate dynamic message
            const dynamicMessage = this.generateDynamicMessage(sessionData);
            this.addMessage('assistant', dynamicMessage);
        }
    }

    /**
     * Generate dynamic welcome message based on session status
     */
    generateDynamicMessage(sessionData) {
        const greeting = sessionData.user_name ? `Welcome back, ${sessionData.user_name}!` : 'Welcome back!';
        const field = sessionData.next_missing_field;
        const section = sessionData.current_section;
        
        if (!field) {
            return `${greeting} Let's continue with your carbon footprint assessment.`;
        }
        
        return this.getMessageForField(section, field, greeting);
    }

    /**
     * Get message for a specific field
     */
    getMessageForField(section, field, greeting) {
        const sectionMessages = {
            'introduction': {
                'name': `${greeting} Let's start by getting to know you better.\n\nWhat's your name?`,
                'city': `${greeting} I'd like to know your location to provide accurate recommendations.\n\nWhat city are you in?`,
                'state': `${greeting} Thanks! What state are you in?`,
                'household_size': `${greeting} How many people live in your household?`,
                'housing_type': `${greeting} What type of housing do you live in? (house, apartment, condo)`
            },
            'home_energy': {
                'square_footage': `${greeting} Now let's talk about your home energy usage.\n\nWhat's the square footage of your home?`,
                'monthly_electricity': `${greeting} What's your average monthly electricity bill?`,
                'heating_type': `${greeting} What type of heating do you have? (natural gas, electric, oil, heat pump)`,
                'heating_bill': `${greeting} What's your average monthly heating bill?`,
                'solar_panels': `${greeting} Do you have solar panels installed?`
            },
            'transportation': {
                'vehicle_year': `${greeting} Let's discuss your transportation.\n\nWhat year is your primary vehicle?`,
                'vehicle_make': `${greeting} What make is your vehicle?`,
                'vehicle_model': `${greeting} What model is your vehicle?`,
                'annual_miles': `${greeting} How many miles do you drive per year?`,
                'domestic_flights': `${greeting} How many domestic flights do you take per year?`,
                'international_flights': `${greeting} How many international flights do you take per year?`
            },
            'consumption': {
                'diet_type': `${greeting} Finally, let's talk about your consumption habits.\n\nHow would you describe your diet? (vegan, vegetarian, light meat eater, heavy meat eater)`,
                'shopping_frequency': `${greeting} How often do you shop online? (low, moderate, high, very high)`
            }
        };
        
        const sectionMap = sectionMessages[section];
        if (sectionMap && sectionMap[field]) {
            return sectionMap[field];
        }
        
        // Fallback
        return `${greeting} Let's continue with your carbon footprint assessment.`;
    }

    /**
     * Send user message
     */
    async sendMessage() {
        const userInput = document.getElementById('user-input');
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Clear input and disable send button
        userInput.value = '';
        document.getElementById('send-button').disabled = true;
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send message to backend
            const response = await this.sessionManager.sendMessage(message);
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            if (response.success) {
                // If name was collected in this response, update all user message avatars
                if (response.data_collected && response.data_collected.name) {
                    this.updateAllUserMessageAvatars(response.data_collected.name);
                }
                
                // Add assistant response
                this.addMessage('assistant', response.message);
                
                // Check if we need to calculate footprint
                if (response.section_complete && response.current_section === 'results') {
                    await this.calculateAndShowResults();
                }
            } else {
                // Show error message
                this.addMessage('assistant', response.message || 'Sorry, I encountered an error. Please try again.');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered a technical error. Please try again.');
        }
        
        // Focus back on input
        userInput.focus();
    }

    /**
     * Add message to chat
     */
    addMessage(sender, content) {
        const chatMessages = document.getElementById('chat-messages');
        const timestamp = new Date();
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (sender === 'user') {
            avatar.textContent = this.getUserInitials();
        } else {
            // Assistant avatar - use carbon coach image
            const avatarImg = document.createElement('img');
            avatarImg.src = 'carbon_coach_avatar.png';
            avatarImg.alt = 'Carbon Coach';
            avatarImg.style.width = '100%';
            avatarImg.style.height = '100%';
            avatarImg.style.borderRadius = '50%';
            avatarImg.style.objectFit = 'cover';
            avatar.appendChild(avatarImg);
        }
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Format message content (preserve line breaks)
        const formattedContent = content.replace(/\n/g, '<br>');
        messageContent.innerHTML = formattedContent;
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = this.sessionManager.formatTimestamp(timestamp);
        
        messageElement.appendChild(avatar);
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-wrapper';
        contentWrapper.appendChild(messageContent);
        contentWrapper.appendChild(messageTime);
        messageElement.appendChild(contentWrapper);
        
        chatMessages.appendChild(messageElement);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.style.display = 'block';
            this.isTyping = true;
        }
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.style.display = 'none';
            this.isTyping = false;
        }
    }

    /**
     * Calculate and show results
     */
    async calculateAndShowResults() {
        // Show loading overlay
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        
        try {
            // Calculate footprint
            const results = await this.sessionManager.calculateFootprint();
            
            if (results.success) {
                // Hide chat interface and show results
                this.showResults(results);
            } else {
                throw new Error('Calculation failed');
            }
            
        } catch (error) {
            console.error('Error calculating footprint:', error);
            this.addMessage('assistant', 'Sorry, I had trouble calculating your carbon footprint. Please try again or contact support.');
        } finally {
            // Hide loading overlay
            if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
            }
        }
    }

    /**
     * Show results section
     */
    showResults(results) {
        // Hide chat container
        document.querySelector('.chat-container').style.display = 'none';
        
        // Show results section
        const resultsSection = document.getElementById('results-section');
        resultsSection.style.display = 'block';
        
        // Populate results
        this.populateResults(results);
        
        // Update progress to 100%
        this.sessionManager.updateProgress(100);
    }

    /**
     * Populate results section with data
     */
    populateResults(results) {
        const footprintSummary = document.getElementById('footprint-summary');
        const recommendationsSection = document.getElementById('recommendations-section');
        
        const footprint = results.footprint;
        const estimatedTotal = footprint.total_tons_co2 * 1.25;
        
        // Create footprint summary HTML with estimated total first
        const summaryHTML = `
            <div class="footprint-total">
                <div class="total-emissions">${estimatedTotal.toFixed(1)}</div>
                <div class="emissions-unit">estimated tons CO₂ per year</div>
                <div class="emissions-comparison">
                    <div class="comparison-item">
                        ${(estimatedTotal / footprint.us_average_tons * 100).toFixed(0)}% of the US average (${footprint.us_average_tons} tons)
                    </div>
                    <div class="comparison-item paris-target">
                        ${(estimatedTotal / footprint.paris_target_tons * 100).toFixed(0)}% of Paris Climate target (~${footprint.paris_target_tons} tons)
                    </div>
                </div>
            </div>
            <div class="emissions-breakdown">
                <div class="breakdown-item">
                    <div class="breakdown-value">${(footprint.home_emissions / 1000).toFixed(1)}</div>
                    <div class="breakdown-label">Home Energy</div>
                </div>
                <div class="breakdown-item">
                    <div class="breakdown-value">${(footprint.transport_emissions / 1000).toFixed(1)}</div>
                    <div class="breakdown-label">Transportation</div>
                </div>
                <div class="breakdown-item">
                    <div class="breakdown-value">${(footprint.consumption_emissions / 1000).toFixed(1)}</div>
                    <div class="breakdown-label">Consumption</div>
                </div>
            </div>
            <div class="footprint-explanation">
                <p><strong>How we calculate:</strong> Your responses cover about 80% of typical emissions factors. We use a multiplier to account for other smaller factors such as public services and infrastructure, healthcare, entertainment, and the supply chains of the products you buy.</p>
            </div>
        `;
        
        footprintSummary.innerHTML = summaryHTML;
        
        // Recommendations section removed - now handled by dedicated recommendations page
        recommendationsSection.style.display = 'none';
        
        // Show the sticky recommendations button
        const stickyRecommendationsContainer = document.getElementById('sticky-recommendations-container');
        if (stickyRecommendationsContainer) {
            stickyRecommendationsContainer.style.display = 'flex';
        }
    }

    /**
     * Get user initials from session data
     */
    getUserInitials() {
        // Try to get initials from session manager
        if (this.sessionManager && this.sessionManager.sessionData) {
            return this.sessionManager.sessionData.user_initials || '';
        }
        return '';
    }

    /**
     * Generate initials from a name (max 2 characters)
     */
    generateInitials(name) {
        if (!name || typeof name !== 'string') {
            return '';
        }
        
        name = name.trim();
        if (!name) {
            return '';
        }
        
        // Split by spaces and filter out empty strings
        const words = name.split(' ').filter(word => word.trim());
        
        if (!words.length) {
            return '';
        } else if (words.length === 1) {
            // Single word - take first character
            return words[0][0].toUpperCase();
        } else {
            // Multiple words - take first letter of first and last word
            return (words[0][0] + words[words.length - 1][0]).toUpperCase();
        }
    }

    /**
     * Update all user message avatars with the new initials
     */
    updateAllUserMessageAvatars(name) {
        const chatMessages = document.getElementById('chat-messages');
        const userMessages = chatMessages.querySelectorAll('.message.user .message-avatar');
        const initials = this.generateInitials(name);
        
        userMessages.forEach(avatar => {
            avatar.textContent = initials;
        });
    }

}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CarbonCalculatorApp();
});
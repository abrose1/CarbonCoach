/**
 * Session Management
 * Handles session creation, persistence, and data management
 */

class SessionManager {
    constructor() {
        this.sessionId = null;
        this.sessionData = null;
        this.apiBaseUrl = 'http://localhost:5001/api';
        this.init();
    }

    /**
     * Initialize session manager
     */
    init() {
        // Get or create session ID
        this.sessionId = this.getOrCreateSessionId();
        
        // Initialize session with backend
        this.initializeSession();
    }

    /**
     * Get existing session ID from localStorage or create new one
     */
    getOrCreateSessionId() {
        let sessionId = localStorage.getItem('carbon_calculator_session_id');
        
        if (!sessionId) {
            // Generate new UUID-like session ID
            sessionId = this.generateSessionId();
            localStorage.setItem('carbon_calculator_session_id', sessionId);
        }
        
        return sessionId;
    }

    /**
     * Generate a new session ID (UUID v4 format)
     */
    generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Initialize session with backend
     */
    async initializeSession() {
        try {
            // Get lightweight session status
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}/status`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.sessionData = await response.json();
            
            // Update progress bar
            this.updateProgress(this.sessionData.progress_pct || 0);
            
        } catch (error) {
            console.error('Error initializing session:', error);
            this.handleError('Failed to initialize session. Please refresh the page.');
        }
    }

    /**
     * Get current session data
     */
    getSessionData() {
        return this.sessionData;
    }

    /**
     * Refresh session data from backend to get latest user initials
     */
    async refreshSessionData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.sessionId}/data`);
            if (response.ok) {
                const data = await response.json();
                if (this.sessionData && data.user_initials) {
                    this.sessionData.user_initials = data.user_initials;
                }
            }
        } catch (error) {
            console.error('Error refreshing session data:', error);
        }
    }

    /**
     * Get session ID
     */
    getSessionId() {
        return this.sessionId;
    }

    /**
     * Start a new session (for "New Assessment" functionality)
     */
    startNewSession() {
        // Generate new session ID
        this.sessionId = this.generateSessionId();
        
        // Update localStorage
        localStorage.setItem('carbon_calculator_session_id', this.sessionId);
        
        // Reset session data
        this.sessionData = null;
        
        // Initialize new session with backend
        this.initializeSession();
        
        // Reset progress display
        this.updateProgress(0);
    }

    /**
     * Update session progress
     */
    updateProgress(progressPct) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressFill && progressText) {
            progressFill.style.width = `${progressPct}%`;
            progressText.textContent = `${progressPct}% Complete`;
        }
        
        // Update session data
        if (this.sessionData) {
            this.sessionData.progress_pct = progressPct;
        }
    }

    /**
     * Send message to conversation API
     */
    async sendMessage(message) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/conversation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            // Update progress if provided
            if (result.progress_pct !== undefined) {
                this.updateProgress(result.progress_pct);
            }
            
            // Update session data
            if (this.sessionData) {
                this.sessionData.current_section = result.current_section;
                this.sessionData.progress_pct = result.progress_pct;
            }
            
            // Refresh session data to get updated user initials
            await this.refreshSessionData();
            
            return result;
            
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    /**
     * Calculate carbon footprint
     */
    async calculateFootprint() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
            
        } catch (error) {
            console.error('Error calculating footprint:', error);
            throw error;
        }
    }


    /**
     * Handle errors with user feedback
     */
    handleError(message) {
        console.error('Session error:', message);
        
        const errorToast = document.getElementById('error-toast');
        const toastMessage = document.getElementById('toast-message');
        
        if (errorToast && toastMessage) {
            toastMessage.textContent = message;
            errorToast.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorToast.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /**
     * Check if session is completed
     */
    isCompleted() {
        return this.sessionData && this.sessionData.completed;
    }

    /**
     * Get current section
     */
    getCurrentSection() {
        return this.sessionData ? this.sessionData.current_section : 'introduction';
    }
}

// Export for use in other scripts
window.SessionManager = SessionManager;
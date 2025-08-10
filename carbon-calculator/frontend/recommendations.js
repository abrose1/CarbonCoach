// Recommendations Page JavaScript - Fetch and Display Real Data

document.addEventListener('DOMContentLoaded', function() {
    loadRecommendations();
    setupEventHandlers();
});

async function loadRecommendations() {
    const sessionId = localStorage.getItem('carbon_calculator_session_id');
    
    if (!sessionId) {
        showError("No session found. Please complete the assessment first.");
        return;
    }

    try {
        showLoading();
        
        const response = await fetch(`https://carbonbackend.up.railway.app/api/recommendations/${sessionId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.recommendations) {
            const techRecs = data.recommendations.technology_upgrades || [];
            const lifestyleRecs = data.recommendations.lifestyle_adjustments || [];
            
            if (techRecs.length > 0 || lifestyleRecs.length > 0) {
                displayRecommendations(techRecs, lifestyleRecs);
            } else {
                showNoRecommendations();
            }
        } else {
            showNoRecommendations();
        }
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        showError("Unable to load recommendations. Please try again.");
    }
}

function showLoading() {
    document.getElementById('loading-container').style.display = 'block';
    document.getElementById('error-container').style.display = 'none';
    document.getElementById('recommendations-content').style.display = 'none';
}

function showError(message) {
    document.getElementById('loading-container').style.display = 'none';
    document.getElementById('error-container').style.display = 'block';
    document.getElementById('recommendations-content').style.display = 'none';
    
    const errorContainer = document.getElementById('error-container');
    errorContainer.querySelector('p').textContent = message;
}

function showNoRecommendations() {
    document.getElementById('loading-container').style.display = 'none';
    document.getElementById('error-container').style.display = 'none';
    document.getElementById('recommendations-content').style.display = 'block';
    
    // Show message that no specific recommendations were found
    const techSection = document.getElementById('technology-recommendations');
    techSection.innerHTML = `
        <div class="no-recommendations">
            <p>Great job! Your energy usage appears quite efficient already. Consider exploring additional energy-saving opportunities like LED lighting upgrades or smart thermostats.</p>
        </div>
    `;
    
    document.getElementById('lifestyle-section').style.display = 'none';
}

function displayRecommendations(technologyRecs, lifestyleRecs) {
    document.getElementById('loading-container').style.display = 'none';
    document.getElementById('error-container').style.display = 'none';
    document.getElementById('recommendations-content').style.display = 'block';
    
    // Technology and lifestyle recommendations are now structured objects
    const techRecsAsObjects = technologyRecs.map(rec => ({
        text: rec.recommendation_text,
        category: rec.category,
        priority_score: rec.priority_score,
        co2_savings_kg: rec.co2_savings_kg,
        government_program: rec.government_program
    }));
    
    const lifestyleRecsAsObjects = lifestyleRecs.map(rec => ({
        text: rec.recommendation_text,
        action_type: rec.action_type,
        co2_savings_kg: rec.co2_savings_kg,
        cost_savings: rec.cost_savings
    }));
    
    // Display technology recommendations
    if (techRecsAsObjects.length > 0) {
        displayTechnologyRecommendations(techRecsAsObjects);
        document.getElementById('technology-section').style.display = 'block';
    } else {
        // Show positive message when no technology upgrades are needed
        document.getElementById('technology-section').style.display = 'block';
        document.getElementById('technology-recommendations').innerHTML = `
            <div class="no-recommendations">
                <p>Excellent! Your home appears to be quite energy efficient already. We'll continue to update our recommendations as new technologies and programs become available.</p>
            </div>
        `;
    }
    
    // Display lifestyle recommendations  
    if (lifestyleRecsAsObjects.length > 0) {
        displayLifestyleRecommendations(lifestyleRecsAsObjects);
        document.getElementById('lifestyle-section').style.display = 'block';
    } else {
        document.getElementById('lifestyle-section').style.display = 'none';
    }
    
    // If no recommendations in either category, show a message
    if (techRecsAsObjects.length === 0 && lifestyleRecsAsObjects.length === 0) {
        document.getElementById('technology-section').style.display = 'block';
        document.getElementById('technology-recommendations').innerHTML = `
            <div class="no-recommendations">
                <p>Great job! Your current setup appears quite efficient. We'll continue to update our recommendations as new programs become available.</p>
            </div>
        `;
    }
}

function displayTechnologyRecommendations(recommendations) {
    const container = document.getElementById('technology-recommendations');
    
    // Group recommendations by technology type
    const groupedRecs = groupRecommendationsByType(recommendations);
    
    let html = '';
    
    Object.keys(groupedRecs).forEach((type, index) => {
        const recs = groupedRecs[type];
        const primaryRec = recs[0]; // Use first rec for main display
        const icon = getTechnologyIcon(primaryRec.text);
        const priority = getPriorityLevel(Math.max(...recs.map(r => r.priority_score)));
        const totalCO2Savings = primaryRec.co2_savings_kg || 0; // All recs in group have same CO2 savings
        
        html += `
            <div class="recommendation-card">
                <div class="rec-header">
                    <div class="rec-icon">${icon}</div>
                    <div class="rec-title-area">
                        <h4>${type}</h4>
                        <div class="rec-impact">
                            <span class="co2-savings">Save ~${totalCO2Savings ? Math.round(totalCO2Savings).toLocaleString() : 'TBD'} kg CO₂/year</span>
                            <span class="cost-savings">${getFinancialPillForGroup(recs)}</span>
                        </div>
                    </div>
                    ${priority ? `<div class="rec-priority ${priority.toLowerCase()}">${priority} Impact</div>` : ''}
                </div>
                
                <div class="rec-description">
                    ${getRecommendationDescription(primaryRec)}
                </div>

                ${createGroupedProgramContainer(recs, index)}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayLifestyleRecommendations(recommendations) {
    const container = document.getElementById('lifestyle-recommendations');
    
    let html = '';
    
    recommendations.forEach(rec => {
        const icon = getLifestyleIcon(rec.text);
        
        html += `
            <div class="lifestyle-card">
                <div class="card-header">
                    <div class="lifestyle-icon">${icon}</div>
                    <div class="rec-title-area">
                        <h4>${getStructuredTitle(rec)}</h4>
                        <div class="rec-impact">
                            <span class="co2-savings">Save ~${rec.co2_savings_kg ? Math.round(rec.co2_savings_kg).toLocaleString() : 'TBD'} kg CO₂/year</span>
                            <span class="cost-savings">${rec.cost_savings ? `Save ~$${rec.cost_savings.toLocaleString()}/year` : 'Savings potential calculated'}</span>
                        </div>
                    </div>
                </div>
                <p>${rec.text}</p>
                <div class="lifestyle-tips">
                    <div class="tip">💡 Start with small changes for lasting impact</div>
                    <div class="tip">💡 Track your progress over time</div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}




function groupRecommendationsByType(recommendations) {
    const groups = {};
    
    recommendations.forEach(rec => {
        let type;
        
        // Use the actual category from the diagnostic engine
        switch (rec.category) {
            case 'solar_opportunity':
                type = 'Install Solar Panels';
                break;
            case 'home_heating':
                type = 'Upgrade to Heat Pump';
                break;
            case 'transportation':
                type = 'Switch to Electric Vehicle';
                break;
            case 'home_efficiency':
                type = 'Improve Home Insulation';
                break;
            default:
                // Fallback to text-based detection for any unexpected categories
                const text = rec.text.toLowerCase();
                if (text.includes('solar')) {
                    type = 'Install Solar Panels';
                } else if (text.includes('heat pump')) {
                    type = 'Upgrade to Heat Pump';
                } else if (text.includes('electric vehicle') || text.includes('ev')) {
                    type = 'Switch to Electric Vehicle';
                } else if (text.includes('insulation')) {
                    type = 'Improve Home Insulation';
                } else {
                    type = 'Energy Improvement';
                }
                break;
        }
        
        if (!groups[type]) {
            groups[type] = [];
        }
        groups[type].push(rec);
    });
    
    return groups;
}

function createGroupedProgramContainer(recommendations, index) {
    const programId = `grouped-program-${index}`;
    
    // Get actual government programs from the recommendations
    const programs = [];
    
    recommendations.forEach(rec => {
        if (rec.government_program && !programs.find(p => p.id === rec.government_program.id)) {
            const program = rec.government_program;
            programs.push({
                id: program.id,
                name: program.name,
                type: program.is_federal ? 'Federal' : (program.state ? `${program.state} State` : 'State'),
                benefit: 'Financial incentives available',
                // Include raw financial data for frontend formatting
                incentive_amount: program.incentive_amount,
                percent_of_cost: program.percent_of_cost,
                percent_of_cost_cap: program.percent_of_cost_cap,
                per_unit_rate: program.per_unit_rate,
                per_unit_type: program.per_unit_type,
                description: program.summary || 'Government incentive program to support clean energy adoption.',
                program_type: program.program_type || 'incentive',
                website_url: program.website_url,
                credibility_boost: program.credibility_boost
            });
        }
    });
    
    if (programs.length === 0) {
        return '';
    }
    
    const fundingText = 'View Available Incentives';
    
    return `
        <div class="programs-container">
            <button class="programs-summary-button" data-target="${programId}">
                <span class="funding-total">${fundingText}</span>
                <span class="arrow"></span>
            </button>
            
            <div class="programs-details" id="${programId}">
                <div class="program-tabs">
                    ${programs.map((program, i) => {
                        const shortPill = formatFinancialPillShort(program);
                        const showPill = shortPill && shortPill !== '';
                        return `
                        <button class="program-tab ${i === 0 ? 'active' : ''}" data-program="${programId}-detail-${i}">
                            <span class="program-type">${program.type}</span>
                            <span class="program-name">${program.name}</span>
                            <span class="program-benefit">See details</span>
                            ${showPill ? `<span class="cost-savings">${shortPill}</span>` : ''}
                        </button>
                        `;
                    }).join('')}
                </div>
                
                ${programs.map((program, i) => `
                    <div class="program-details ${i === 0 ? 'active' : ''}" id="${programId}-detail-${i}">
                        <div class="program-summary">
                            <p><strong>${program.name}</strong></p>
                            ${createTruncatedDescription(program.description, programId, i)}
                            <ul>
                                <li>✓ ${program.program_type} program</li>
                                <li>✓ ${program.type} incentive</li>
                                <li>✓ Check eligibility requirements</li>
                                ${program.credibility_boost ? '<li>✓ Well-established program</li>' : ''}
                            </ul>
                            ${program.website_url ? 
                                `<a href="${program.website_url}" target="_blank" class="program-link">Learn more & Apply →</a>` :
                                `<a href="#" class="program-link" onclick="alert('Contact your installer or visit program website for applications')">Learn more & Apply →</a>`
                            }
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function getStructuredTitle(recommendation) {
    // For technology recommendations with DSIRE programs - use program name
    if (recommendation.government_program && recommendation.government_program.name) {
        return recommendation.government_program.name;
    }
    
    // For lifestyle recommendations - use action_type from backend
    if (recommendation.action_type) {
        switch (recommendation.action_type) {
            case 'reduce_flights':
                return 'Reduce Air Travel';
            case 'reduce_international_flights':
                return 'Reduce International Flights';
            case 'reduce_domestic_flights':
                return 'Reduce Domestic Flights';
            case 'drive_less':
                return 'Drive Less Frequently';
            case 'reduce_energy_use':
                return 'Reduce Energy Usage';
            case 'reduce_meat_consumption':
                return 'Reduce Meat Consumption';
            case 'reduce_shopping_frequency':
                return 'Shop Less Frequently';
            default:
                return 'Lifestyle Adjustment';
        }
    }
    
    // Fallback for edge cases
    return 'Lifestyle Adjustment';
}

function getRecommendationDescription(recommendation) {
    // Use the personalized recommendation text from backend
    return recommendation.text || "No recommendation available.";
}

function getTechnologyIcon(text) {
    const lowerText = text.toLowerCase();
    if (lowerText.includes('heat pump') || lowerText.includes('heating')) return '🔥';
    if (lowerText.includes('solar') || lowerText.includes('panel')) return '☀️';
    if (lowerText.includes('electric vehicle') || lowerText.includes('ev') || lowerText.includes('car')) return '🚗';
    if (lowerText.includes('insulation') || lowerText.includes('window')) return '🏠';
    if (lowerText.includes('thermostat') || lowerText.includes('smart')) return '🌡️';
    return '⚡';
}

function getLifestyleIcon(text) {
    const lowerText = text.toLowerCase();
    if (lowerText.includes('flight') || lowerText.includes('travel')) return '✈️';
    if (lowerText.includes('drive') || lowerText.includes('transport')) return '🚗';
    if (lowerText.includes('diet') || lowerText.includes('food')) return '🥗';
    if (lowerText.includes('shop') || lowerText.includes('consumption')) return '🛍️';
    return '🌱';
}

function getPriorityLevel(score) {
    // Score is on 0-100 scale from backend
    // Based on data analysis: 90+ = 11.8%, 80+ = 65.4%, 60+ = 76.4%
    if (score >= 85) return 'High';    // ~65% of recommendations
    if (score >= 60) return 'Medium';  // ~17% of recommendations  
    return ''; // ~14% show no impact label
}

function getFinancialPillForGroup(recommendations) {
    // Get actual government programs from the recommendations
    const programs = recommendations
        .map(rec => rec.government_program)
        .filter(prog => prog);
    
    if (programs.length === 0) {
        return '--'; // No financial data found
    }
    
    if (programs.length === 1) {
        return formatFinancialPillFull(programs[0]); // Single program, use frontend formatting
    }
    
    // Multiple programs - use frontend combined formatting
    return formatCombinedFinancialPill(programs);
}

function setupEventHandlers() {
    // Handle dropdown button clicks
    document.addEventListener('click', function(e) {
        if (e.target.closest('.programs-summary-button')) {
            const button = e.target.closest('.programs-summary-button');
            const targetId = button.getAttribute('data-target');
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                targetSection.classList.toggle('active');
                button.classList.toggle('expanded');
            }
        }
        
        // Handle program tab clicks
        if (e.target.closest('.program-tab')) {
            const tab = e.target.closest('.program-tab');
            const targetId = tab.getAttribute('data-program');
            const container = tab.closest('.programs-container');
            
            // Remove active class from all tabs in this container
            container.querySelectorAll('.program-tab').forEach(t => t.classList.remove('active'));
            
            // Remove active class from all details in this container
            container.querySelectorAll('.program-details').forEach(d => d.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding details
            tab.classList.add('active');
            const targetDetail = document.getElementById(targetId);
            if (targetDetail) {
                targetDetail.classList.add('active');
            }
        }
    });
    
    // Handle retry button
    document.getElementById('retry-button').addEventListener('click', loadRecommendations);
}

// Share functionality
function shareRecommendations() {
    const shareMessage = generateShareMessage();
    const mainSiteUrl = window.location.origin; // Just the main site, not the recommendations page
    
    if (navigator.share) {
        navigator.share({
            title: 'I just used Carbon Coach to calculate my carbon footprint and get personalized recommendations! 🌱',
            text: shareMessage,
            url: mainSiteUrl
        });
    } else {
        // Fallback - copy to clipboard
        const fullMessage = `${shareMessage}\n\nTry it yourself: ${mainSiteUrl}`;
        navigator.clipboard.writeText(fullMessage).then(() => {
            alert('Share message copied to clipboard!');
        }).catch(() => {
            // Final fallback
            alert(`Share this message:\n\n${fullMessage}`);
        });
    }
}

function generateShareMessage() {
    // Get the current recommendation data from the page
    const techCards = document.querySelectorAll('.recommendation-card');
    const lifestyleCards = document.querySelectorAll('.lifestyle-card');
    
    let message = "";
    
    // Add technology recommendations summary
    if (techCards.length > 0) {
        message += `💡 Technology upgrades recommended: ${techCards.length} (`;
        const techTypes = Array.from(techCards).map(card => {
            const title = card.querySelector('h4')?.textContent?.trim();
            return title;
        }).filter(title => title);
        
        if (techTypes.length > 0) {
            message += techTypes.join(', ');
        }
        message += ")\n";
        
        // Count total incentive programs
        const programTabs = document.querySelectorAll('.program-tab');
        if (programTabs.length > 0) {
            message += `💰 Found ${programTabs.length} government incentive programs to help with costs\n`;
        }
    }
    
    // Add lifestyle recommendations summary  
    if (lifestyleCards.length > 0) {
        message += `🌱 Lifestyle adjustments recommended: ${lifestyleCards.length}\n`;
    }
    
    if (techCards.length === 0 && lifestyleCards.length === 0) {
        message += "Great job! My current setup is already quite efficient.\n";
    }
    
    message += "\nCarbon Coach gave me a personalized action plan with government incentives to reduce my environmental impact. Check it out!";
    
    return message;
}

// Financial formatting functions
function formatCurrency(amount) {
    if (!amount) return '';
    
    try {
        const num = parseFloat(amount);
        if (num >= 1000000) {
            return `$${(num / 1000000).toFixed(1)}M`;
        } else if (num >= 1000) {
            return `$${(num / 1000).toFixed(1)}K`;
        } else {
            return `$${num.toFixed(0)}`;
        }
    } catch (e) {
        return String(amount);
    }
}

function formatFinancialPillFull(program) {
    /**
     * Create full financial pill text like "30% of cost" or "$7,500" 
     * (equivalent to backend's format_financial_pill function)
     */
    if (!program) return 'See program details';
    
    const hasAmount = program.incentive_amount !== null && program.incentive_amount !== undefined;
    const hasPercent = program.percent_of_cost !== null && program.percent_of_cost !== undefined;
    const hasPercentCap = program.percent_of_cost_cap !== null && program.percent_of_cost_cap !== undefined;
    const hasPerUnit = program.per_unit_rate !== null && program.per_unit_rate !== undefined;
    
    // No financial data
    if (!hasAmount && !hasPercent && !hasPerUnit) {
        return 'See program details';
    }
    
    const parts = [];
    
    // Add percentage information
    if (hasPercent) {
        if (hasPercentCap) {
            parts.push(`${program.percent_of_cost}% up to ${formatCurrency(program.percent_of_cost_cap)}`);
        } else if (hasAmount) {
            // Amount serves as cap for percentage
            parts.push(`${program.percent_of_cost}% up to ${formatCurrency(program.incentive_amount)}`);
        } else {
            parts.push(`${program.percent_of_cost}% of cost covered by incentives`);
        }
    }
    // Add fixed amount (if not already used as a cap)
    else if (hasAmount) {
        parts.push(formatCurrency(program.incentive_amount) + " of incentives available");
    }
    
    // Add per-unit rate information
    if (hasPerUnit) {
        const rateStr = formatCurrency(program.per_unit_rate);
        // Clean up unit type
        const unitMapping = {
            '$/kWh (4 years)': 'kWh (4 years)',
            '$/kW': 'kW', 
            '$/W': 'W',
            '$/Unit': 'unit',
            '$/ton': 'ton'
        };
        const cleanUnit = unitMapping[program.per_unit_type] || program.per_unit_type;
        parts.push(`${rateStr}/${cleanUnit}+ " of incentives available"`);
    }
    
    return parts.length > 0 ? parts.join(' + ') : 'See program details';
}

function formatFinancialPillShort(program) {
    /**
     * Create short financial pill text like "30%" or "$7.5K" for tabs
     */
    if (!program) return '';
    
    const hasAmount = program.incentive_amount !== null && program.incentive_amount !== undefined;
    const hasPercent = program.percent_of_cost !== null && program.percent_of_cost !== undefined;
    const hasPerUnit = program.per_unit_rate !== null && program.per_unit_rate !== undefined;
    
    // Prioritize percentage if available
    if (hasPercent) {
        return `${program.percent_of_cost}%`;
    }
    
    // Then fixed amount
    if (hasAmount) {
        return formatCurrency(program.incentive_amount);
    }
    
    // Then per-unit with unit type
    if (hasPerUnit) {
        const rateStr = formatCurrency(program.per_unit_rate);
        // Clean up unit type for short display
        const unitMapping = {
            '$/kWh (4 years)': '/kWh',
            '$/kW': '/kW', 
            '$/W': '/W',
            '$/Unit': '/unit',
            '$/ton': '/ton'
        };
        const cleanUnit = unitMapping[program.per_unit_type] || `/${program.per_unit_type}`;
        return `${rateStr}${cleanUnit}`;
    }
    
    return '';
}

function formatCombinedFinancialPill(programs) {
    /**
     * Create combined financial pill for multiple programs
     * (equivalent to backend's format_combined_financial_pill function)
     */
    if (!programs || programs.length === 0) {
        return 'See program details';
    }
    
    if (programs.length === 1) {
        return formatFinancialPillFull(programs[0]);
    }
    
    // Separate programs by financial structure
    const fixedAmounts = [];
    const simplePercentages = [];
    const complexPrograms = [];
    
    for (const program of programs) {
        const hasAmount = program.incentive_amount !== null && program.incentive_amount !== undefined;
        const hasPercent = program.percent_of_cost !== null && program.percent_of_cost !== undefined;
        const hasPercentCap = program.percent_of_cost_cap !== null && program.percent_of_cost_cap !== undefined;
        const hasPerUnit = program.per_unit_rate !== null && program.per_unit_rate !== undefined;
        
        // Simple fixed amount only
        if (hasAmount && !hasPercent && !hasPerUnit) {
            fixedAmounts.push(program.incentive_amount);
        }
        // Simple percentage (ignore caps for combining purposes)
        else if (hasPercent && !hasAmount && !hasPerUnit) {
            simplePercentages.push(program.percent_of_cost);
        }
        // Amount + percentage (treat amount as cap, but allow combining)
        else if (hasAmount && hasPercent && !hasPerUnit && !hasPercentCap) {
            // Only add percentage since amount is typically a cap
            simplePercentages.push(program.percent_of_cost);
        }
        // Everything else is complex
        else {
            complexPrograms.push(program);
        }
    }
    
    // If any complex programs, fall back to count
    if (complexPrograms.length > 0) {
        return `${programs.length} incentive programs available`;
    }
    
    // Combine simple fixed amounts
    if (fixedAmounts.length > 0 && simplePercentages.length === 0) {
        const totalAmount = fixedAmounts.reduce((sum, amt) => sum + amt, 0);
        return formatCurrency(totalAmount) + " of incentives available";
    }
    
    // Combine simple percentages
    if (simplePercentages.length > 0 && fixedAmounts.length === 0) {
        const totalPercent = simplePercentages.reduce((sum, pct) => sum + pct, 0);
        return `${totalPercent}% of cost covered by incentives`;
    }
    
    // Mixed simple types - show both
    if (fixedAmounts.length > 0 && simplePercentages.length > 0) {
        const amountStr = formatCurrency(fixedAmounts.reduce((sum, amt) => sum + amt, 0));
        const percentStr = `${simplePercentages.reduce((sum, pct) => sum + pct, 0)}%`;
        return `${amountStr} + ${percentStr} covered by incentives`;
    }
    
    // Fallback
    return `${programs.length} incentive programs available`;
}

// Mobile truncation functions
function truncateAtWordBoundary(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return { truncated: text, needsTruncation: false };
    }
    
    // Find the last space before maxLength
    let truncateIndex = maxLength;
    while (truncateIndex > 0 && text[truncateIndex] !== ' ') {
        truncateIndex--;
    }
    
    // If no space found, just truncate at maxLength to avoid infinite loop
    if (truncateIndex === 0) {
        truncateIndex = maxLength;
    }
    
    return {
        truncated: text.substring(0, truncateIndex).trim(),
        needsTruncation: true
    };
}

function createTruncatedDescription(description, programId, detailIndex) {
    const { truncated, needsTruncation } = truncateAtWordBoundary(description, 1000);
    
    if (!needsTruncation) {
        return `<div>${description}</div>`;
    }
    
    const toggleId = `${programId}-toggle-${detailIndex}`;
    
    return `
        <!-- Desktop version - always full text -->
        <div class="program-description-desktop">${description}</div>
        
        <!-- Mobile version - truncated with toggle -->
        <div class="mobile-truncate">
            <div class="program-description-truncated" id="${toggleId}-truncated">
                ${truncated}...
                <button class="view-more-btn" onclick="toggleProgramDescription('${toggleId}')" style="color: var(--accent-color); background: none; border: none; text-decoration: underline; cursor: pointer; font-size: inherit; padding: 0; margin-left: 4px;">
                    View more
                </button>
            </div>
            <div class="program-description-full" id="${toggleId}-full" style="display: none;">
                ${description}
                <button class="view-less-btn" onclick="toggleProgramDescription('${toggleId}')" style="color: var(--accent-color); background: none; border: none; text-decoration: underline; cursor: pointer; font-size: inherit; padding: 0; margin-left: 4px;">
                    View less
                </button>
            </div>
        </div>
    `;
}

// Make this function globally available
window.toggleProgramDescription = function(toggleId) {
    const truncated = document.getElementById(`${toggleId}-truncated`);
    const full = document.getElementById(`${toggleId}-full`);
    
    if (truncated && full) {
        if (truncated.style.display === 'none') {
            // Show truncated, hide full
            truncated.style.display = 'block';
            full.style.display = 'none';
        } else {
            // Show full, hide truncated
            truncated.style.display = 'none';
            full.style.display = 'block';
        }
    }
}

// Global function for "New Assessment" button
function startNewAssessment() {
    // Get the session manager instance (it should be available globally)
    const sessionManager = new SessionManager();
    
    // Start a new session
    sessionManager.startNewSession();
    
    // Redirect to main page
    window.location.href = '/';
}
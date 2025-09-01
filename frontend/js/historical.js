class HistoricalInterface {
    constructor() {
        this.historicalEndpoint = '/api/historical';
        this.currentFilters = {};
        this.currentPage = 1;
        this.perPage = 20;
        this.init();
    }

    init() {
        this.setupHistoricalNavigation();
        this.setupTimelineView();
        this.loadHistoricalContent();
    }

    setupHistoricalNavigation() {
        // Add historical navigation to header
        const header = document.querySelector('header');
        if (!header) return;

        // Create historical toggle button
        const historicalButton = document.createElement('button');
        historicalButton.innerHTML = '🏛️ Historical';
        historicalButton.className = 'historical-toggle-button';
        historicalButton.style.cssText = `
            background: var(--warning);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
            font-weight: 500;
            margin-top: 15px;
            margin-left: 10px;
        `;

        header.appendChild(historicalButton);

        // Create historical panel
        const historicalPanel = document.createElement('div');
        historicalPanel.className = 'historical-panel';
        historicalPanel.style.cssText = `
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            display: none;
            box-shadow: var(--shadow);
        `;

        historicalPanel.innerHTML = `
            <h3 style="margin-top: 0; color: var(--dark);">Historical Data Explorer</h3>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Administration</label>
                <select id="administration-filter" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <option value="">All Administrations</option>
                    <option value="Obama">Obama</option>
                    <option value="Trump">Trump</option>
                    <option value="Biden">Biden</option>
                </select>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Date Range</label>
                <div style="display: flex; gap: 10px;">
                    <input type="date" id="historical-date-start" style="flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <input type="date" id="historical-date-end" style="flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Topic</label>
                <select id="topic-filter" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <option value="">All Topics</option>
                    <option value="Healthcare">Healthcare</option>
                    <option value="Economy">Economy</option>
                    <option value="Foreign Policy">Foreign Policy</option>
                    <option value="Environment">Environment</option>
                </select>
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="clear-historical-filters" style="padding: 8px 16px; border: 1px solid #e2e8f0; border-radius: 4px; background: white; cursor: pointer;">
                    Clear
                </button>
                <button id="apply-historical-filters" style="padding: 8px 16px; border: 1px solid var(--warning); border-radius: 4px; background: var(--warning); color: white; cursor: pointer;">
                    Apply Filters
                </button>
            </div>
        `;

        header.appendChild(historicalPanel);

        // Add event listeners
        historicalButton.addEventListener('click', () => {
            historicalPanel.style.display = historicalPanel.style.display === 'none' ? 'block' : 'none';
            this.loadHistoricalContent();
        });

        // Filter event listeners
        document.getElementById('administration-filter').addEventListener('change', () => {
            this.updateHistoricalFilters();
        });

        document.getElementById('historical-date-start').addEventListener('change', () => {
            this.updateHistoricalFilters();
        });

        document.getElementById('historical-date-end').addEventListener('change', () => {
            this.updateHistoricalFilters();
        });

        document.getElementById('topic-filter').addEventListener('change', () => {
            this.updateHistoricalFilters();
        });

        document.getElementById('apply-historical-filters').addEventListener('click', () => {
            this.loadHistoricalContent();
        });

        document.getElementById('clear-historical-filters').addEventListener('click', () => {
            this.clearHistoricalFilters();
        });
    }

    updateHistoricalFilters() {
        // Update administration filter
        const administration = document.getElementById('administration-filter').value;
        if (administration) {
            this.currentFilters.administration = administration;
        } else {
            delete this.currentFilters.administration;
        }

        // Update date filters
        const startDate = document.getElementById('historical-date-start').value;
        const endDate = document.getElementById('historical-date-end').value;
        
        if (startDate || endDate) {
            this.currentFilters.date_range = {
                start: startDate ? new Date(startDate).toISOString() : null,
                end: endDate ? new Date(endDate).toISOString() : null
            };
        } else {
            delete this.currentFilters.date_range;
        }

        // Update topic filter
        const topic = document.getElementById('topic-filter').value;
        if (topic) {
            this.currentFilters.topic = topic;
        } else {
            delete this.currentFilters.topic;
        }
    }

    clearHistoricalFilters() {
        // Clear all filters
        document.getElementById('administration-filter').value = '';
        document.getElementById('historical-date-start').value = '';
        document.getElementById('historical-date-end').value = '';
        document.getElementById('topic-filter').value = '';
        
        this.currentFilters = {};
        this.loadHistoricalContent();
    }

    setupTimelineView() {
        // Add timeline view button
        const header = document.querySelector('header');
        if (!header) return;

        const timelineButton = document.createElement('button');
        timelineButton.innerHTML = '📅 Timeline';
        timelineButton.className = 'timeline-toggle-button';
        timelineButton.style.cssText = `
            background: var(--success);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
            font-weight: 500;
            margin-top: 15px;
            margin-left: 10px;
        `;

        header.appendChild(timelineButton);

        // Add timeline view to content area
        const contentFeed = document.getElementById('truth-feed');
        if (!contentFeed) return;

        const timelineView = document.createElement('div');
        timelineView.className = 'timeline-view';
        timelineView.style.cssText = `
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: var(--shadow);
        `;

        timelineView.innerHTML = `
            <h3 style="margin-top: 0; color: var(--dark);">Historical Timeline</h3>
            <div id="timeline-content" style="position: relative; padding: 20px 0;">
                <!-- Timeline entries will be added here -->
            </div>
        `;

        contentFeed.parentNode.insertBefore(timelineView, contentFeed.nextSibling);

        // Add event listener for timeline button
        timelineButton.addEventListener('click', () => {
            const timelineView = document.querySelector('.timeline-view');
            const contentFeed = document.getElementById('truth-feed');
            
            if (timelineView.style.display === 'none') {
                timelineView.style.display = 'block';
                contentFeed.style.display = 'none';
                this.loadTimeline();
            } else {
                timelineView.style.display = 'none';
                contentFeed.style.display = 'grid';
            }
        });
    }

    loadHistoricalContent() {
        // Prepare query parameters
        let queryParams = `page=${this.currentPage}&per_page=${this.perPage}`;
        
        // Add filters
        if (this.currentFilters.administration) {
            queryParams += `&administration=${encodeURIComponent(this.currentFilters.administration)}`;
        }
        
        if (this.currentFilters.topic) {
            queryParams += `&topic=${encodeURIComponent(this.currentFilters.topic)}`;
        }
        
        if (this.currentFilters.date_range) {
            if (this.currentFilters.date_range.start) {
                queryParams += `&start_date=${encodeURIComponent(this.currentFilters.date_range.start)}`;
            }
            if (this.currentFilters.date_range.end) {
                queryParams += `&end_date=${encodeURIComponent(this.currentFilters.date_range.end)}`;
            }
        }

        // Show loading indicator
        const contentFeed = document.getElementById('truth-feed');
        if (contentFeed) {
            contentFeed.innerHTML = `
                <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <div style="font-size: 24px; margin-bottom: 10px;">🏛️</div>
                    <div>Loading historical content...</div>
                </div>
            `;
        }

        // Fetch historical statements
        fetch(`${this.historicalEndpoint}/statements?${queryParams}`)
            .then(response => response.json())
            .then(data => {
                this.displayHistoricalContent(data);
            })
            .catch(error => {
                console.error('Error loading historical content:', error);
                if (contentFeed) {
                    contentFeed.innerHTML = `
                        <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                            <div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>
                            <div>Error loading historical content</div>
                        </div>
                    `;
                }
            });
    }

    displayHistoricalContent(data) {
        const contentFeed = document.getElementById('truth-feed');
        if (!contentFeed) return;

        // Display results
        if (data.statements && data.statements.length > 0) {
            contentFeed.innerHTML = '';
            data.statements.forEach(statement => {
                const card = this.createHistoricalCard(statement);
                contentFeed.appendChild(card);
            });
        } else {
            contentFeed.innerHTML = `
                <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <div style="font-size: 24px; margin-bottom: 10px;">🏛️</div>
                    <div>No historical content found</div>
                </div>
            `;
        }

        // Update pagination
        this.updateHistoricalPagination(data.pagination);
    }

    updateHistoricalPagination(pagination) {
        // Update pagination controls for historical content
        const pageInfo = document.getElementById('page-info');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        if (pageInfo && pagination) {
            pageInfo.textContent = `Page ${pagination.current_page} of ${pagination.total_pages}`;
        }
        
        if (prevButton && nextButton && pagination) {
            prevButton.disabled = pagination.current_page <= 1;
            nextButton.disabled = pagination.current_page >= pagination.total_pages;
            
            // Update event listeners for historical pagination
            prevButton.onclick = () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.loadHistoricalContent();
                }
            };
            
            nextButton.onclick = () => {
                if (pagination.current_page < pagination.total_pages) {
                    this.currentPage++;
                    this.loadHistoricalContent();
                }
            };
        }
    }

    createHistoricalCard(statement) {
        const card = document.createElement('div');
        card.className = 'truth-card historical-card';
        card.setAttribute('data-statement-id', statement.id);

        card.innerHTML = `
            <div class="truth-header">
                <h2 class="truth-title">${this.escapeHtml(statement.title || statement.topic || 'Historical Statement')}</h2>
                <span class="truth-status status-verified">Historical</span>
            </div>
            <div class="truth-content">
                <p>${this.escapeHtml(statement.statement || '').substring(0, 300)}${(statement.statement || '').length > 300 ? '...' : ''}</p>
            </div>
            <div class="action-section">
                <span class="action-label">Administration:</span>
                <span class="action-content">${this.escapeHtml(statement.administration || 'Unknown')}</span>
            </div>
            <div class="source">
                ${statement.date ? new Date(statement.date).toLocaleDateString() : 'Unknown date'} | 
                ${statement.president || 'Unknown president'}
            </div>
            <div class="methodology">
                ${statement.context || 'Historical context'}
            </div>
        `;

        return card;
    }

    loadTimeline() {
        // Fetch timeline data
        fetch(`${this.historicalEndpoint}/timeline`)
            .then(response => response.json())
            .then(data => {
                this.displayTimeline(data.timeline);
            })
            .catch(error => {
                console.error('Error loading timeline:', error);
                const timelineContent = document.getElementById('timeline-content');
                if (timelineContent) {
                    timelineContent.innerHTML = '<div>Error loading timeline</div>';
                }
            });
    }

    displayTimeline(timeline) {
        const timelineContent = document.getElementById('timeline-content');
        if (!timelineContent) return;

        if (!timeline || timeline.length === 0) {
            timelineContent.innerHTML = '<div>No timeline data available</div>';
            return;
        }

        // Sort timeline by date
        timeline.sort((a, b) => new Date(a.date) - new Date(b.date));

        // Create timeline visualization
        let timelineHTML = `
            <div style="position: relative; padding-left: 30px;">
                <div style="position: absolute; left: 15px; top: 0; bottom: 0; width: 2px; background: var(--warning);"></div>
        `;

        timeline.forEach((entry, index) => {
            timelineHTML += `
                <div style="position: relative; margin-bottom: 30px;">
                    <div style="position: absolute; left: -35px; top: 10px; width: 12px; height: 12px; background: var(--warning); border-radius: 50%; border: 2px solid white; box-shadow: 0 0 0 2px var(--warning);"></div>
                    <div style="background: #f0f4ff; border-radius: 8px; padding: 15px; border: 1px solid #e2e8f0;">
                        <div style="font-weight: bold; color: var(--warning); margin-bottom: 5px;">
                            ${entry.date ? new Date(entry.date).toLocaleDateString() : 'Unknown date'}
                        </div>
                        <div style="font-size: 1.1em; margin-bottom: 10px;">${this.escapeHtml(entry.title || 'Historical Event')}</div>
                        <div>${this.escapeHtml(entry.description || '')}</div>
                        ${entry.type ? `<div style="margin-top: 10px; font-style: italic; color: var(--neutral);">Type: ${this.escapeHtml(entry.type)}</div>` : ''}
                    </div>
                </div>
            `;
        });

        timelineHTML += '</div>';
        timelineContent.innerHTML = timelineHTML;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.historicalInterface = new HistoricalInterface();
});
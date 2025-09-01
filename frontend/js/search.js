class SearchInterface {
    constructor() {
        this.searchEndpoint = '/api/search';
        this.suggestEndpoint = '/api/search/suggest';
        this.currentQuery = '';
        this.currentFilters = {};
        this.currentSort = { field: 'relevance', order: 'desc' };
        this.currentPage = 1;
        this.perPage = 20;
        this.searchTimeout = null;
        this.init();
    }

    init() {
        this.setupSearchInput();
        this.setupFilterControls();
        this.setupSortControls();
        this.setupPaginationControls();
        this.loadInitialContent();
    }

    setupSearchInput() {
        const searchBox = document.querySelector('.search-box');
        if (!searchBox) return;

        // Add search button
        const searchButton = document.createElement('button');
        searchButton.innerHTML = '🔍';
        searchButton.className = 'search-button';
        searchButton.style.cssText = `
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
        `;

        // Position search box relatively
        searchBox.style.position = 'relative';
        searchBox.parentNode.style.position = 'relative';
        searchBox.parentNode.appendChild(searchButton);

        // Add event listeners
        searchBox.addEventListener('input', (e) => {
            this.currentQuery = e.target.value;
            this.handleSearchInput();
        });

        searchBox.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeSearch();
            }
        });

        searchButton.addEventListener('click', () => {
            this.executeSearch();
        });

        // Add autocomplete dropdown
        const autocomplete = document.createElement('div');
        autocomplete.className = 'autocomplete-dropdown';
        autocomplete.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 0 0 8px 8px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        searchBox.parentNode.appendChild(autocomplete);
    }

    handleSearchInput() {
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Set new timeout for autocomplete
        this.searchTimeout = setTimeout(() => {
            if (this.currentQuery.length > 2) {
                this.getSuggestions();
            } else {
                this.hideAutocomplete();
            }
        }, 300);
    }

    getSuggestions() {
        fetch(`${this.suggestEndpoint}?q=${encodeURIComponent(this.currentQuery)}&limit=5`)
            .then(response => response.json())
            .then(data => {
                this.showAutocomplete(data.suggestions);
            })
            .catch(error => {
                console.error('Error fetching suggestions:', error);
            });
    }

    showAutocomplete(suggestions) {
        const autocomplete = document.querySelector('.autocomplete-dropdown');
        if (!autocomplete || !suggestions.length) {
            this.hideAutocomplete();
            return;
        }

        // Clear previous suggestions
        autocomplete.innerHTML = '';

        // Add suggestions
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = suggestion;
            item.style.cssText = `
                padding: 10px 15px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
            `;

            item.addEventListener('click', () => {
                document.querySelector('.search-box').value = suggestion;
                this.currentQuery = suggestion;
                this.hideAutocomplete();
                this.executeSearch();
            });

            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = '#f0f4ff';
            });

            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = 'white';
            });

            autocomplete.appendChild(item);
        });

        // Show autocomplete
        autocomplete.style.display = 'block';
    }

    hideAutocomplete() {
        const autocomplete = document.querySelector('.autocomplete-dropdown');
        if (autocomplete) {
            autocomplete.style.display = 'none';
        }
    }

    setupFilterControls() {
        // Add filter button to header
        const header = document.querySelector('header');
        if (!header) return;

        const filterButton = document.createElement('button');
        filterButton.innerHTML = '⚙️ Filters';
        filterButton.className = 'filter-toggle-button';
        filterButton.style.cssText = `
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
            font-weight: 500;
            margin-top: 15px;
        `;

        header.appendChild(filterButton);

        // Create filter panel
        const filterPanel = document.createElement('div');
        filterPanel.className = 'filter-panel';
        filterPanel.style.cssText = `
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            display: none;
            box-shadow: var(--shadow);
        `;

        filterPanel.innerHTML = `
            <h3 style="margin-top: 0; color: var(--dark);">Advanced Filters</h3>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Date Range</label>
                <div style="display: flex; gap: 10px;">
                    <input type="date" id="date-start" style="flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                    <input type="date" id="date-end" style="flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Sources</label>
                <div id="source-filters" style="display: flex; flex-wrap: wrap; gap: 10px;">
                    <label style="display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" value="youtube" class="source-filter">
                        <span>YouTube</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" value="twitter" class="source-filter">
                        <span>Twitter</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" value="brave_search" class="source-filter">
                        <span>Brave Search</span>
                    </label>
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Content Types</label>
                <div id="type-filters" style="display: flex; flex-wrap: wrap; gap: 10px;">
                    <label style="display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" value="statement" class="type-filter">
                        <span>Statements</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px;">
                        <input type="checkbox" value="action" class="type-filter">
                        <span>Actions</span>
                    </label>
                </div>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">Credibility Score</label>
                <input type="range" id="credibility-slider" min="0" max="100" value="0" style="width: 100%;">
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <span>Any</span>
                    <span id="credibility-value">0%</span>
                </div>
            </div>
            
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="clear-filters" style="padding: 8px 16px; border: 1px solid #e2e8f0; border-radius: 4px; background: white; cursor: pointer;">
                    Clear
                </button>
                <button id="apply-filters" style="padding: 8px 16px; border: 1px solid var(--primary); border-radius: 4px; background: var(--primary); color: white; cursor: pointer;">
                    Apply Filters
                </button>
            </div>
        `;

        header.appendChild(filterPanel);

        // Add event listeners
        filterButton.addEventListener('click', () => {
            filterPanel.style.display = filterPanel.style.display === 'none' ? 'block' : 'none';
        });

        // Date filters
        document.getElementById('date-start').addEventListener('change', () => {
            this.updateFilters();
        });

        document.getElementById('date-end').addEventListener('change', () => {
            this.updateFilters();
        });

        // Source filters
        document.querySelectorAll('.source-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateFilters();
            });
        });

        // Type filters
        document.querySelectorAll('.type-filter').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateFilters();
            });
        });

        // Credibility slider
        const credibilitySlider = document.getElementById('credibility-slider');
        const credibilityValue = document.getElementById('credibility-value');
        
        credibilitySlider.addEventListener('input', () => {
            const value = credibilitySlider.value;
            credibilityValue.textContent = value + '%';
            this.updateFilters();
        });

        // Apply/clear buttons
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.executeSearch();
            filterPanel.style.display = 'none';
        });

        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });
    }

    updateFilters() {
        // Update date filters
        const startDate = document.getElementById('date-start').value;
        const endDate = document.getElementById('date-end').value;
        
        if (startDate || endDate) {
            this.currentFilters.date_range = {
                start: startDate ? new Date(startDate).toISOString() : null,
                end: endDate ? new Date(endDate).toISOString() : null
            };
        } else {
            delete this.currentFilters.date_range;
        }

        // Update source filters
        const sources = Array.from(document.querySelectorAll('.source-filter:checked'))
            .map(checkbox => checkbox.value);
        if (sources.length > 0) {
            this.currentFilters.sources = sources;
        } else {
            delete this.currentFilters.sources;
        }

        // Update type filters
        const types = Array.from(document.querySelectorAll('.type-filter:checked'))
            .map(checkbox => checkbox.value);
        if (types.length > 0) {
            this.currentFilters.types = types;
        } else {
            delete this.currentFilters.types;
        }

        // Update credibility filter
        const credibility = document.getElementById('credibility-slider').value;
        if (credibility > 0) {
            this.currentFilters.credibility_min = credibility / 100;
        } else {
            delete this.currentFilters.credibility_min;
        }
    }

    clearFilters() {
        // Clear date filters
        document.getElementById('date-start').value = '';
        document.getElementById('date-end').value = '';
        
        // Clear source filters
        document.querySelectorAll('.source-filter').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Clear type filters
        document.querySelectorAll('.type-filter').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Reset credibility slider
        document.getElementById('credibility-slider').value = 0;
        document.getElementById('credibility-value').textContent = '0%';
        
        // Clear filters object
        this.currentFilters = {};
        
        // Execute search with cleared filters
        this.executeSearch();
    }

    setupSortControls() {
        // Add sort controls to filter panel
        const filterPanel = document.querySelector('.filter-panel');
        if (!filterPanel) return;

        const sortSection = document.createElement('div');
        sortSection.style.cssText = 'margin-bottom: 20px;';
        sortSection.innerHTML = `
            <label style="display: block; margin-bottom: 8px; font-weight: 500;">Sort By</label>
            <select id="sort-field" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; margin-bottom: 10px;">
                <option value="relevance">Relevance</option>
                <option value="date">Date</option>
                <option value="credibility">Credibility</option>
                <option value="popularity">Popularity</option>
            </select>
            <select id="sort-order" style="width: 100%; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px;">
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
            </select>
        `;

        // Insert before the buttons
        filterPanel.insertBefore(sortSection, filterPanel.querySelector('div[style*="justify-content: flex-end"]'));

        // Add event listeners
        document.getElementById('sort-field').addEventListener('change', () => {
            this.updateSort();
        });

        document.getElementById('sort-order').addEventListener('change', () => {
            this.updateSort();
        });
    }

    updateSort() {
        this.currentSort.field = document.getElementById('sort-field').value;
        this.currentSort.order = document.getElementById('sort-order').value;
    }

    setupPaginationControls() {
        // Add pagination controls after content feed
        const contentFeed = document.getElementById('truth-feed');
        if (!contentFeed) return;

        const pagination = document.createElement('div');
        pagination.className = 'pagination-controls';
        pagination.style.cssText = `
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 30px 0;
            flex-wrap: wrap;
        `;

        pagination.innerHTML = `
            <button id="prev-page" style="padding: 8px 16px; border: 1px solid #e2e8f0; border-radius: 4px; background: white; cursor: pointer;">
                Previous
            </button>
            <span id="page-info" style="align-self: center; padding: 0 15px;">Page 1</span>
            <button id="next-page" style="padding: 8px 16px; border: 1px solid #e2e8f0; border-radius: 4px; background: white; cursor: pointer;">
                Next
            </button>
        `;

        contentFeed.parentNode.insertBefore(pagination, contentFeed.nextSibling);

        // Add event listeners
        document.getElementById('prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.executeSearch();
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            this.currentPage++;
            this.executeSearch();
        });
    }

    loadInitialContent() {
        // Load initial content when page loads
        this.executeSearch();
    }

    executeSearch() {
        // Hide autocomplete
        this.hideAutocomplete();

        // Prepare search request
        const searchRequest = {
            query: this.currentQuery,
            filters: this.currentFilters,
            sort: this.currentSort,
            pagination: {
                page: this.currentPage,
                per_page: this.perPage
            }
        };

        // Show loading indicator
        this.showLoadingIndicator();

        // Execute search
        fetch(this.searchEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(searchRequest)
        })
        .then(response => response.json())
        .then(data => {
            this.displayResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
            this.hideLoadingIndicator();
            this.showErrorMessage('Search failed. Please try again.');
        });
    }

    showLoadingIndicator() {
        const contentFeed = document.getElementById('truth-feed');
        if (contentFeed) {
            contentFeed.innerHTML = `
                <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <div style="font-size: 24px; margin-bottom: 10px;">🔍</div>
                    <div>Searching...</div>
                </div>
            `;
        }
    }

    hideLoadingIndicator() {
        // Loading indicator is replaced by results, so no need to hide explicitly
    }

    showErrorMessage(message) {
        const contentFeed = document.getElementById('truth-feed');
        if (contentFeed) {
            contentFeed.innerHTML = `
                <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>
                    <div>${message}</div>
                </div>
            `;
        }
    }

    displayResults(data) {
        const contentFeed = document.getElementById('truth-feed');
        if (!contentFeed) return;

        this.hideLoadingIndicator();

        // Update pagination controls
        this.updatePagination(data.pagination);

        // Display results
        if (data.results && data.results.length > 0) {
            contentFeed.innerHTML = '';
            data.results.forEach(result => {
                const card = this.createContentCard(result.document);
                contentFeed.appendChild(card);
            });
        } else {
            contentFeed.innerHTML = `
                <div style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <div style="font-size: 24px; margin-bottom: 10px;">🔍</div>
                    <div>No results found for "${this.currentQuery}"</div>
                </div>
            `;
        }

        // Update page info
        const pageInfo = document.getElementById('page-info');
        if (pageInfo && data.pagination) {
            pageInfo.textContent = `Page ${data.pagination.current_page} of ${data.pagination.total_pages}`;
        }
    }

    updatePagination(pagination) {
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        
        if (prevButton && nextButton && pagination) {
            prevButton.disabled = pagination.current_page <= 1;
            nextButton.disabled = pagination.current_page >= pagination.total_pages;
        }
    }

    createContentCard(document) {
        const card = document.createElement('div');
        card.className = 'truth-card';
        card.setAttribute('data-ipfs-hash', document.ipfs_hash);

        // Determine status class based on content type
        let statusClass = 'status-verified';
        let statusText = 'Verified Truth';
        
        if (document.type === 'action' || document.type === 'contradicted') {
            statusClass = 'status-contradicted';
            statusText = 'Contradicted Action';
        }

        card.innerHTML = `
            <button class="flag-button">🚩 Flag</button>
            <div class="truth-header">
                <h2 class="truth-title">${this.escapeHtml(document.title || 'Untitled')}</h2>
                <span class="truth-status ${statusClass}">${statusText}</span>
            </div>
            <div class="truth-content">
                <p>${this.escapeHtml(document.content || '').substring(0, 300)}${document.content && document.content.length > 300 ? '...' : ''}</p>
            </div>
            <div class="action-section">
                <span class="action-label">Source:</span>
                <span class="action-content">${this.escapeHtml(document.source || 'Unknown')}</span>
            </div>
            <div class="source">IPFS: ${document.ipfs_hash} | ${document.timestamp ? new Date(document.timestamp).toLocaleDateString() : 'Unknown date'}</div>
            <div class="methodology">
                ${document.credibility_score ? `Credibility: ${Math.round(document.credibility_score * 100)}%` : 'Verified content'}
            </div>
        `;

        return card;
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
    window.searchInterface = new SearchInterface();
});
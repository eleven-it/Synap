/**
 * Autocomplete functionality for client forms
 * Provides search and selection capabilities for various fields
 */

function initializeAutocomplete() {
    // Initialize all autocomplete fields
    const autocompleteFields = document.querySelectorAll('.autocomplete-field');
    autocompleteFields.forEach(field => {
        setupAutocomplete(field);
    });
}

function setupAutocomplete(field) {
    let dropdown = null;
    let selectedIndex = -1;
    let results = [];
    let isOpen = false;
    
    // Create dropdown element
    function createDropdown() {
        dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown hidden';
        field.parentNode.appendChild(dropdown);
    }
    
    // Show dropdown
    function showDropdown() {
        if (dropdown) {
            dropdown.classList.remove('hidden');
            isOpen = true;
        }
    }
    
    // Hide dropdown
    function hideDropdown() {
        if (dropdown) {
            dropdown.classList.add('hidden');
            isOpen = false;
            selectedIndex = -1;
        }
    }
    
    // Update dropdown content
    function updateDropdown(data) {
        if (!dropdown) return;
        
        dropdown.innerHTML = '';
        results = data;
        
        if (data.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-item text-gray-500 dark:text-gray-400">{% trans "No results found" %}</div>';
            showDropdown();
            return;
        }
        
        data.forEach((item, index) => {
            const itemElement = document.createElement('div');
            itemElement.className = 'autocomplete-item';
            itemElement.textContent = item.name || item.text;
            itemElement.dataset.value = item.id || item.value;
            itemElement.dataset.index = index;
            
            itemElement.addEventListener('click', () => {
                selectItem(item);
            });
            
            itemElement.addEventListener('mouseenter', () => {
                selectedIndex = index;
                updateSelection();
            });
            
            dropdown.appendChild(itemElement);
        });
        
        showDropdown();
    }
    
    // Update selection highlighting
    function updateSelection() {
        const items = dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    // Select an item
    function selectItem(item) {
        field.value = item.name || item.text;
        
        // Update hidden field if it exists
        const hiddenField = field.parentNode.querySelector('input[type="hidden"]');
        if (hiddenField) {
            hiddenField.value = item.id || item.value;
        }
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        field.dispatchEvent(event);
        
        hideDropdown();
    }
    
    // Search function with debouncing
    let searchTimeout;
    function performSearch(query) {
        clearTimeout(searchTimeout);
        
        searchTimeout = setTimeout(() => {
            const url = field.dataset.autocompleteUrl;
            if (!url) return;
            
            fetch(`${url}?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDropdown(data.results || []);
                    } else {
                        updateDropdown([]);
                    }
                })
                .catch(error => {
                    console.error('Autocomplete error:', error);
                    updateDropdown([]);
                });
        }, 300);
    }
    
    // Event listeners
    field.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            hideDropdown();
            return;
        }
        
        performSearch(query);
    });
    
    field.addEventListener('focus', () => {
        const query = field.value.trim();
        if (query.length >= 2) {
            performSearch(query);
        }
    });
    
    field.addEventListener('blur', () => {
        // Delay hiding to allow for clicks
        setTimeout(() => {
            hideDropdown();
        }, 200);
    });
    
    field.addEventListener('keydown', (e) => {
        if (!isOpen) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
                updateSelection();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && results[selectedIndex]) {
                    selectItem(results[selectedIndex]);
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                hideDropdown();
                break;
        }
    });
    
    // Initialize dropdown
    createDropdown();
}

// Country-specific autocomplete
function setupCountryAutocomplete() {
    const countryField = document.getElementById('id_country');
    const countrySearchField = document.getElementById('id_country_search');
    
    if (countryField && countrySearchField) {
        setupAutocomplete(countrySearchField);
        
        // Update hidden field when country is selected
        countrySearchField.addEventListener('change', () => {
            const selectedCountry = countrySearchField.value;
            if (selectedCountry) {
                // Find country by name and set the ID
                fetch('/sales/api/countries-autocomplete/?q=' + encodeURIComponent(selectedCountry))
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.results.length > 0) {
                            const country = data.results.find(c => c.name === selectedCountry);
                            if (country) {
                                countryField.value = country.id;
                                // Trigger state update
                                const event = new Event('change', { bubbles: true });
                                countryField.dispatchEvent(event);
                            }
                        }
                    });
            }
        });
    }
}

// State-specific autocomplete
function setupStateAutocomplete() {
    const stateField = document.getElementById('id_state');
    const stateSearchField = document.getElementById('id_state_search');
    const countryField = document.getElementById('id_country');
    
    if (stateField && stateSearchField) {
        setupAutocomplete(stateSearchField);
        
        // Update URL when country changes
        if (countryField) {
            countryField.addEventListener('change', () => {
                const countryId = countryField.value;
                if (countryId) {
                    stateSearchField.dataset.autocompleteUrl = `/sales/api/states-autocomplete/?country_id=${countryId}`;
                }
            });
        }
        
        // Update hidden field when state is selected
        stateSearchField.addEventListener('change', () => {
            const selectedState = stateSearchField.value;
            if (selectedState) {
                const countryId = countryField ? countryField.value : '';
                const url = countryId ? 
                    `/sales/api/states-autocomplete/?q=${encodeURIComponent(selectedState)}&country_id=${countryId}` :
                    `/sales/api/states-autocomplete/?q=${encodeURIComponent(selectedState)}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.results.length > 0) {
                            const state = data.results.find(s => s.name === selectedState);
                            if (state) {
                                stateField.value = state.id;
                            }
                        }
                    });
            }
        });
    }
}

// Fiscal responsibility autocomplete
function setupFiscalResponsibilityAutocomplete() {
    const fiscalField = document.getElementById('id_fiscal_responsibility');
    const fiscalSearchField = document.getElementById('id_fiscal_responsibility_search');
    
    if (fiscalField && fiscalSearchField) {
        setupAutocomplete(fiscalSearchField);
        
        fiscalSearchField.addEventListener('change', () => {
            const selectedFiscal = fiscalSearchField.value;
            if (selectedFiscal) {
                fetch('/sales/api/fiscal-responsibilities-autocomplete/?q=' + encodeURIComponent(selectedFiscal))
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.results.length > 0) {
                            const fiscal = data.results.find(f => f.name === selectedFiscal);
                            if (fiscal) {
                                fiscalField.value = fiscal.id;
                            }
                        }
                    });
            }
        });
    }
}

// Payment terms autocomplete
function setupPaymentTermsAutocomplete() {
    const paymentField = document.getElementById('id_payment_terms');
    const paymentSearchField = document.getElementById('id_payment_terms_search');
    
    if (paymentField && paymentSearchField) {
        setupAutocomplete(paymentSearchField);
        
        paymentSearchField.addEventListener('change', () => {
            const selectedPayment = paymentSearchField.value;
            if (selectedPayment) {
                fetch('/sales/api/payment-terms-autocomplete/?q=' + encodeURIComponent(selectedPayment))
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.results.length > 0) {
                            const payment = data.results.find(p => p.name === selectedPayment);
                            if (payment) {
                                paymentField.value = payment.id;
                            }
                        }
                    });
            }
        });
    }
}

// Initialize all autocomplete fields when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAutocomplete();
    setupCountryAutocomplete();
    setupStateAutocomplete();
    setupFiscalResponsibilityAutocomplete();
    setupPaymentTermsAutocomplete();
});

// Export functions for global use
window.initializeAutocomplete = initializeAutocomplete;
window.setupAutocomplete = setupAutocomplete; 
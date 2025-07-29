/**
 * Tags chips functionality for client forms
 * Provides tag management with visual chips and autocomplete
 */

function initializeTags() {
    const tagsSelect = document.querySelector('.tags-select');
    const newTagsField = document.getElementById('id_new_tags');
    
    if (tagsSelect) {
        setupTagsSelect(tagsSelect);
    }
    
    if (newTagsField) {
        setupNewTagsField(newTagsField);
    }
}

function setupTagsSelect(select) {
    const container = document.createElement('div');
    container.className = 'tags-container relative';
    
    // Replace the select with our custom container
    select.parentNode.insertBefore(container, select);
    select.style.display = 'none';
    
    const chipsContainer = document.createElement('div');
    chipsContainer.className = 'tags-chips flex flex-wrap gap-2 p-2 border border-gray-300 dark:border-gray-600 rounded-md min-h-[38px] bg-white dark:bg-gray-800';
    container.appendChild(chipsContainer);
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tags-input flex-1 min-w-0 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400';
    input.placeholder = '{% trans "Type to add tags..." %}';
    chipsContainer.appendChild(input);
    
    let dropdown = null;
    let selectedIndex = -1;
    let results = [];
    let isOpen = false;
    
    // Create dropdown
    function createDropdown() {
        dropdown = document.createElement('div');
        dropdown.className = 'tags-dropdown absolute top-full left-0 right-0 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg max-h-60 overflow-y-auto hidden';
        container.appendChild(dropdown);
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
            dropdown.innerHTML = '<div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">{% trans "No tags found" %}</div>';
            showDropdown();
            return;
        }
        
        data.forEach((tag, index) => {
            const itemElement = document.createElement('div');
            itemElement.className = 'px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors';
            itemElement.textContent = tag.name;
            itemElement.dataset.value = tag.id;
            itemElement.dataset.index = index;
            
            itemElement.addEventListener('click', () => {
                addTag(tag);
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
        const items = dropdown.querySelectorAll('div[data-index]');
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.classList.add('bg-orange-100', 'dark:bg-orange-900', 'text-orange-900', 'dark:text-orange-100');
            } else {
                item.classList.remove('bg-orange-100', 'dark:bg-orange-900', 'text-orange-900', 'dark:text-orange-100');
            }
        });
    }
    
    // Add tag chip
    function addTag(tag) {
        // Check if tag is already selected
        const existingChip = chipsContainer.querySelector(`[data-tag-id="${tag.id}"]`);
        if (existingChip) return;
        
        const chip = document.createElement('div');
        chip.className = 'tag-chip inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
        chip.dataset.tagId = tag.id;
        chip.dataset.tagName = tag.name;
        
        chip.innerHTML = `
            <span>${tag.name}</span>
            <button type="button" class="tag-remove ml-1 text-orange-600 dark:text-orange-400 hover:text-orange-800 dark:hover:text-orange-200">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        `;
        
        // Insert before input
        chipsContainer.insertBefore(chip, input);
        
        // Add to select
        const option = document.createElement('option');
        option.value = tag.id;
        option.text = tag.name;
        option.selected = true;
        select.appendChild(option);
        
        // Clear input and hide dropdown
        input.value = '';
        hideDropdown();
        input.focus();
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        select.dispatchEvent(event);
    }
    
    // Remove tag chip
    function removeTag(chip) {
        const tagId = chip.dataset.tagId;
        
        // Remove from select
        const option = select.querySelector(`option[value="${tagId}"]`);
        if (option) {
            option.remove();
        }
        
        // Remove chip
        chip.remove();
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        select.dispatchEvent(event);
    }
    
    // Search tags
    let searchTimeout;
    function searchTags(query) {
        clearTimeout(searchTimeout);
        
        searchTimeout = setTimeout(() => {
            fetch(`/sales/api/client-tags-autocomplete/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDropdown(data.results || []);
                    } else {
                        updateDropdown([]);
                    }
                })
                .catch(error => {
                    console.error('Tags search error:', error);
                    updateDropdown([]);
                });
        }, 300);
    }
    
    // Event listeners
    input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        if (query.length === 0) {
            hideDropdown();
            return;
        }
        
        searchTags(query);
    });
    
    input.addEventListener('focus', () => {
        const query = input.value.trim();
        if (query.length > 0) {
            searchTags(query);
        }
    });
    
    input.addEventListener('blur', () => {
        setTimeout(() => {
            hideDropdown();
        }, 200);
    });
    
    input.addEventListener('keydown', (e) => {
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
                    addTag(results[selectedIndex]);
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                hideDropdown();
                break;
        }
    });
    
    // Remove tag event delegation
    chipsContainer.addEventListener('click', (e) => {
        if (e.target.closest('.tag-remove')) {
            e.preventDefault();
            const chip = e.target.closest('.tag-chip');
            if (chip) {
                removeTag(chip);
            }
        }
    });
    
    // Initialize dropdown
    createDropdown();
    
    // Load existing tags
    loadExistingTags();
    
    function loadExistingTags() {
        const selectedOptions = Array.from(select.selectedOptions);
        selectedOptions.forEach(option => {
            const tag = {
                id: option.value,
                name: option.text
            };
            addTag(tag);
        });
    }
}

function setupNewTagsField(field) {
    const container = document.createElement('div');
    container.className = 'new-tags-container';
    
    // Replace the input with our custom container
    field.parentNode.insertBefore(container, field);
    field.style.display = 'none';
    
    const chipsContainer = document.createElement('div');
    chipsContainer.className = 'new-tags-chips flex flex-wrap gap-2 p-2 border border-gray-300 dark:border-gray-600 rounded-md min-h-[38px] bg-white dark:bg-gray-800';
    container.appendChild(chipsContainer);
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'new-tags-input flex-1 min-w-0 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400';
    input.placeholder = '{% trans "Type new tags separated by commas..." %}';
    chipsContainer.appendChild(input);
    
    // Add new tag chip
    function addNewTag(tagName) {
        const trimmedName = tagName.trim();
        if (!trimmedName) return;
        
        // Check if tag already exists
        const existingChip = chipsContainer.querySelector(`[data-tag-name="${trimmedName}"]`);
        if (existingChip) return;
        
        const chip = document.createElement('div');
        chip.className = 'new-tag-chip inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
        chip.dataset.tagName = trimmedName;
        
        chip.innerHTML = `
            <span>${trimmedName}</span>
            <button type="button" class="new-tag-remove ml-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        `;
        
        // Insert before input
        chipsContainer.insertBefore(chip, input);
        
        // Update hidden field
        updateHiddenField();
        
        // Clear input
        input.value = '';
        input.focus();
    }
    
    // Remove new tag chip
    function removeNewTag(chip) {
        chip.remove();
        updateHiddenField();
    }
    
    // Update hidden field
    function updateHiddenField() {
        const chips = chipsContainer.querySelectorAll('.new-tag-chip');
        const tagNames = Array.from(chips).map(chip => chip.dataset.tagName);
        field.value = tagNames.join(', ');
    }
    
    // Event listeners
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const value = input.value.trim();
            if (value) {
                addNewTag(value);
            }
        }
    });
    
    input.addEventListener('blur', () => {
        const value = input.value.trim();
        if (value) {
            addNewTag(value);
        }
    });
    
    // Remove tag event delegation
    chipsContainer.addEventListener('click', (e) => {
        if (e.target.closest('.new-tag-remove')) {
            e.preventDefault();
            const chip = e.target.closest('.new-tag-chip');
            if (chip) {
                removeNewTag(chip);
            }
        }
    });
    
    // Load existing new tags
    loadExistingNewTags();
    
    function loadExistingNewTags() {
        const existingTags = field.value.split(',').map(tag => tag.trim()).filter(tag => tag);
        existingTags.forEach(tagName => {
            addNewTag(tagName);
        });
    }
}

// Initialize tags when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeTags();
});

// Export functions for global use
window.initializeTags = initializeTags;
window.setupTagsSelect = setupTagsSelect;
window.setupNewTagsField = setupNewTagsField; 
/**
 * Búsqueda predictiva para campos de mapeo
 * Similar al comportamiento del wizard de clientes
 */
class PredictiveFieldSearch {
    constructor(input, endpoint, usedFields = []) {
        this.input = input;
        this.endpoint = endpoint;
        this.usedFields = usedFields;
        this.dropdown = null;
        this.debounceTimer = null;
        this.currentIndex = -1;
        this.results = [];
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        // Crear dropdown
        this.createDropdown();
        
        // Event listeners
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        
        // Click fuera para cerrar
        document.addEventListener('click', this.handleClickOutside.bind(this));
    }
    
    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'absolute z-50 w-full bg-white dark:bg-neutral-800 border border-gray-300 dark:border-neutral-600 rounded-md shadow-lg max-h-60 overflow-y-auto hidden';
        this.dropdown.style.top = '100%';
        this.dropdown.style.left = '0';
        
        // Insertar después del input
        this.input.parentNode.style.position = 'relative';
        this.input.parentNode.appendChild(this.dropdown);
    }
    
    async handleInput(e) {
        const query = e.target.value.trim();
        
        // Clear debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Debounce de 300ms
        this.debounceTimer = setTimeout(async () => {
            if (query.length >= 1) {
                await this.search(query);
            } else {
                this.hideDropdown();
            }
        }, 300);
    }
    
    async search(query) {
        try {
            // Construir URL con parámetros
            const url = new URL(this.endpoint, window.location.origin);
            url.searchParams.append('q', query);
            
            // Agregar parámetros específicos según el endpoint
            if (this.endpoint.includes('table-fields')) {
                const tableName = this.getTableName();
                if (tableName) {
                    url.searchParams.append('table', tableName);
                }
            } else if (this.endpoint.includes('model-fields')) {
                const modelName = this.getModelName();
                if (modelName) {
                    url.searchParams.append('model', modelName);
                }
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.results = this.filterUsedFields(data.fields || data.preset?.fields || []);
                this.showResults();
            } else {
                console.error('Search error:', data.error);
                this.hideDropdown();
            }
        } catch (error) {
            console.error('Search failed:', error);
            this.hideDropdown();
        }
    }
    
    filterUsedFields(fields) {
        // Filtrar campos ya utilizados
        if (Array.isArray(fields)) {
            return fields.filter(field => {
                const fieldName = typeof field === 'string' ? field : field.name;
                return !this.usedFields.includes(fieldName);
            });
        } else if (typeof fields === 'object') {
            // Si es un objeto de mapeo, devolver solo las claves no utilizadas
            return Object.keys(fields).filter(key => !this.usedFields.includes(key));
        }
        return [];
    }
    
    showResults() {
        if (this.results.length === 0) {
            this.showNoResults();
            return;
        }
        
        this.dropdown.innerHTML = '';
        
        this.results.forEach((result, index) => {
            const item = document.createElement('div');
            item.className = 'px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-neutral-700 text-xs font-sans';
            item.dataset.index = index;
            
            const fieldName = typeof result === 'string' ? result : result.name;
            const fieldType = result.type || '';
            const fieldComment = result.comment || '';
            
            item.innerHTML = `
                <div class="font-medium text-gray-900 dark:text-white">${fieldName}</div>
                ${fieldType ? `<div class="text-xs text-gray-500 dark:text-gray-400">${fieldType}</div>` : ''}
                ${fieldComment ? `<div class="text-xs text-gray-400 dark:text-gray-500">${fieldComment}</div>` : ''}
            `;
            
            item.addEventListener('click', () => this.selectResult(fieldName));
            item.addEventListener('mouseenter', () => this.highlightItem(index));
            
            this.dropdown.appendChild(item);
        });
        
        this.showDropdown();
    }
    
    showNoResults() {
        this.dropdown.innerHTML = `
            <div class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 font-sans">
                No se encontraron campos disponibles
            </div>
        `;
        this.showDropdown();
    }
    
    showDropdown() {
        this.dropdown.classList.remove('hidden');
        this.isOpen = true;
        this.currentIndex = -1;
    }
    
    hideDropdown() {
        this.dropdown.classList.add('hidden');
        this.isOpen = false;
        this.currentIndex = -1;
    }
    
    highlightItem(index) {
        // Remover highlight anterior
        this.dropdown.querySelectorAll('[data-index]').forEach(item => {
            item.classList.remove('bg-blue-100', 'dark:bg-blue-900');
        });
        
        // Highlight nuevo
        const item = this.dropdown.querySelector(`[data-index="${index}"]`);
        if (item) {
            item.classList.add('bg-blue-100', 'dark:bg-blue-900');
            this.currentIndex = index;
        }
    }
    
    selectResult(value) {
        this.input.value = value;
        this.input.dispatchEvent(new Event('change'));
        this.hideDropdown();
        this.input.focus();
    }
    
    handleKeydown(e) {
        if (!this.isOpen) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.currentIndex = Math.min(this.currentIndex + 1, this.results.length - 1);
                this.highlightItem(this.currentIndex);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.currentIndex = Math.max(this.currentIndex - 1, -1);
                if (this.currentIndex === -1) {
                    this.dropdown.querySelectorAll('[data-index]').forEach(item => {
                        item.classList.remove('bg-blue-100', 'dark:bg-blue-900');
                    });
                } else {
                    this.highlightItem(this.currentIndex);
                }
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.currentIndex >= 0 && this.results[this.currentIndex]) {
                    const fieldName = typeof this.results[this.currentIndex] === 'string' 
                        ? this.results[this.currentIndex] 
                        : this.results[this.currentIndex].name;
                    this.selectResult(fieldName);
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                this.hideDropdown();
                break;
        }
    }
    
    handleFocus() {
        if (this.input.value.trim().length >= 1) {
            this.search(this.input.value.trim());
        }
    }
    
    handleBlur() {
        // Delay para permitir clicks en el dropdown
        setTimeout(() => {
            if (!this.dropdown.contains(document.activeElement)) {
                this.hideDropdown();
            }
        }, 150);
    }
    
    handleClickOutside(e) {
        if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.hideDropdown();
        }
    }
    
    getTableName() {
        // Obtener nombre de tabla del formulario
        const tableInput = document.querySelector('input[name="administraNET_table"]');
        return tableInput ? tableInput.value : '';
    }
    
    getModelName() {
        // Obtener nombre de modelo del formulario
        const modelInput = document.querySelector('input[name="synap_model"]');
        return modelInput ? modelInput.value : '';
    }
    
    updateUsedFields(usedFields) {
        this.usedFields = usedFields;
    }
    
    destroy() {
        if (this.dropdown) {
            this.dropdown.remove();
        }
        // Remover event listeners
        this.input.removeEventListener('input', this.handleInput);
        this.input.removeEventListener('keydown', this.handleKeydown);
        this.input.removeEventListener('focus', this.handleFocus);
        this.input.removeEventListener('blur', this.handleBlur);
    }
} 
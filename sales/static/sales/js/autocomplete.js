/**
 * Sistema de autocompletado para formularios de clientes y contactos
 * Incluye validación en tiempo real y microinteracciones
 */

class AutocompleteManager {
    constructor() {
        this.activeAutocomplete = null;
        this.searchTimeouts = {};
        this.init();
    }

    init() {
        this.setupAutocomplete('clientSearch', 'clientId', '/sales/api/sales-representatives/autocomplete/');
        this.setupAutocomplete('countrySearch', 'countryId', '/sales/api/countries/autocomplete/');
        this.setupAutocomplete('stateSearch', 'stateId', '/sales/api/states/autocomplete/');
        this.setupAutocomplete('citySearch', 'cityId', '/sales/api/cities/autocomplete/');
        this.setupAutocomplete('salesRepSearch', 'salesRepId', '/sales/api/sales-representatives/autocomplete/');
        
        this.setupFormValidation();
        this.setupRealTimeValidation();
    }

    setupAutocomplete(searchInputId, hiddenInputId, apiUrl) {
        const searchInput = document.getElementById(searchInputId);
        const hiddenInput = document.getElementById(hiddenInputId);
        const resultsContainer = document.getElementById(searchInputId.replace('Search', 'Results'));

        if (!searchInput || !hiddenInput || !resultsContainer) return;

        let selectedIndex = -1;
        let results = [];

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Limpiar timeout anterior
            if (this.searchTimeouts[searchInputId]) {
                clearTimeout(this.searchTimeouts[searchInputId]);
            }

            // Ocultar resultados si no hay query
            if (!query) {
                this.hideResults(resultsContainer);
                return;
            }

            // Debounce de 300ms
            this.searchTimeouts[searchInputId] = setTimeout(() => {
                this.performSearch(query, apiUrl, resultsContainer, hiddenInput, searchInput);
            }, 300);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (!results.length) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
                    this.highlightResult(resultsContainer, selectedIndex);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, -1);
                    this.highlightResult(resultsContainer, selectedIndex);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0 && results[selectedIndex]) {
                        this.selectResult(results[selectedIndex], hiddenInput, searchInput, resultsContainer);
                    }
                    break;
                case 'Escape':
                    this.hideResults(resultsContainer);
                    break;
            }
        });

        // Cerrar autocompletado al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
                this.hideResults(resultsContainer);
            }
        });
    }

    async performSearch(query, apiUrl, resultsContainer, hiddenInput, searchInput) {
        try {
            // Mostrar indicador de carga
            resultsContainer.innerHTML = '<div class="p-3 text-center text-gray-500"><i class="fas fa-spinner fa-spin"></i> Buscando...</div>';
            resultsContainer.style.display = 'block';

            const response = await fetch(`${apiUrl}?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) throw new Error('Error en la búsqueda');

            const data = await response.json();
            results = data;

            if (results.length === 0) {
                resultsContainer.innerHTML = '<div class="p-3 text-center text-gray-500">No se encontraron resultados</div>';
            } else {
                this.displayResults(results, resultsContainer, hiddenInput, searchInput);
            }

        } catch (error) {
            console.error('Error en autocompletado:', error);
            resultsContainer.innerHTML = '<div class="p-3 text-center text-red-500">Error en la búsqueda</div>';
        }
    }

    displayResults(results, resultsContainer, hiddenInput, searchInput) {
        resultsContainer.innerHTML = '';
        
        results.forEach((result, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <div class="font-medium">${result.name}</div>
                ${result.additional_info ? `<div class="text-sm text-gray-500">${result.additional_info}</div>` : ''}
            `;
            
            item.addEventListener('click', () => {
                this.selectResult(result, hiddenInput, searchInput, resultsContainer);
            });
            
            item.addEventListener('mouseenter', () => {
                this.highlightResult(resultsContainer, index);
            });
            
            resultsContainer.appendChild(item);
        });
        
        resultsContainer.style.display = 'block';
    }

    selectResult(result, hiddenInput, searchInput, resultsContainer) {
        hiddenInput.value = result.id;
        searchInput.value = result.name;
        this.hideResults(resultsContainer);
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        hiddenInput.dispatchEvent(event);
        
        // Efecto visual
        searchInput.classList.add('ring-2', 'ring-green-500');
        setTimeout(() => {
            searchInput.classList.remove('ring-2', 'ring-green-500');
        }, 1000);
    }

    highlightResult(resultsContainer, index) {
        const items = resultsContainer.querySelectorAll('.autocomplete-item');
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    hideResults(resultsContainer) {
        resultsContainer.style.display = 'none';
    }

    setupFormValidation() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                    this.showFormErrors(form);
                }
            });
        });
    }

    setupRealTimeValidation() {
        // Validación de email
        document.querySelectorAll('input[type="email"]').forEach(input => {
            input.addEventListener('blur', () => this.validateEmail(input));
            input.addEventListener('input', () => this.clearError(input));
        });

        // Validación de teléfono
        document.querySelectorAll('input[type="tel"]').forEach(input => {
            input.addEventListener('blur', () => this.validatePhone(input));
            input.addEventListener('input', () => this.clearError(input));
        });

        // Validación de VAT/Tax ID
        document.querySelectorAll('input[name="tax_id"]').forEach(input => {
            input.addEventListener('blur', () => this.validateTaxId(input));
            input.addEventListener('input', () => this.clearError(input));
        });

        // Validación de URL
        document.querySelectorAll('input[type="url"]').forEach(input => {
            input.addEventListener('blur', () => this.validateUrl(input));
            input.addEventListener('input', () => this.clearError(input));
        });
    }

    validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'Este campo es obligatorio');
                isValid = false;
            }
        });

        // Validaciones específicas
        const emailFields = form.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !this.validateEmail(field)) {
                isValid = false;
            }
        });

        const phoneFields = form.querySelectorAll('input[type="tel"]');
        phoneFields.forEach(field => {
            if (field.value && !this.validatePhone(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateEmail(input) {
        const email = input.value.trim();
        if (!email) return true; // Campo vacío no es error si no es required
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            this.showFieldError(input, 'Ingrese un email válido');
            return false;
        }
        
        this.clearError(input);
        return true;
    }

    validatePhone(input) {
        const phone = input.value.trim();
        if (!phone) return true;
        
        const cleanPhone = phone.replace(/[\s\-\(\)\+]/g, '');
        if (!/^\d{7,15}$/.test(cleanPhone)) {
            this.showFieldError(input, 'Ingrese un número de teléfono válido');
            return false;
        }
        
        this.clearError(input);
        return true;
    }

    validateTaxId(input) {
        const taxId = input.value.trim();
        if (!taxId) return true;
        
        if (taxId.length < 3) {
            this.showFieldError(input, 'El ID fiscal debe tener al menos 3 caracteres');
            return false;
        }
        
        this.clearError(input);
        return true;
    }

    validateUrl(input) {
        const url = input.value.trim();
        if (!url) return true;
        
        try {
            new URL(url);
            this.clearError(input);
            return true;
        } catch {
            this.showFieldError(input, 'Ingrese una URL válida');
            return false;
        }
    }

    showFieldError(input, message) {
        this.clearError(input);
        
        input.classList.add('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-red-500 text-sm mt-1 flex items-center';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>${message}`;
        errorDiv.id = `error-${input.id || input.name}`;
        
        input.parentNode.appendChild(errorDiv);
        
        // Animación de shake
        input.classList.add('animate-shake');
        setTimeout(() => {
            input.classList.remove('animate-shake');
        }, 500);
    }

    clearError(input) {
        input.classList.remove('border-red-500', 'focus:border-red-500', 'focus:ring-red-500');
        
        const errorDiv = input.parentNode.querySelector(`#error-${input.id || input.name}`);
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    showFormErrors(form) {
        // Mostrar toast de error
        this.showToast('Por favor, corrija los errores en el formulario', 'error');
        
        // Scroll al primer error
        const firstError = form.querySelector('.border-red-500');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
        
        const icon = type === 'error' ? 'fa-exclamation-circle' : 
                    type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
        
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 'bg-blue-500';
        
        toast.innerHTML = `
            <div class="flex items-center ${bgColor} text-white p-3 rounded-lg">
                <i class="fas ${icon} mr-2"></i>
                <span>${message}</span>
                <button class="ml-4 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Animar entrada
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.autocompleteManager = new AutocompleteManager();
});

// CSS para animaciones
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    .animate-shake {
        animation: shake 0.5s ease-in-out;
    }
    
    .autocomplete-item {
        transition: all 0.2s ease;
    }
    
    .autocomplete-item:hover {
        background-color: #f3f4f6;
    }
    
    .autocomplete-item.selected {
        background-color: #fed7aa;
        color: #ea580c;
    }
    
    .dark .autocomplete-item:hover {
        background-color: #374151;
    }
    
    .dark .autocomplete-item.selected {
        background-color: #7c2d12;
        color: #fed7aa;
    }
`;
document.head.appendChild(style); 
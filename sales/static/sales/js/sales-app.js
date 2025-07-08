/**
 * Aplicación principal de ventas
 * Inicializa todos los componentes y funcionalidades
 */

class SalesApp {
    constructor() {
        this.autocompleteManager = null;
        this.formValidator = null;
        this.init();
    }

    init() {
        // Inicializar componentes cuando el DOM esté listo
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeComponents();
            this.setupEventListeners();
            this.setupGlobalHandlers();
        });
    }

    initializeComponents() {
        // Inicializar autocompletado
        if (typeof AutocompleteManager !== 'undefined') {
            this.autocompleteManager = new AutocompleteManager();
        }

        // Inicializar validación de formularios
        if (typeof FormValidator !== 'undefined') {
            this.formValidator = new FormValidator();
        }

        // Inicializar tooltips
        this.initializeTooltips();

        // Inicializar notificaciones
        this.initializeNotifications();

        // Inicializar filtros de tabla
        this.initializeTableFilters();

        // Inicializar modales
        this.initializeModals();
    }

    setupEventListeners() {
        // Eventos globales
        document.addEventListener('click', this.handleGlobalClick.bind(this));
        document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));

        // Eventos de formulario
        document.addEventListener('submit', this.handleFormSubmit.bind(this));

        // Eventos de navegación
        window.addEventListener('popstate', this.handlePopState.bind(this));
    }

    setupGlobalHandlers() {
        // Manejar errores globales
        window.addEventListener('error', this.handleGlobalError.bind(this));

        // Manejar errores de fetch
        this.setupFetchErrorHandling();

        // Configurar interceptores de axios si está disponible
        if (typeof axios !== 'undefined') {
            this.setupAxiosInterceptors();
        }
    }

    initializeTooltips() {
        // Inicializar tooltips usando Tippy.js si está disponible
        if (typeof tippy !== 'undefined') {
            tippy('[data-tippy-content]', {
                placement: 'top',
                arrow: true,
                theme: 'light-border'
            });
        } else {
            // Tooltips nativos
            document.querySelectorAll('[title]').forEach(element => {
                element.addEventListener('mouseenter', this.showNativeTooltip.bind(this));
                element.addEventListener('mouseleave', this.hideNativeTooltip.bind(this));
            });
        }
    }

    initializeNotifications() {
        // Configurar sistema de notificaciones
        this.notificationContainer = document.createElement('div');
        this.notificationContainer.id = 'notification-container';
        this.notificationContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.notificationContainer);
    }

    initializeTableFilters() {
        // Inicializar filtros de tabla
        document.querySelectorAll('.table-filter').forEach(filter => {
            filter.addEventListener('change', this.handleTableFilter.bind(this));
        });

        // Inicializar búsqueda en tablas
        document.querySelectorAll('.table-search').forEach(search => {
            search.addEventListener('input', this.handleTableSearch.bind(this));
        });
    }

    initializeModals() {
        // Inicializar modales
        document.querySelectorAll('[data-modal]').forEach(trigger => {
            trigger.addEventListener('click', this.openModal.bind(this));
        });

        // Cerrar modales con Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }

    handleGlobalClick(event) {
        // Manejar clics en elementos con data-action
        if (event.target.hasAttribute('data-action')) {
            const action = event.target.getAttribute('data-action');
            this.handleAction(action, event.target);
        }

        // Cerrar dropdowns al hacer clic fuera
        if (!event.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.classList.add('hidden');
            });
        }
    }

    handleGlobalKeydown(event) {
        // Atajos de teclado globales
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 'k':
                    event.preventDefault();
                    this.focusSearch();
                    break;
                case 'n':
                    event.preventDefault();
                    this.createNew();
                    break;
                case 's':
                    if (event.target.tagName === 'FORM') {
                        // Permitir guardar formulario
                        return;
                    }
                    event.preventDefault();
                    this.saveCurrent();
                    break;
            }
        }
    }

    handleFormSubmit(event) {
        const form = event.target;
        
        // Mostrar indicador de carga
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Guardando...';
            
            // Restaurar después de un tiempo
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }, 5000);
        }
    }

    handleTableFilter(event) {
        const filter = event.target;
        const table = filter.closest('.table-container').querySelector('table');
        const filterValue = filter.value.toLowerCase();
        
        // Filtrar filas de la tabla
        table.querySelectorAll('tbody tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            if (filterValue === '' || text.includes(filterValue)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    handleTableSearch(event) {
        const search = event.target;
        const table = search.closest('.table-container').querySelector('table');
        const searchValue = search.value.toLowerCase();
        
        // Buscar en todas las columnas
        table.querySelectorAll('tbody tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            let found = false;
            
            cells.forEach(cell => {
                if (cell.textContent.toLowerCase().includes(searchValue)) {
                    found = true;
                }
            });
            
            if (found) {
                row.style.display = '';
                // Resaltar texto encontrado
                this.highlightSearchText(row, searchValue);
            } else {
                row.style.display = 'none';
            }
        });
    }

    highlightSearchText(row, searchText) {
        if (!searchText) return;
        
        row.querySelectorAll('td').forEach(cell => {
            const text = cell.textContent;
            const regex = new RegExp(`(${searchText})`, 'gi');
            cell.innerHTML = text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>');
        });
    }

    openModal(event) {
        const modalId = event.target.getAttribute('data-modal');
        const modal = document.getElementById(modalId);
        
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            
            // Focus en el primer input
            const firstInput = modal.querySelector('input, select, textarea');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        });
    }

    handleAction(action, element) {
        switch (action) {
            case 'delete':
                this.handleDelete(element);
                break;
            case 'duplicate':
                this.handleDuplicate(element);
                break;
            case 'export':
                this.handleExport(element);
                break;
            case 'print':
                this.handlePrint(element);
                break;
            default:
                console.log('Acción no implementada:', action);
        }
    }

    handleDelete(element) {
        const itemName = element.getAttribute('data-item-name') || 'este elemento';
        const confirmMessage = `¿Está seguro de que desea eliminar ${itemName}?`;
        
        if (confirm(confirmMessage)) {
            const url = element.getAttribute('data-url');
            if (url) {
                this.performDelete(url);
            }
        }
    }

    async performDelete(url) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                this.showNotification('Elemento eliminado correctamente', 'success');
                // Recargar página o actualizar tabla
                window.location.reload();
            } else {
                throw new Error('Error al eliminar');
            }
        } catch (error) {
            this.showNotification('Error al eliminar el elemento', 'error');
        }
    }

    handleDuplicate(element) {
        const url = element.getAttribute('data-url');
        if (url) {
            window.location.href = url;
        }
    }

    handleExport(element) {
        const url = element.getAttribute('data-url');
        if (url) {
            window.open(url, '_blank');
        }
    }

    handlePrint(element) {
        window.print();
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
        
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        notification.innerHTML = `
            <div class="flex items-center ${bgColor} text-white">
                <i class="fas fa-${this.getNotificationIcon(type)} mr-2"></i>
                <span>${message}</span>
                <button class="ml-4 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        this.notificationContainer.appendChild(notification);
        
        // Animar entrada
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remover después de 5 segundos
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'error': return 'exclamation-circle';
            case 'success': return 'check-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.match(/csrftoken=([^;]+)/)?.[1];
    }

    setupFetchErrorHandling() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response;
            } catch (error) {
                this.showNotification(`Error de red: ${error.message}`, 'error');
                throw error;
            }
        };
    }

    setupAxiosInterceptors() {
        // Request interceptor
        axios.interceptors.request.use(
            config => {
                // Agregar CSRF token
                const token = this.getCSRFToken();
                if (token) {
                    config.headers['X-CSRFToken'] = token;
                }
                return config;
            },
            error => {
                return Promise.reject(error);
            }
        );

        // Response interceptor
        axios.interceptors.response.use(
            response => {
                return response;
            },
            error => {
                this.showNotification(`Error: ${error.message}`, 'error');
                return Promise.reject(error);
            }
        );
    }

    handleGlobalError(event) {
        console.error('Error global:', event.error);
        this.showNotification('Ha ocurrido un error inesperado', 'error');
    }

    focusSearch() {
        const searchInput = document.querySelector('.table-search, input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    createNew() {
        const createBtn = document.querySelector('[href*="/create/"], [data-action="create"]');
        if (createBtn) {
            createBtn.click();
        }
    }

    saveCurrent() {
        const saveBtn = document.querySelector('button[type="submit"]');
        if (saveBtn) {
            saveBtn.click();
        }
    }

    showNativeTooltip(event) {
        const element = event.target;
        const title = element.getAttribute('title');
        
        if (title) {
            const tooltip = document.createElement('div');
            tooltip.className = 'fixed z-50 px-2 py-1 text-sm text-white bg-gray-900 rounded shadow-lg';
            tooltip.textContent = title;
            tooltip.id = 'native-tooltip';
            
            document.body.appendChild(tooltip);
            
            const rect = element.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
        }
    }

    hideNativeTooltip() {
        const tooltip = document.getElementById('native-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }
}

// Inicializar la aplicación
window.salesApp = new SalesApp(); 
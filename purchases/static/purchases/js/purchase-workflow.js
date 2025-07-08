/**
 * JavaScript para manejar el workflow unificado de documentos de compra
 */

class PurchaseWorkflow {
    constructor() {
        this.initializeEventListeners();
        this.initializeFormValidation();
        this.initializeLineManagement();
        this.initializeCalculations();
    }

    initializeEventListeners() {
        // Botones de acción del workflow
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => this.handleAction(e));
        });

        // Cambio de tipo de documento
        const documentTypeSelect = document.getElementById('document_type');
        if (documentTypeSelect) {
            documentTypeSelect.addEventListener('change', (e) => this.handleDocumentTypeChange(e));
        }

        // Búsqueda de productos
        const productSearch = document.getElementById('product_search');
        if (productSearch) {
            productSearch.addEventListener('input', (e) => this.handleProductSearch(e));
        }

        // Botones de agregar/quitar líneas
        document.querySelectorAll('.add-line-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.addLine(e));
        });

        document.querySelectorAll('.remove-line-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.removeLine(e));
        });

        // Validación de formulario
        const form = document.getElementById('purchase-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
    }

    initializeFormValidation() {
        // Validación de campos requeridos
        const requiredFields = document.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', (e) => this.validateField(e.target));
            field.addEventListener('input', (e) => this.clearFieldError(e.target));
        });
    }

    initializeLineManagement() {
        // Inicializar contador de líneas
        this.lineCounter = document.querySelectorAll('.purchase-line').length;
        
        // Hacer líneas existentes editables
        document.querySelectorAll('.purchase-line').forEach(line => {
            this.makeLineEditable(line);
        });
    }

    initializeCalculations() {
        // Calcular totales iniciales
        this.calculateTotals();
        
        // Eventos para recalcular totales
        document.querySelectorAll('.quantity-input, .price-input, .discount-input').forEach(input => {
            input.addEventListener('input', () => this.calculateTotals());
        });
    }

    handleAction(event) {
        event.preventDefault();
        
        const button = event.currentTarget;
        const action = button.dataset.action;
        const documentId = button.dataset.documentId;
        const reason = button.dataset.reason || '';

        // Mostrar confirmación para acciones críticas
        if (this.requiresConfirmation(action)) {
            const confirmed = confirm(this.getConfirmationMessage(action));
            if (!confirmed) return;
        }

        // Mostrar modal de razón si es necesario
        if (this.requiresReason(action)) {
            this.showReasonModal(action, documentId);
            return;
        }

        // Ejecutar acción
        this.executeAction(action, documentId, reason);
    }

    requiresConfirmation(action) {
        const criticalActions = ['cancel', 'reject', 'delete'];
        return criticalActions.includes(action);
    }

    requiresReason(action) {
        const reasonActions = ['reject', 'cancel', 'approve'];
        return reasonActions.includes(action);
    }

    getConfirmationMessage(action) {
        const messages = {
            'cancel': '¿Está seguro de que desea cancelar este documento?',
            'reject': '¿Está seguro de que desea rechazar este documento?',
            'delete': '¿Está seguro de que desea eliminar este documento?'
        };
        return messages[action] || '¿Está seguro de que desea realizar esta acción?';
    }

    showReasonModal(action, documentId) {
        const reason = prompt(this.getReasonPrompt(action));
        if (reason !== null) {
            this.executeAction(action, documentId, reason);
        }
    }

    getReasonPrompt(action) {
        const prompts = {
            'reject': 'Por favor, indique la razón del rechazo:',
            'cancel': 'Por favor, indique la razón de la cancelación:',
            'approve': 'Comentarios adicionales (opcional):'
        };
        return prompts[action] || 'Por favor, indique la razón:';
    }

    async executeAction(action, documentId, reason = '') {
        try {
            // Mostrar indicador de carga
            this.showLoading();

            const formData = new FormData();
            formData.append('reason', reason);

            const response = await fetch(`/purchases/documents/${documentId}/action/${action}/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                // Redirigir a la página de detalles
                window.location.href = `/purchases/documents/${documentId}/`;
            } else {
                const error = await response.text();
                this.showError('Error al ejecutar la acción: ' + error);
            }
        } catch (error) {
            this.showError('Error de conexión: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    handleDocumentTypeChange(event) {
        const documentType = event.target.value;
        const supplierSection = document.getElementById('supplier-section');
        const requestFields = document.querySelectorAll('.request-field');
        const orderFields = document.querySelectorAll('.order-field');

        if (documentType === 'order') {
            supplierSection.style.display = 'block';
            requestFields.forEach(field => field.style.display = 'none');
            orderFields.forEach(field => field.style.display = 'block');
        } else {
            supplierSection.style.display = 'none';
            requestFields.forEach(field => field.style.display = 'block');
            orderFields.forEach(field => field.style.display = 'none');
        }

        // Actualizar validaciones
        this.updateValidations(documentType);
    }

    handleProductSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const productOptions = document.querySelectorAll('.product-option');

        productOptions.forEach(option => {
            const productName = option.textContent.toLowerCase();
            if (productName.includes(searchTerm)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    }

    addLine(event) {
        event.preventDefault();
        
        this.lineCounter++;
        const lineTemplate = this.getLineTemplate(this.lineCounter);
        const linesContainer = document.getElementById('lines-container');
        
        linesContainer.insertAdjacentHTML('beforeend', lineTemplate);
        
        // Hacer la nueva línea editable
        const newLine = linesContainer.lastElementChild;
        this.makeLineEditable(newLine);
        
        // Actualizar totales
        this.calculateTotals();
        
        // Mostrar animación
        this.animateNewLine(newLine);
    }

    removeLine(event) {
        event.preventDefault();
        
        const line = event.currentTarget.closest('.purchase-line');
        if (document.querySelectorAll('.purchase-line').length > 1) {
            this.animateRemoveLine(line, () => {
                line.remove();
                this.calculateTotals();
            });
        } else {
            this.showError('Debe tener al menos una línea en el documento');
        }
    }

    makeLineEditable(line) {
        // Hacer campos editables
        const inputs = line.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', () => this.calculateTotals());
            input.addEventListener('change', () => this.validateLine(line));
        });
    }

    getLineTemplate(lineNumber) {
        return `
            <div class="purchase-line bg-white border border-gray-200 rounded-lg p-4 mb-4 transition-all duration-300 hover:shadow-md">
                <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
                    <div class="md:col-span-4">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Producto</label>
                        <select name="line_${lineNumber}_product" class="product-select w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-orange-500 focus:border-orange-500" required>
                            <option value="">Seleccionar producto</option>
                            ${this.getProductOptions()}
                        </select>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Cantidad</label>
                        <input type="number" name="line_${lineNumber}_quantity" class="quantity-input w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-orange-500 focus:border-orange-500" min="0" step="0.01" required>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Precio Unit.</label>
                        <input type="number" name="line_${lineNumber}_price" class="price-input w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-orange-500 focus:border-orange-500" min="0" step="0.01">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Subtotal</label>
                        <input type="text" class="subtotal-input w-full border border-gray-300 rounded-md px-3 py-2 bg-gray-50" readonly>
                    </div>
                    <div class="md:col-span-2 flex items-end">
                        <button type="button" class="remove-line-btn bg-red-500 hover:bg-red-600 text-white px-3 py-2 rounded-md transition-colors duration-200">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    getProductOptions() {
        // Obtener productos del DOM o hacer una petición AJAX
        const products = window.purchaseProducts || [];
        return products.map(product => 
            `<option value="${product.id}">${product.name}</option>`
        ).join('');
    }

    calculateTotals() {
        let subtotal = 0;
        let tax = 0;
        let total = 0;

        document.querySelectorAll('.purchase-line').forEach(line => {
            const quantity = parseFloat(line.querySelector('.quantity-input').value) || 0;
            const price = parseFloat(line.querySelector('.price-input').value) || 0;
            const lineSubtotal = quantity * price;
            
            // Actualizar subtotal de la línea
            line.querySelector('.subtotal-input').value = lineSubtotal.toFixed(2);
            
            subtotal += lineSubtotal;
        });

        // Calcular impuestos (si aplica)
        const taxRate = parseFloat(document.getElementById('tax_rate')?.value) || 0;
        tax = subtotal * (taxRate / 100);

        total = subtotal + tax;

        // Actualizar totales en la barra fija
        document.getElementById('subtotal-amount').textContent = subtotal.toFixed(2);
        document.getElementById('tax-amount').textContent = tax.toFixed(2);
        document.getElementById('total-amount').textContent = total.toFixed(2);

        // Actualizar progreso
        this.updateProgress();
    }

    updateProgress() {
        const form = document.getElementById('purchase-form');
        const requiredFields = form.querySelectorAll('[required]');
        const filledFields = Array.from(requiredFields).filter(field => field.value.trim() !== '');
        const progress = (filledFields.length / requiredFields.length) * 100;

        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
    }

    validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        
        if (isRequired && value === '') {
            this.showFieldError(field, 'Este campo es obligatorio');
            return false;
        }
        
        this.clearFieldError(field);
        return true;
    }

    validateLine(line) {
        const product = line.querySelector('.product-select').value;
        const quantity = line.querySelector('.quantity-input').value;
        
        if (!product || !quantity) {
            line.classList.add('border-red-500');
            return false;
        }
        
        line.classList.remove('border-red-500');
        return true;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        field.classList.add('border-red-500');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-red-500 text-sm mt-1';
        errorDiv.textContent = message;
        errorDiv.dataset.error = 'true';
        
        field.parentNode.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.classList.remove('border-red-500');
        const errorDiv = field.parentNode.querySelector('[data-error="true"]');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    handleFormSubmit(event) {
        event.preventDefault();
        
        // Validar formulario
        const form = event.target;
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Validar líneas
        const lines = form.querySelectorAll('.purchase-line');
        lines.forEach(line => {
            if (!this.validateLine(line)) {
                isValid = false;
            }
        });

        if (!isValid) {
            this.showError('Por favor, complete todos los campos requeridos');
            return;
        }

        // Enviar formulario
        this.submitForm(form);
    }

    async submitForm(form) {
        try {
            this.showLoading();
            
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: form.method,
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    this.showSuccess(result.message || 'Documento guardado exitosamente');
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 1500);
                } else {
                    this.showError(result.message || 'Error al guardar el documento');
                }
            } else {
                this.showError('Error del servidor');
            }
        } catch (error) {
            this.showError('Error de conexión: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    // Utilidades
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    showLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.style.display = 'flex';
        }
    }

    hideLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.style.display = 'none';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 ${
            type === 'success' ? 'bg-green-500 text-white' : 
            type === 'error' ? 'bg-red-500 text-white' : 
            'bg-blue-500 text-white'
        }`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    animateNewLine(line) {
        line.style.opacity = '0';
        line.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            line.style.transition = 'all 0.3s ease';
            line.style.opacity = '1';
            line.style.transform = 'translateY(0)';
        }, 10);
    }

    animateRemoveLine(line, callback) {
        line.style.transition = 'all 0.3s ease';
        line.style.opacity = '0';
        line.style.transform = 'translateX(-100%)';
        
        setTimeout(callback, 300);
    }

    updateValidations(documentType) {
        const supplierField = document.getElementById('supplier');
        if (documentType === 'order') {
            supplierField.setAttribute('required', 'required');
        } else {
            supplierField.removeAttribute('required');
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new PurchaseWorkflow();
}); 
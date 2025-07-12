/**
 * TPV (Point of Sale) JavaScript
 * Funcionalidades: búsqueda en tiempo real, carrito, pago, microinteracciones
 */

class TPV {
    constructor() {
        this.cart = [];
        this.searchTimeout = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialProducts();
        this.updateCartDisplay();
    }

    bindEvents() {
        // Búsqueda en tiempo real
        const searchInput = document.getElementById('product-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.searchProducts(e.target.value);
                }, 300);
            });

            searchInput.addEventListener('focus', () => {
                this.showSearchResults();
            });

            // Cerrar resultados al hacer clic fuera
            document.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !document.getElementById('search-results').contains(e.target)) {
                    this.hideSearchResults();
                }
            });
        }

        // Botón de pago
        const payBtn = document.getElementById('pay-btn');
        if (payBtn) {
            payBtn.addEventListener('click', () => {
                this.showPaymentModal();
            });
        }

        // Modal de pago
        const paymentModal = document.getElementById('payment-modal');
        const cancelPayment = document.getElementById('cancel-payment');
        const paymentForm = document.getElementById('payment-form');

        if (cancelPayment) {
            cancelPayment.addEventListener('click', () => {
                this.hidePaymentModal();
            });
        }

        if (paymentForm) {
            paymentForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.processPayment();
            });
        }

        // Método de pago
        const paymentMethod = document.getElementById('payment-method');
        if (paymentMethod) {
            paymentMethod.addEventListener('change', (e) => {
                this.updatePaymentFields(e.target.value);
            });
        }

        // Cerrar modal con Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hidePaymentModal();
            }
        });
    }

    async searchProducts(query) {
        if (!query || query.length < 2) {
            this.hideSearchResults();
            return;
        }

        try {
            const response = await fetch(`/sales/api/products/search/?q=${encodeURIComponent(query)}`);
            const products = await response.json();
            this.displaySearchResults(products);
        } catch (error) {
            console.error('Error searching products:', error);
            this.showToast('Error searching products', 'error');
        }
    }

    displaySearchResults(products) {
        const resultsContainer = document.getElementById('search-results');
        if (!resultsContainer) return;

        if (products.length === 0) {
            resultsContainer.innerHTML = `
                <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                    No products found
                </div>
            `;
        } else {
            resultsContainer.innerHTML = products.map(product => `
                <div class="product-result p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-600 last:border-b-0 transition-colors"
                     data-product-id="${product.id}">
                    <div class="flex items-center justify-between">
                        <div>
                            <div class="font-medium text-gray-900 dark:text-white">${product.name}</div>
                            <div class="text-sm text-gray-500 dark:text-gray-400">${product.sku || 'No SKU'}</div>
                        </div>
                        <div class="text-right">
                            <div class="font-semibold text-gray-900 dark:text-white">$${product.price}</div>
                            <div class="text-sm text-gray-500 dark:text-gray-400">Stock: ${product.stock || 0}</div>
                        </div>
                    </div>
                </div>
            `).join('');

            // Bind click events
            resultsContainer.querySelectorAll('.product-result').forEach(item => {
                item.addEventListener('click', () => {
                    const productId = item.dataset.productId;
                    this.addToCart(productId);
                    this.hideSearchResults();
                    document.getElementById('product-search').value = '';
                });
            });
        }

        this.showSearchResults();
    }

    showSearchResults() {
        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.classList.remove('hidden');
            resultsContainer.classList.add('animate-fade-in');
        }
    }

    hideSearchResults() {
        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.classList.add('hidden');
        }
    }

    async addToCart(productId) {
        try {
            const response = await fetch(`/sales/api/products/${productId}/`);
            const product = await response.json();
            
            const existingItem = this.cart.find(item => item.id === product.id);
            
            if (existingItem) {
                existingItem.quantity += 1;
            } else {
                this.cart.push({
                    id: product.id,
                    name: product.name,
                    price: product.price,
                    quantity: 1,
                    stock: product.stock || 0
                });
            }

            this.updateCartDisplay();
            this.showToast('Product added to cart', 'success');
            tpvSounds.scan.play();
            
            // Animación de éxito
            this.animateAddToCart();
            
            // Scroll automático al carrito
            const cartContainer = document.getElementById('cart-items');
            if (cartContainer) cartContainer.scrollTop = cartContainer.scrollHeight;
            
        } catch (error) {
            console.error('Error adding product to cart:', error);
            this.showToast('Error adding product to cart', 'error');
        }
    }

    removeFromCart(index) {
        this.cart.splice(index, 1);
        this.updateCartDisplay();
        this.showToast('Product removed from cart', 'info');
    }

    updateQuantity(index, delta) {
        const item = this.cart[index];
        const newQuantity = item.quantity + delta;
        
        if (newQuantity <= 0) {
            this.removeFromCart(index);
        } else if (newQuantity <= item.stock) {
            item.quantity = newQuantity;
            this.updateCartDisplay();
        } else {
            this.showToast('Not enough stock available', 'error');
        }
    }

    updateCartDisplay() {
        const cartContainer = document.getElementById('cart-items');
        const totalElement = document.getElementById('cart-total');
        
        if (!cartContainer || !totalElement) return;

        if (this.cart.length === 0) {
            cartContainer.innerHTML = `
                <div class="text-center text-gray-500 dark:text-gray-400 py-8">
                    <svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path>
                    </svg>
                    <p>Cart is empty</p>
                </div>
            `;
        } else {
            cartContainer.innerHTML = this.cart.map((item, index) => `
                <div class="cart-item bg-gray-50 dark:bg-gray-800 rounded-lg p-3 mb-3 animate-fade-in">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="font-medium text-gray-900 dark:text-white">${item.name}</div>
                            <div class="text-sm text-gray-500 dark:text-gray-400">$${item.price} each</div>
                        </div>
                        <div class="flex items-center gap-2">
                            <button class="quantity-btn w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
                                    onclick="tpv.updateQuantity(${index}, -1)">
                                <svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path>
                                </svg>
                            </button>
                            <span class="quantity-display w-8 text-center font-semibold text-gray-900 dark:text-white" data-index="${index}">${item.quantity}</span>
                            <button class="quantity-btn w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
                                    onclick="tpv.updateQuantity(${index}, 1)">
                                <svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                                </svg>
                            </button>
                            <button class="remove-btn w-8 h-8 rounded-full bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800 transition"
                                    onclick="tpv.removeFromCart(${index})">
                                <svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="mt-2 text-right">
                        <span class="font-semibold text-gray-900 dark:text-white">$${(item.price * item.quantity).toFixed(2)}</span>
                    </div>
                </div>
            `).join('');
        }

        const total = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        totalElement.textContent = `$${total.toFixed(2)}`;
        
        // Actualizar botón de pago
        const payBtn = document.getElementById('pay-btn');
        if (payBtn) {
            payBtn.disabled = this.cart.length === 0;
            payBtn.classList.toggle('opacity-50', this.cart.length === 0);
        }
    }

    showPaymentModal() {
        if (this.cart.length === 0) {
            this.showToast('Cart is empty', 'error');
            return;
        }

        const modal = document.getElementById('payment-modal');
        const amount = document.getElementById('payment-amount');
        
        if (modal && amount) {
            const total = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            amount.textContent = `$${total.toFixed(2)}`;
            
            modal.classList.remove('hidden');
            modal.classList.add('animate-fade-in');
            
            // Focus en el primer campo
            setTimeout(() => {
                const paymentMethod = document.getElementById('payment-method');
                if (paymentMethod) paymentMethod.focus();
            }, 100);
        }
    }

    hidePaymentModal() {
        const modal = document.getElementById('payment-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    updatePaymentFields(method) {
        const extraFields = document.getElementById('payment-extra-fields');
        const cloverFields = document.getElementById('clover-fields');
        if (!extraFields) return;

        // Ocultar campos de Clover por defecto
        if (cloverFields) {
            cloverFields.style.display = 'none';
        }

        let fields = '';
        
        // Obtener información del método seleccionado
        const paymentMethodSelect = document.getElementById('payment-method');
        const selectedOption = paymentMethodSelect ? paymentMethodSelect.options[paymentMethodSelect.selectedIndex] : null;
        const processor = selectedOption ? selectedOption.dataset.processor : '';
        const paymentType = selectedOption ? selectedOption.dataset.type : '';
        
        // Si es Clover, mostrar campos específicos
        if (processor === 'clover') {
            if (cloverFields) {
                cloverFields.style.display = 'block';
                
                // Mostrar campos según el tipo de pago
                const installmentsField = document.getElementById('clover-installments');
                const referenceField = document.getElementById('clover-reference');
                
                if (installmentsField) {
                    installmentsField.style.display = paymentType === 'card' ? 'block' : 'none';
                }
                
                if (referenceField) {
                    referenceField.style.display = ['cash', 'check', 'bank_transfer'].includes(paymentType) ? 'block' : 'none';
                }
            }
        } else {
            // Campos para métodos no-Clover
            switch (method) {
                case 'CASH':
                    fields = `
                        <div>
                            <label for="cash-received" class="block text-gray-700 dark:text-gray-200 mb-1">Cash received</label>
                            <input type="number" id="cash-received" step="0.01" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                        </div>
                        <div id="change-display" class="text-lg font-semibold text-green-600 dark:text-green-400"></div>
                    `;
                    break;
                case 'CREDIT_CARD':
                case 'DEBIT_CARD':
                    fields = `
                        <div>
                            <label for="card-number" class="block text-gray-700 dark:text-gray-200 mb-1">Card number (last 4 digits)</label>
                            <input type="text" id="card-number" maxlength="4" placeholder="1234" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                        </div>
                        <div>
                            <label for="card-installments" class="block text-gray-700 dark:text-gray-200 mb-1">Installments</label>
                            <select id="card-installments" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none">
                                <option value="1">1 installment</option>
                                <option value="3">3 installments</option>
                                <option value="6">6 installments</option>
                                <option value="12">12 installments</option>
                            </select>
                        </div>
                    `;
                    break;
                case 'BANK_TRANSFER':
                    fields = `
                        <div>
                            <label for="transfer-reference" class="block text-gray-700 dark:text-gray-200 mb-1">Transfer reference</label>
                            <input type="text" id="transfer-reference" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                        </div>
                    `;
                    break;
                case 'CHECK':
                    fields = `
                        <div>
                            <label for="check-number" class="block text-gray-700 dark:text-gray-200 mb-1">Check number</label>
                            <input type="text" id="check-number" class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                        </div>
                    `;
                    break;
            }
        }
        
        extraFields.innerHTML = fields;
        
        // Bind events for new fields
        if (method === 'CASH') {
            const cashReceived = document.getElementById('cash-received');
            if (cashReceived) {
                cashReceived.addEventListener('input', () => {
                    this.calculateChange();
                });
            }
        }
    }

    calculateChange() {
        const cashReceived = document.getElementById('cash-received');
        const changeDisplay = document.getElementById('change-display');
        const total = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        
        if (cashReceived && changeDisplay) {
            const received = parseFloat(cashReceived.value) || 0;
            const change = received - total;
            
            if (change >= 0) {
                changeDisplay.textContent = `Change: $${change.toFixed(2)}`;
                changeDisplay.classList.remove('text-red-600', 'dark:text-red-400');
                changeDisplay.classList.add('text-green-600', 'dark:text-green-400');
            } else {
                changeDisplay.textContent = `Remaining: $${Math.abs(change).toFixed(2)}`;
                changeDisplay.classList.remove('text-green-600', 'dark:text-green-400');
                changeDisplay.classList.add('text-red-600', 'dark:text-red-400');
            }
        }
    }

    async processPayment() {
        const paymentMethod = document.getElementById('payment-method');
        const method = paymentMethod ? paymentMethod.value : '';
        
        if (!method) {
            this.showToast('Please select a payment method', 'error');
            return;
        }
        
        // Obtener información del método seleccionado
        const selectedOption = paymentMethod ? paymentMethod.options[paymentMethod.selectedIndex] : null;
        const processor = selectedOption ? selectedOption.dataset.processor : '';
        
        // Validaciones específicas por método
        if (processor === 'clover') {
            const cloverDevice = document.getElementById('clover-device');
            if (!cloverDevice || !cloverDevice.value) {
                this.showToast('Please select a Clover device', 'error');
                return;
            }
        } else if (method === 'CASH') {
            const cashReceived = document.getElementById('cash-received');
            const total = this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            if (!cashReceived || parseFloat(cashReceived.value) < total) {
                this.showToast('Insufficient cash received', 'error');
                return;
            }
        }

        try {
            const paymentData = {
                items: this.cart,
                payment_method: method,
                total: this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0),
                extra_data: this.getPaymentExtraData(method)
            };

            const response = await fetch('/sales/tpv/process-payment/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(paymentData)
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccessPayment(result);
                this.clearCart();
                this.hidePaymentModal();
            } else {
                throw new Error('Payment failed');
            }
            
        } catch (error) {
            console.error('Error processing payment:', error);
            this.showToast('Error processing payment', 'error');
        }
    }

    getPaymentExtraData(method) {
        const data = {};
        
        // Obtener información del método seleccionado
        const paymentMethodSelect = document.getElementById('payment-method');
        const selectedOption = paymentMethodSelect ? paymentMethodSelect.options[paymentMethodSelect.selectedIndex] : null;
        const processor = selectedOption ? selectedOption.dataset.processor : '';
        
        // Si es Clover, obtener datos específicos
        if (processor === 'clover') {
            const cloverDevice = document.getElementById('clover-device');
            const cloverInstallments = document.getElementById('clover-installments-select');
            const cloverReference = document.getElementById('clover-reference-input');
            
            if (cloverDevice) data.clover_device_id = cloverDevice.value;
            if (cloverInstallments) data.installments = parseInt(cloverInstallments.value);
            if (cloverReference) data.reference = cloverReference.value;
            
            data.processor = 'clover';
        } else {
            // Datos para métodos no-Clover
            switch (method) {
                case 'CASH':
                    const cashReceived = document.getElementById('cash-received');
                    if (cashReceived) data.cash_received = parseFloat(cashReceived.value);
                    break;
                case 'CREDIT_CARD':
                case 'DEBIT_CARD':
                    const cardNumber = document.getElementById('card-number');
                    const cardInstallments = document.getElementById('card-installments');
                    if (cardNumber) data.card_number = cardNumber.value;
                    if (cardInstallments) data.installments = parseInt(cardInstallments.value);
                    break;
                case 'BANK_TRANSFER':
                    const transferRef = document.getElementById('transfer-reference');
                    if (transferRef) data.transfer_reference = transferRef.value;
                    break;
                case 'CHECK':
                    const checkNumber = document.getElementById('check-number');
                    if (checkNumber) data.check_number = checkNumber.value;
                    break;
            }
        }
        
        return data;
    }

    showSuccessPayment(result) {
        // Mostrar confeti animado
        this.showConfetti();
        
        // Toast de éxito
        this.showToast('Payment successful!', 'success');
        
        // Mostrar resumen de la venta
        setTimeout(() => {
            this.showSaleSummary(result);
            // Focus en búsqueda tras pago
            const searchInput = document.getElementById('product-search');
            if (searchInput) searchInput.focus();
        }, 1000);
    }

    showConfetti() {
        tpvSounds.pay.play();
        // Crear confeti simple con CSS
        const confetti = document.createElement('div');
        confetti.className = 'fixed inset-0 pointer-events-none z-50';
        confetti.innerHTML = Array.from({length: 50}, () => 
            `<div class="absolute w-2 h-2 bg-yellow-400 rounded-full animate-bounce" 
                  style="left: ${Math.random() * 100}%; top: ${Math.random() * 100}%; animation-delay: ${Math.random() * 2}s;"></div>`
        ).join('');
        
        document.body.appendChild(confetti);
        
        setTimeout(() => {
            confetti.remove();
        }, 3000);
    }

    showSaleSummary(result) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50 animate-fade-in';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-900 rounded-xl shadow-2xl p-8 w-full max-w-md">
                <div class="text-center">
                    <div class="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-2">Sale Completed!</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-4">Sale #${result.sale_number}</p>
                    <div class="text-2xl font-bold text-gray-900 dark:text-white mb-6">$${result.total.toFixed(2)}</div>
                    <button onclick="this.closest('.fixed').remove()" class="w-full py-2 rounded-lg bg-gradient-to-r from-orange-400 to-orange-600 text-white font-bold hover:scale-105 transition">
                        Continue
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    clearCart() {
        this.cart = [];
        this.updateCartDisplay();
    }

    async loadInitialProducts() {
        try {
            const response = await fetch('/sales/api/products/');
            const products = await response.json();
            this.displayProductList(products);
        } catch (error) {
            console.error('Error loading products:', error);
        }
    }

    displayProductList(products) {
        const productList = document.getElementById('product-list');
        if (!productList) return;

        productList.innerHTML = products.map(product => `
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                <td class="px-4 py-3">
                    <div>
                        <div class="font-medium text-gray-900 dark:text-white">${product.name}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${product.sku || 'No SKU'}</div>
                    </div>
                </td>
                <td class="px-4 py-3 text-gray-900 dark:text-white font-semibold">$${product.price}</td>
                <td class="px-4 py-3">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${product.stock > 10 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : product.stock > 0 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}">
                        ${product.stock || 0}
                    </span>
                </td>
                <td class="px-4 py-3">
                    <button onclick="tpv.addToCart(${product.id})" 
                            class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800 transition">
                        <svg class="w-4 h-4 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                        </svg>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    animateAddToCart() {
        // Animación simple de éxito
        const payBtn = document.getElementById('pay-btn');
        if (payBtn) {
            payBtn.classList.add('scale-105');
            setTimeout(() => {
                payBtn.classList.remove('scale-105');
            }, 200);
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg text-white font-medium animate-fade-in`;
        
        switch (type) {
            case 'success':
                toast.classList.add('bg-green-500');
                tpvSounds.success.play();
                break;
            case 'error':
                toast.classList.add('bg-red-500');
                tpvSounds.error.play();
                break;
            case 'warning':
                toast.classList.add('bg-yellow-500');
                break;
            default:
                toast.classList.add('bg-blue-500');
        }
        
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
}

// Sonidos de feedback: éxito, error, escaneo, pago
// Los archivos deben estar en /static/sales/sounds/ y pueden ser reemplazados por sonidos personalizados.
// Hotkeys: F2 (buscar), F4 (pago), Enter (confirmar pago), ESC (cancelar pago), + y - (cantidad)
const tpvSounds = {
    success: new Audio('/static/sales/sounds/success.mp3'),
    error: new Audio('/static/sales/sounds/error.mp3'),
    scan: new Audio('/static/sales/sounds/scan.mp3'),
    pay: new Audio('/static/sales/sounds/pay.mp3'),
};

// --- HOTKEYS Y TECLAS RÁPIDAS ---
document.addEventListener('keydown', (e) => {
    // Si el modal de pago está abierto
    const paymentModal = document.getElementById('payment-modal');
    if (paymentModal && !paymentModal.classList.contains('hidden')) {
        if (e.key === 'Escape') {
            tpv.hidePaymentModal();
        }
        if (e.key === 'Enter') {
            const paymentForm = document.getElementById('payment-form');
            if (paymentForm) paymentForm.requestSubmit();
        }
        return;
    }
    // Hotkeys globales
    if (e.key === 'F2') {
        e.preventDefault();
        const searchInput = document.getElementById('product-search');
        if (searchInput) searchInput.focus();
    }
    if (e.key === 'F4') {
        e.preventDefault();
        tpv.showPaymentModal();
    }
    if ((e.key === '+' || e.key === '-') && document.activeElement.classList.contains('quantity-display')) {
        const index = parseInt(document.activeElement.dataset.index);
        if (!isNaN(index)) {
            tpv.updateQuantity(index, e.key === '+' ? 1 : -1);
        }
    }
});

// --- SOPORTE PARA ESCÁNER DE CÓDIGO DE BARRAS ---
// Input invisible para capturar códigos de barras
const barcodeInput = document.createElement('input');
barcodeInput.type = 'text';
barcodeInput.id = 'barcode-scanner-input';
barcodeInput.autocomplete = 'off';
barcodeInput.style.position = 'absolute';
barcodeInput.style.opacity = 0;
barcodeInput.style.pointerEvents = 'none';
document.body.appendChild(barcodeInput);

let barcodeBuffer = '';
let barcodeTimeout = null;

document.addEventListener('keydown', (e) => {
    // Si es un número o Enter, agregar al buffer
    if (/^[0-9]$/.test(e.key)) {
        barcodeBuffer += e.key;
        clearTimeout(barcodeTimeout);
        barcodeTimeout = setTimeout(() => {
            barcodeBuffer = '';
        }, 100);
    } else if (e.key === 'Enter' && barcodeBuffer.length >= 6) {
        // Simular búsqueda automática por código de barras
        tpv.searchProducts(barcodeBuffer);
        tpvSounds.scan.play();
        barcodeBuffer = '';
    }
});

// Inicializar TPV cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.tpv = new TPV();
    // Modal de ayuda de hotkeys y sonidos
    const helpBtn = document.getElementById('tpv-help-btn');
    const helpModal = document.getElementById('tpv-help-modal');
    const helpClose = document.getElementById('tpv-help-close');
    if (helpBtn && helpModal && helpClose) {
        helpBtn.addEventListener('click', () => {
            helpModal.classList.remove('hidden');
        });
        helpClose.addEventListener('click', () => {
            helpModal.classList.add('hidden');
        });
        helpModal.addEventListener('click', (e) => {
            if (e.target === helpModal) helpModal.classList.add('hidden');
        });
    }
});

// Agregar estilos CSS para animaciones
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fade-in {
        animation: fade-in 0.3s ease-out;
    }
    
    .animate-bounce {
        animation: bounce 1s infinite;
    }
    
    @keyframes bounce {
        0%, 20%, 53%, 80%, 100% {
            transform: translate3d(0,0,0);
        }
        40%, 43% {
            transform: translate3d(0, -30px, 0);
        }
        70% {
            transform: translate3d(0, -15px, 0);
        }
        90% {
            transform: translate3d(0, -4px, 0);
        }
    }
`;
document.head.appendChild(style); 
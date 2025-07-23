// TPV Synap - Lógica principal

// Búsqueda de productos
function searchProducts() {
    const search = document.getElementById('product-search').value;
    fetch(`/sales/pos/api/products/?search=${encodeURIComponent(search)}`)
        .then(res => res.json())
        .then(data => renderProducts(data.products));
}

// Renderizar productos en el grid
function renderProducts(products) {
    const grid = document.querySelector('.product-grid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!products.length) {
        grid.innerHTML = '<div class="text-center text-gray-400 dark:text-gray-500 py-8">No hay productos para mostrar.</div>';
        return;
    }
    products.forEach(product => {
        const card = document.createElement('div');
        card.className = 'bg-white dark:bg-gray-800 rounded-lg shadow p-3 flex flex-col items-center cursor-pointer hover:scale-105 transition relative';
        if (product.has_multiple_variants) {
            card.onclick = () => openVariantModal(product);
        } else {
            card.onclick = () => addToCart(product.id, false, product.stock);
        }
        card.innerHTML = `
            <img src="${product.image_url}" alt="${product.name}" class="h-24 w-24 object-contain mb-2">
            <span class="text-sm font-medium text-gray-900 dark:text-white mb-1">${product.name}</span>
            <span class="text-xs text-gray-500 dark:text-gray-300 mb-1">${product.code}</span>
            <span class="text-xs text-gray-500 dark:text-gray-300 mb-1">Stock: ${product.stock}</span>
            <span class="text-base font-bold text-orange-600">$${parseFloat(product.price).toFixed(2)}</span>
            ${product.has_multiple_variants ? `<span class="absolute top-2 right-2 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 text-[10px] px-2 py-0.5 rounded-full flex items-center gap-1"><span class="material-icons text-xs align-middle">tune</span> Variantes</span>` : ''}
        `;
        grid.appendChild(card);
    });
}

// Al cargar la página, renderizar productos iniciales
if (window.initialProducts) {
    renderProducts(window.initialProducts);
}
console.log('window.initialProducts:', window.initialProducts);

// Agregar producto al carrito
function addToCart(productId, isVariant = false, stock = null) {
    // Validar stock antes de enviar
    if (stock !== null && parseInt(stock) <= 0) {
        showToast('Sin stock disponible', true);
        return;
    }
    fetch('/sales/pos/api/cart/add/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({product_id: productId, quantity: 1, is_variant: isVariant})
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, true);
        } else {
            updateCart(data.cart, data.cart_subtotal, data.cart_discount, data.cart_total);
        }
    });
}

// Actualizar carrito
function updateCart(cart, subtotal, discount, total) {
    const cartPanel = document.querySelector('aside.w-80');
    if (!cartPanel) return;
    const cartList = cartPanel.querySelector('.flex-1 ul');
    const cartEmpty = cartPanel.querySelector('.flex-1 > div');
    // Limpiar lista
    if (cartList) cartList.innerHTML = '';
    if (cart && cart.length > 0) {
        if (cartEmpty) cartEmpty.style.display = 'none';
        let html = '';
        cart.forEach(line => {
            html += `<li class="flex items-center justify-between bg-gray-50 dark:bg-gray-900 rounded p-2">
                <div>
                    <span class="font-medium text-gray-900 dark:text-white">${line.product}</span>
                    <span class="block text-xs text-gray-500 dark:text-gray-300">x${line.quantity}</span>
                </div>
                <div class="flex flex-col items-end">
                    <span class="text-sm font-bold text-orange-600">$${line.subtotal.toFixed(2)}</span>
                    <div class="flex gap-1 mt-1">
                        <button class="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-xs" onclick="editQty(${line.id}, -1)">-</button>
                        <button class="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-xs" onclick="editQty(${line.id}, 1)">+</button>
                        <button class="px-2 py-1 rounded bg-blue-200 dark:bg-blue-800 text-xs" onclick="editDiscount(${line.id})">% Disc</button>
                        <button class="px-2 py-1 rounded bg-gray-300 dark:bg-gray-600 text-xs" onclick="editPrice(${line.id})">$</button>
                        <button class="px-2 py-1 rounded bg-red-200 dark:bg-red-800 text-xs" onclick="removeLine(${line.id})">&times;</button>
                    </div>
                </div>
            </li>`;
        });
        if (cartList) cartList.innerHTML = html;
    } else {
        if (cartList) cartList.innerHTML = '';
        if (cartEmpty) cartEmpty.style.display = '';
    }
    // Actualizar totales
    if (typeof subtotal !== 'undefined') {
        const subtotalEl = cartPanel.querySelector('span:has-text("Subtotal") + span');
        if (subtotalEl) subtotalEl.textContent = `$${parseFloat(subtotal).toFixed(2)}`;
    }
    if (typeof discount !== 'undefined') {
        const discountEl = cartPanel.querySelector('span:has-text("Descuento") + span');
        if (discountEl) discountEl.textContent = `-$${parseFloat(discount).toFixed(2)}`;
    }
    if (typeof total !== 'undefined') {
        const totalEl = cartPanel.querySelector('span:has-text("Total") + span');
        if (totalEl) totalEl.textContent = `$${parseFloat(total).toFixed(2)}`;
    }
}

// Confirmar pago
function confirmPayment() {
    const total = parseFloat(document.getElementById('payment-amount').value);
    const split = document.getElementById('split-payment').checked;
    let payments = [];
    if (split) {
        document.querySelectorAll('.split-payment-row').forEach(row => {
            const method = row.querySelector('.split-method').value;
            const amount = parseFloat(row.querySelector('.split-amount').value);
            if (amount > 0) {
                payments.push({method, amount});
            }
        });
    } else {
        const method = document.getElementById('payment-method').value;
        payments.push({method, amount: total});
    }
    // Validar suma
    const sum = payments.reduce((acc, p) => acc + p.amount, 0);
    if (Math.abs(sum - total) > 0.01) {
        showToast('El monto pagado no coincide con el total', true);
        return;
    }
    fetch('/sales/pos/api/payment/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({payments: payments})
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast('Venta completada');
            closePaymentModal();
            // Limpiar carrito, recargar productos, mostrar confetti, etc.
            setTimeout(() => { window.location.reload(); }, 1200);
        } else {
            showToast(data.error, true);
        }
    });
}

// Editar cantidad de línea
function editQty(lineId, delta) {
    fetch('/sales/pos/api/cart/update/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({line_id: lineId, quantity: delta})
    })
    .then(res => res.json())
    .then(data => updateCart(data.cart));
}

// Eliminar línea del carrito
function removeLine(lineId) {
    fetch('/sales/pos/api/cart/remove/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
        body: JSON.stringify({line_id: lineId})
    })
    .then(res => res.json())
    .then(data => updateCart(data.cart));
}

// Abrir modal de pago
function openPaymentModal() {
    document.getElementById('payment-modal').classList.remove('hidden');
    // Rellenar importe y métodos de pago si es necesario
}

// Cerrar modal de pago
function closePaymentModal() {
    document.getElementById('payment-modal').classList.add('hidden');
}

// Modal de selección de variante
let currentProductVariants = [];
let selectedVariantId = null;

function openVariantModal(product) {
    // Guardar variantes en variable global temporal
    currentProductVariants = product.variants.filter(v => v.stock > 0);
    selectedVariantId = null;
    // Renderizar atributos
    const attrDiv = document.getElementById('variant-attributes');
    attrDiv.innerHTML = '';
    if (currentProductVariants.length > 0 && currentProductVariants[0].attributes.length > 0) {
        // Mostrar los nombres de los atributos
        let attrs = currentProductVariants[0].attributes.map(a => a.attribute__name);
        attrDiv.innerHTML = attrs.map(a => `<span class='inline-block bg-gray-100 dark:bg-gray-700 text-xs text-gray-700 dark:text-gray-200 rounded px-2 py-1 mr-2 mb-1'>${a}</span>`).join('');
    }
    // Renderizar opciones de variante
    const optionsDiv = document.getElementById('variant-options');
    optionsDiv.innerHTML = '';
    if (currentProductVariants.length === 0) {
        optionsDiv.innerHTML = `<div class='text-center text-gray-400 dark:text-gray-500 py-4'>No hay variantes disponibles con stock.</div>`;
    } else {
        currentProductVariants.forEach(variant => {
            const label = variant.attributes.map(a => `${a.value}`).join(' / ');
            const btn = document.createElement('button');
            btn.className = `w-full px-3 py-2 rounded border border-gray-300 dark:border-gray-700 mb-1 text-sm flex justify-between items-center`;
            btn.innerHTML = `<span>${label || variant.sku}</span><span class='text-xs text-gray-400'>${variant.stock} stock</span>`;
            btn.onclick = () => selectVariant(variant.id, btn, variant.stock);
            optionsDiv.appendChild(btn);
        });
    }
    // Deshabilitar botón de agregar
    document.getElementById('variant-add-btn').disabled = true;
    document.getElementById('variant-modal').classList.remove('hidden');
}

function selectVariant(variantId, btn, stock) {
    selectedVariantId = variantId;
    // Quitar selección previa
    document.querySelectorAll('#variant-options button').forEach(b => b.classList.remove('ring-2', 'ring-orange-500'));
    btn.classList.add('ring-2', 'ring-orange-500');
    // Habilitar botón de agregar si hay stock
    document.getElementById('variant-add-btn').disabled = stock <= 0;
}

document.getElementById('variant-add-btn').onclick = function() {
    if (!selectedVariantId) return;
    addToCart(selectedVariantId, true);
    closeVariantModal();
};

function closeVariantModal() {
    document.getElementById('variant-modal').classList.add('hidden');
    currentProductVariants = [];
    selectedVariantId = null;
}

// Utilidad para CSRF
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Toasts visuales
function showToast(msg, error=false) {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded shadow-lg text-sm font-medium ${error ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`;
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.classList.add('opacity-0'); setTimeout(() => toast.remove(), 1000); }, 2500);
}

// Eventos
if (document.getElementById('product-search')) {
    document.getElementById('product-search').addEventListener('input', searchProducts);
}
window.editQty = editQty;
window.editDiscount = editDiscount;
window.editPrice = editPrice;
window.removeLine = removeLine; 
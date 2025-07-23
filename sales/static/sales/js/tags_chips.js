// tags_chips.js
// Widget de selección múltiple de etiquetas tipo chips/autocomplete para Synap
// Sin dependencias externas, visual moderno, dark mode, UX Odoo-like

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.tag-select').forEach(function(select) {
        // Ocultar el select original
        select.style.display = 'none';
        // Crear el contenedor visual
        const container = document.createElement('div');
        container.className = 'tag-chips-container flex flex-wrap items-center gap-1 py-1 px-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md min-h-[2.2rem]';
        select.parentNode.insertBefore(container, select);
        // Crear input de búsqueda
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'tag-chip-input flex-1 bg-transparent border-none focus:outline-none text-xs py-1 px-1 dark:bg-gray-800';
        input.placeholder = select.getAttribute('placeholder') || 'Agregar etiqueta...';
        container.appendChild(input);
        // Dropdown de sugerencias
        let dropdown = null;
        let tagsCache = [];
        let selectedTags = Array.from(select.selectedOptions).map(opt => ({id: opt.value, text: opt.text, color: opt.dataset.color || '#f97316'}));
        renderChips();
        // Renderizar chips
        function renderChips() {
            // Eliminar chips previos
            container.querySelectorAll('.tag-chip').forEach(e => e.remove());
            selectedTags.forEach(tag => {
                const chip = document.createElement('span');
                chip.className = 'tag-chip inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mr-1 mb-1';
                chip.style.background = tag.color || '#f97316';
                chip.style.color = '#fff';
                chip.innerHTML = `<span>${tag.text}</span><button type="button" class="ml-1 focus:outline-none remove-chip" title="Eliminar">&times;</button>`;
                chip.querySelector('.remove-chip').addEventListener('click', function() {
                    selectedTags = selectedTags.filter(t => t.id !== tag.id);
                    updateSelect();
                    renderChips();
                });
                container.insertBefore(chip, input);
            });
        }
        // Actualizar el select original
        function updateSelect() {
            Array.from(select.options).forEach(opt => opt.selected = false);
            selectedTags.forEach(tag => {
                let opt = Array.from(select.options).find(o => o.value == tag.id);
                if (!opt) {
                    opt = new Option(tag.text, tag.id, true, true);
                    opt.selected = true;
                    select.appendChild(opt);
                } else {
                    opt.selected = true;
                }
            });
        }
        // Buscar etiquetas
        input.addEventListener('input', function() {
            const query = input.value.trim();
            if (dropdown) dropdown.remove();
            if (query.length < 1) return;
            dropdown = document.createElement('div');
            dropdown.className = 'tag-dropdown absolute z-50 mt-1 w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow text-xs';
            dropdown.style.minWidth = '10rem';
            dropdown.style.maxHeight = '180px';
            dropdown.style.overflowY = 'auto';
            container.appendChild(dropdown);
            // Buscar en cache primero
            let results = tagsCache.filter(t => t.text.toLowerCase().includes(query.toLowerCase()));
            // Si no hay suficientes, buscar en backend
            fetch(select.getAttribute('data-autocomplete-url') + '?q=' + encodeURIComponent(query))
                .then(r => r.json())
                .then(data => {
                    if (data.results) {
                        tagsCache = data.results;
                        results = data.results.filter(t => t.text.toLowerCase().includes(query.toLowerCase()));
                    }
                    renderDropdown(results, query);
                });
        });
        // Renderizar dropdown
        function renderDropdown(results, query) {
            if (!dropdown) return;
            dropdown.innerHTML = '';
            results.forEach(tag => {
                if (selectedTags.some(t => t.id == tag.id)) return;
                const item = document.createElement('div');
                item.className = 'tag-dropdown-item px-2 py-1 cursor-pointer hover:bg-orange-100 dark:hover:bg-orange-900 flex items-center';
                item.innerHTML = `<span class="inline-block w-3 h-3 rounded-full mr-2" style="background:${tag.color}"></span>${tag.text}`;
                item.addEventListener('click', function() {
                    selectedTags.push(tag);
                    updateSelect();
                    renderChips();
                    dropdown.remove();
                    input.value = '';
                });
                dropdown.appendChild(item);
            });
            // Opción para crear nueva etiqueta
            if (!results.some(t => t.text.toLowerCase() === query.toLowerCase()) && query.length > 1) {
                const createItem = document.createElement('div');
                createItem.className = 'tag-dropdown-item px-2 py-1 cursor-pointer bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900 dark:text-green-200 flex items-center';
                createItem.innerHTML = `<span class="inline-block w-3 h-3 rounded-full mr-2 bg-green-400"></span>Crear etiqueta "${query}"`;
                createItem.addEventListener('click', function() {
                    // Crear nueva etiqueta en backend
                    fetch('/sales/api/client-tags-create/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        },
                        body: JSON.stringify({name: query})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success && data.tag) {
                            selectedTags.push({id: data.tag.id, text: data.tag.name, color: data.tag.color});
                            updateSelect();
                            renderChips();
                        }
                        dropdown.remove();
                        input.value = '';
                    });
                });
                dropdown.appendChild(createItem);
            }
        }
        // Cerrar dropdown al hacer click fuera
        document.addEventListener('click', function(e) {
            if (dropdown && !container.contains(e.target)) {
                dropdown.remove();
            }
        });
        // Navegación por teclado (opcional)
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && !input.value && selectedTags.length > 0) {
                selectedTags.pop();
                updateSelect();
                renderChips();
            }
        });
    });
}); 
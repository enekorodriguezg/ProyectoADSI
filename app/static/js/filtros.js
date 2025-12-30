document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. PANEL DE FILTROS (ABRIR/CERRAR) ---
    const btn = document.getElementById('toggleFilters');
    const panel = document.getElementById('filterContent');

    if (btn && panel) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            panel.style.display = (panel.style.display === 'block') ? 'none' : 'block';
        });

        document.addEventListener('click', function(e) {
            if (!panel.contains(e.target) && e.target !== btn) {
                panel.style.display = 'none';
            }
        });
    }

    // --- 2. GESTIÓN DE TAG DE NOMBRE ---
    const nInput = document.getElementById('nombreInput');
    const nHidden = document.getElementById('nombreHidden');
    const nContainer = document.getElementById('nombreTags');

    function renderNombreTag() {
        nContainer.innerHTML = '';
        if (nHidden.value) {
            const tag = document.createElement('div');
            tag.className = 'tag';
            tag.innerHTML = `${nHidden.value} <span onclick="removeNombre()">×</span>`;
            nContainer.appendChild(tag);
        }
    }

    nInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (this.value.trim() !== "") {
                nHidden.value = this.value.trim();
                this.value = "";
                renderNombreTag();
            }
        }
    });

    // Definimos las funciones en el objeto window para que el HTML las encuentre
    window.removeNombre = function() {
        nHidden.value = "";
        renderNombreTag();
    };

    // --- 3. GESTIÓN DE TAGS MÚLTIPLES (TIPO Y HABILIDAD) ---
    function setupMultiSelect(inputId, hiddenId, containerId, listId) {
        const input = document.getElementById(inputId);
        const hidden = document.getElementById(hiddenId);
        const container = document.getElementById(containerId);
        const datalist = document.getElementById(listId);

        if (!input || !hidden || !container || !datalist) return;

        function render() {
            container.innerHTML = '';
            let items = hidden.value ? hidden.value.split(',').filter(x => x !== "") : [];

            items.forEach(item => {
                const tag = document.createElement('div');
                tag.className = 'tag';
                // Usamos una función global simplificada para borrar
                tag.innerHTML = `${item} <span onclick="deleteGlobalItem('${item}', '${hiddenId}')">×</span>`;
                container.appendChild(tag);
            });
        }

        input.addEventListener('input', function() {
            const val = this.value;
            const options = Array.from(datalist.options).map(o => o.value);
            let items = hidden.value ? hidden.value.split(',').filter(x => x !== "") : [];

            if (options.includes(val) && !items.includes(val)) {
                items.push(val);
                hidden.value = items.join(',');
                this.value = '';
                render();
            }
        });

        render();
    }

    // Función global para borrar cualquier item de tipo/habilidad
    window.deleteGlobalItem = function(val, hId) {
        const hField = document.getElementById(hId);
        let currentItems = hField.value.split(',').filter(x => x !== val && x !== "");
        hField.value = currentItems.join(',');

        // Enviamos el formulario automáticamente para que el filtro se actualice
        document.getElementById('pokemonFilterForm').submit();
    };

    // Inicializar
    renderNombreTag();
    setupMultiSelect('tipoInput', 'tipoHidden', 'tipoTags', 'lista-tipos');
    setupMultiSelect('habInput', 'habHidden', 'habTags', 'lista-habs');
});
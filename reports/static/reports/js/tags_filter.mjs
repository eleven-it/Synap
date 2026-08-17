/**
 * Filtros tipo tags (chips + desplegable con ✓) — misma UX que informes legacy/VO.
 * Extraído de dashboard.js para reutilizar en presupuesto y otros formularios.
 *
 * @param {string} fieldId - id del <select multiple> asociado
 * @param {string} [fieldType] - etiqueta de depuración (opcional)
 * @param {string|null} [mutualExcludePeerId] - id de otro select para exclusión mutua
 * @param {object} [options]
 * @param {number} [options.maxSelections=Infinity] - 1 = selección única (reemplaza chip anterior)
 * @param {string} [options.hiddenSyncSelector] - input oculto a sincronizar con el primer valor seleccionado
 * @param {boolean} [options.allowEmptyOption=false] - incluir opciones con value="" en el listado
 * @param {{ minChars: number, fetchFn: (q: string) => Promise<Array<{value: string|number, label: string}>> }} [options.remoteSearch]
 */

export function initializeTagsFilter(
  fieldId,
  fieldType,
  mutualExcludePeerId,
  options = {},
) {
  const maxSelections =
    typeof options.maxSelections === "number" && options.maxSelections > 0
      ? options.maxSelections
      : Infinity;
  const hiddenSyncEl = options.hiddenSyncSelector
    ? document.querySelector(options.hiddenSyncSelector)
    : null;
  const allowEmptyOption = !!options.allowEmptyOption;
  const remoteSearch = options.remoteSearch || null;

  const select = document.getElementById(fieldId);
  const container = document.getElementById(`${fieldId}_tags_container`);
  const chipsContainer = container?.querySelector(".tags-chips");
  const input = document.getElementById(`${fieldId}_search`);
  const dropdown = document.getElementById(`${fieldId}_dropdown`);

  if (!select || !container || !chipsContainer || !input || !dropdown) {
    return;
  }

  const peerSelect =
    mutualExcludePeerId && typeof mutualExcludePeerId === "string"
      ? document.getElementById(mutualExcludePeerId)
      : null;

  const getPeerExcludedValues = () => {
    if (!peerSelect) return new Set();
    return new Set(
      Array.from(peerSelect.selectedOptions)
        .map((o) => String(o.value || "").trim())
        .filter(Boolean),
    );
  };

  const filterPeerExcluded = (opts) => {
    const excl = getPeerExcludedValues();
    if (!excl.size) return opts;
    return opts.filter((opt) => !excl.has(String(opt.value)));
  };

  let allOptions = [];
  let selectedValues = new Set();
  let selectedIndex = -1;
  let searchTimeout = null;

  const syncHidden = () => {
    if (!hiddenSyncEl) return;
    if (selectedValues.size === 0) {
      hiddenSyncEl.value = "";
      return;
    }
    hiddenSyncEl.value = Array.from(selectedValues)[0];
  };

  const renderChips = () => {
    chipsContainer.innerHTML = "";
    selectedValues.forEach((value) => {
      const option = allOptions.find(
        (opt) => String(opt.value) === String(value),
      );
      if (option) {
        const chip = document.createElement("div");
        chip.className =
          "inline-flex items-center gap-1 px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 rounded-full text-xs font-medium";
        chip.dataset.value = value;

        const chipText = document.createElement("span");
        chipText.textContent = option.label;
        chip.appendChild(chipText);

        const chipRemove = document.createElement("button");
        chipRemove.type = "button";
        chipRemove.className =
          "ml-1 hover:text-sky-600 dark:hover:text-sky-300 focus:outline-none";
        chipRemove.innerHTML = "×";
        chipRemove.addEventListener("click", (e) => {
          e.stopPropagation();
          removeTag(value);
        });
        chip.appendChild(chipRemove);

        chipsContainer.appendChild(chip);
      }
    });
    syncHidden();
  };

  const ensureOption = (value, label) => {
    const v = String(value);
    let opt = Array.from(select.options).find((o) => o.value === v);
    if (!opt) {
      opt = document.createElement("option");
      opt.value = v;
      opt.textContent = label || v;
      select.appendChild(opt);
    } else if (label && opt.textContent !== label) {
      opt.textContent = label;
    }
    return opt;
  };

  const clearTagsForSingleMode = () => {
    if (maxSelections !== 1) return;
    selectedValues.clear();
    Array.from(select.options).forEach((opt) => {
      opt.selected = false;
    });
  };

  const addTag = (value, remoteLabel) => {
    const v = String(value);
    if (remoteLabel != null) {
      ensureOption(v, remoteLabel);
    }
    if (maxSelections === 1) {
      clearTagsForSingleMode();
    }
    if (!selectedValues.has(v)) {
      selectedValues.add(v);
      const option = Array.from(select.options).find((o) => o.value === v);
      if (option) {
        option.selected = true;
      } else {
        const o = ensureOption(v, remoteLabel || v);
        o.selected = true;
      }
      renderChips();
      input.value = "";
      hideDropdown();
      updateSelect();
    }
  };

  const removeTag = (value) => {
    selectedValues.delete(String(value));
    const option = Array.from(select.options).find((o) => o.value === String(value));
    if (option) {
      option.selected = false;
    }
    renderChips();
    updateSelect();
  };

  const dashboardRoot = document.querySelector("#dashboard-root");

  const updateSelect = () => {
    Array.from(select.options).forEach((opt) => {
      opt.selected = selectedValues.has(opt.value);
    });
    select.dispatchEvent(new Event("change", { bubbles: true }));
    syncHidden();
    if (typeof saveFilters === "function") {
      saveFilters();
    }
    if (fieldId === "stock_existencias_group_by") {
      if (typeof window.refetchStockExistenciasData === "function") {
        window.refetchStockExistenciasData();
      } else if (typeof window.renderStockExistenciasTableFromState === "function") {
        window.renderStockExistenciasTableFromState();
      }
      return;
    }
    const slug = dashboardRoot?.dataset?.reportSlug;
    if (
      typeof window.fetchDashboardData === "function" &&
      slug &&
      (slug === "uninvoiced_remitos" ||
        slug === "total-consolidado-operativo" ||
        slug === "stock-existencias" ||
        slug === "inventario-deposito-articulo" ||
        (typeof window.isVentasNetasSlug === "function" &&
          window.isVentasNetasSlug(slug)))
    ) {
      window.fetchDashboardData();
    }
  };

  const isDarkDropdown = () =>
    dropdown.dataset.tagsTheme === "dark" ||
    dropdown.classList.contains("tags-dropdown--theme-dark");

  const dropdownHintClass = () =>
    isDarkDropdown()
      ? "px-3 py-2 text-xs text-slate-400"
      : "px-3 py-2 text-xs text-slate-500 dark:text-slate-400";

  const dropdownItemClasses = (index, isSelected) => {
    const dark = isDarkDropdown();
    const base = "px-3 py-2 text-xs cursor-pointer transition-colors";
    const hover =
      index === selectedIndex
        ? dark
          ? "bg-sky-900/70"
          : "bg-sky-100 dark:bg-sky-900"
        : dark
          ? "hover:bg-slate-700"
          : "hover:bg-slate-100 dark:hover:bg-slate-700";
    const selected = isSelected
      ? dark
        ? "bg-sky-950/60"
        : "bg-sky-50 dark:bg-sky-950"
      : "";
    return `${base} ${hover} ${selected}`.trim();
  };

  const dropdownLabelClass = (isSelected) => {
    const dark = isDarkDropdown();
    if (isSelected) {
      return dark
        ? "font-medium text-sky-300"
        : "font-medium text-sky-700 dark:text-sky-300";
    }
    return dark ? "text-slate-200" : "text-slate-700 dark:text-slate-300";
  };

  const dropdownCheckClass = () =>
    isDarkDropdown()
      ? "text-sky-400"
      : "text-sky-600 dark:text-sky-400";

  const showDropdown = () => {
    dropdown.classList.remove("hidden");
  };

  const hideDropdown = () => {
    dropdown.classList.add("hidden");
    selectedIndex = -1;
  };

  const refreshDropdownIfPeerChanged = () => {
    if (dropdown.classList.contains("hidden")) return;
    const q = input.value.trim();
    const base =
      q.length === 0
        ? allOptions.slice(0, 20)
        : allOptions.filter((opt) => opt.label.toLowerCase().includes(q.toLowerCase()));
    renderDropdown(filterPeerExcluded(base), q);
  };

  const renderDropdown = (results, query) => {
    dropdown.innerHTML = "";

    if (results.length === 0) {
      const noResults = document.createElement("div");
      noResults.className = dropdownHintClass();
      noResults.textContent = query ? "No se encontraron resultados" : "Escribe para buscar...";
      dropdown.appendChild(noResults);
      return;
    }

    results.forEach((item, index) => {
      const vKey = String(item.value);
      const isSelected = selectedValues.has(vKey);
      const itemDiv = document.createElement("div");
      itemDiv.className = dropdownItemClasses(index, isSelected);
      itemDiv.dataset.value = vKey;

      const itemContent = document.createElement("div");
      itemContent.className = "flex items-center justify-between";

      const itemLabel = document.createElement("span");
      itemLabel.className = dropdownLabelClass(isSelected);
      itemLabel.textContent = item.label;
      itemContent.appendChild(itemLabel);

      if (isSelected) {
        const checkIcon = document.createElement("span");
        checkIcon.className = dropdownCheckClass();
        checkIcon.textContent = "✓";
        itemContent.appendChild(checkIcon);
      }

      itemDiv.appendChild(itemContent);

      itemDiv.addEventListener("click", () => {
        if (selectedValues.has(vKey)) {
          removeTag(vKey);
        } else {
          addTag(vKey, item.label);
        }
      });

      dropdown.appendChild(itemDiv);
    });

    showDropdown();
  };

  const searchOptions = (query) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const filtered = allOptions.filter((opt) =>
        opt.label.toLowerCase().includes(query.toLowerCase()),
      );
      renderDropdown(filterPeerExcluded(filtered), query);
    }, 150);
  };

  let lastRemoteResults = [];

  if (remoteSearch) {
    const { minChars, fetchFn } = remoteSearch;
    const runRemote = (q) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(async () => {
        try {
          const rows = await fetchFn(q);
          const mapped = (rows || []).map((r) => ({
            value: String(r.value),
            label: r.label,
          }));
          lastRemoteResults = mapped;
          renderDropdown(mapped, q);
        } catch {
          lastRemoteResults = [];
          renderDropdown([], q);
        }
      }, 280);
    };

    input.addEventListener("input", (e) => {
      const q = e.target.value.trim();
      if (q.length < minChars) {
        dropdown.innerHTML = "";
        const hint = document.createElement("div");
        hint.className = dropdownHintClass();
        hint.textContent = `Escriba al menos ${minChars} caracteres...`;
        dropdown.appendChild(hint);
        showDropdown();
        return;
      }
      runRemote(q);
    });

    input.addEventListener("focus", () => {
      const q = input.value.trim();
      if (q.length >= minChars) {
        runRemote(q);
      } else {
        dropdown.innerHTML = "";
        const hint = document.createElement("div");
        hint.className = dropdownHintClass();
        hint.textContent = `Escriba al menos ${minChars} caracteres...`;
        dropdown.appendChild(hint);
        showDropdown();
      }
    });
  } else {
    input.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      if (query.length > 0) {
        searchOptions(query);
      } else {
        renderDropdown(filterPeerExcluded(allOptions.slice(0, 20)), "");
      }
    });

    input.addEventListener("focus", () => {
      if (input.value.trim().length === 0) {
        renderDropdown(filterPeerExcluded(allOptions.slice(0, 20)), "");
      } else {
        searchOptions(input.value.trim());
      }
    });
  }

  input.addEventListener("keydown", (e) => {
    const filteredLocal = filterPeerExcluded(
      allOptions.filter((opt) =>
        opt.label.toLowerCase().includes(input.value.toLowerCase()),
      ),
    );
    const listForKeys = remoteSearch ? lastRemoteResults : filteredLocal;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!listForKeys.length) return;
      selectedIndex = Math.min(selectedIndex + 1, listForKeys.length - 1);
      renderDropdown(listForKeys, input.value);
      const after = dropdown.querySelectorAll("[data-value]");
      after[selectedIndex]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!listForKeys.length) return;
      selectedIndex = Math.max(selectedIndex - 1, -1);
      renderDropdown(listForKeys, input.value);
      if (selectedIndex >= 0) {
        const after = dropdown.querySelectorAll("[data-value]");
        after[selectedIndex]?.scrollIntoView({ block: "nearest" });
      }
    } else if (e.key === "Enter") {
      const rows = dropdown.querySelectorAll("[data-value]");
      if (selectedIndex >= 0 && rows[selectedIndex]) {
        e.preventDefault();
        const value = rows[selectedIndex].dataset.value;
        const labelEl = rows[selectedIndex].querySelector("span");
        const label = labelEl ? labelEl.textContent : value;
        if (selectedValues.has(value)) {
          removeTag(value);
        } else {
          addTag(value, remoteSearch ? label : undefined);
        }
      }
    } else if (e.key === "Escape") {
      hideDropdown();
      input.blur();
    } else if (e.key === "Tab") {
      // Al tabular sin elegir, cerrar el listado (no preventDefault: el foco sigue).
      hideDropdown();
    }
  });

  input.addEventListener("blur", () => {
    // Delay para permitir click/mousedown en una opción del dropdown.
    setTimeout(() => {
      const active = document.activeElement;
      if (container.contains(active) || dropdown.contains(active)) return;
      hideDropdown();
    }, 150);
  });

  document.addEventListener("click", (e) => {
    if (!container.contains(e.target) && !dropdown.contains(e.target)) {
      hideDropdown();
    }
  });

  const loadOptions = () => {
    allOptions = Array.from(select.options)
      .filter((opt) => allowEmptyOption || opt.value !== "")
      .map((opt) => ({
        value: opt.value,
        label: opt.textContent,
      }));

    selectedValues = new Set(
      Array.from(select.selectedOptions)
        .filter((opt) => allowEmptyOption || opt.value !== "")
        .map((opt) => opt.value),
    );

    renderChips();
  };

  const observer = new MutationObserver(() => {
    loadOptions();
  });
  observer.observe(select, { childList: true, subtree: true });

  select.addEventListener("change", () => {
    loadOptions();
  });

  if (peerSelect) {
    peerSelect.addEventListener("change", refreshDropdownIfPeerChanged);
  }

  loadOptions();
}

if (typeof window !== "undefined") {
  window.initializeTagsFilter = initializeTagsFilter;
}

// Comentario: Controlador básico para dashboards interactivos con gráficos D3.

const dashboardRoot = document.querySelector("#dashboard-root");

const widgetDataCache = new Map();
let resizeObserver = null;

const COLORS = [
  "#38bdf8",
  "#818cf8",
  "#f97316",
  "#10b981",
  "#f472b6",
  "#facc15",
];

const formatNumber = (value) => {
  if (typeof value === "number") {
    try {
      return new Intl.NumberFormat(
        document.documentElement.lang || "es-AR",
        { maximumFractionDigits: 2 }
      ).format(value);
    } catch (e) {
      return value.toFixed(2);
    }
  }
  return value;
};

const toTitle = (value) =>
  String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

const getBounding = (element) => {
  const rect = element.getBoundingClientRect();
  const width = rect.width || element.clientWidth || 640;
  const height = rect.height || width * 0.55 || 360;
  return { width, height };
};

const parseDateIfPossible = (value) => {
  const parsed = Date.parse(value);
  if (!Number.isNaN(parsed)) {
    return new Date(parsed);
  }
  if (typeof value === "string" && value.includes("W")) {
    const [year, weekLabel] = value.split("-W");
    if (year && weekLabel) {
      const week = Number.parseInt(weekLabel, 10) || 1;
      const simple = new Date(Number(year), 0, 1 + (week - 1) * 7);
      return simple;
    }
  }
  return value;
};

const discoverNumericFields = (rows) => {
  if (!rows || !rows.length) return [];
  const sample = rows[0];
  return Object.keys(sample).filter((key) => typeof sample[key] === "number");
};

const getWidgetConfig = (widget) => {
  const configId = widget.dataset.widgetConfigId;
  if (!configId) return {};
  const script = document.getElementById(configId);
  if (!script) return {};
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.warn("No se pudo parsear configuración del widget", error);
    return {};
  }
};

const ensureVisible = (element) => {
  element.classList.remove("hidden");
  element.classList.remove("opacity-0");
};

const renderLineChart = (container, data, config, fillArea = false) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const configuredY = config.y_fields || (config.y_field ? [config.y_field] : []);
  const yFields = configuredY.length ? configuredY : discoverNumericFields(data);
  if (!yFields.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xValues = data.map((row) => parseDateIfPossible(row[xField] ?? row[xField.toLowerCase()]));
  const isTimeScale = xValues.every((value) => value instanceof Date);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const xScale = isTimeScale
    ? d3.scaleTime().domain(d3.extent(xValues)).range([margin.left, margin.left + innerWidth])
    : d3.scalePoint().domain(xValues).range([margin.left, margin.left + innerWidth]).padding(0.4);

  const yMax = d3.max(yFields, (field) => d3.max(data, (row) => Number(row[field]) || 0)) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const axisBottom = svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium");

  if (isTimeScale) {
    axisBottom.call(d3.axisBottom(xScale).ticks(5).tickFormat(d3.timeFormat("%d/%m")));
  } else {
    axisBottom.call(d3.axisBottom(xScale));
  }

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale).ticks(5));

  yFields.forEach((field, index) => {
    const line = d3
      .line()
      .defined((row) => row[field] !== null && row[field] !== undefined)
      .x((row, idx) => xScale(xValues[idx]))
      .y((row) => yScale(Number(row[field]) || 0));

    if (fillArea && index === 0) {
      const area = d3
        .area()
        .defined((row) => row[field] !== null && row[field] !== undefined)
        .x((row, idx) => xScale(xValues[idx]))
        .y0(() => yScale(0))
        .y1((row) => yScale(Number(row[field]) || 0));

      svg
        .append("path")
        .datum(data)
        .attr("fill", d3.color(COLORS[index % COLORS.length]).copy({ opacity: 0.2 }))
        .attr("d", area);
    }

    svg
      .append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", COLORS[index % COLORS.length])
      .attr("stroke-width", 2.5)
      .attr("d", line);
  });
};

const renderBarChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }
  const xField = config.x_field || Object.keys(data[0])[0];
  const yFieldCandidate = config.y_field || (config.y_fields ? config.y_fields[0] : null);
  const yField = yFieldCandidate || discoverNumericFields(data)[0];
  if (!yField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const aggregated = Object.values(
    data.reduce((acc, row) => {
      const key = row[xField] ?? row[xField.toLowerCase()] ?? "Sin categoría";
      if (!acc[key]) {
        acc[key] = { label: key, value: 0 };
      }
      acc[key].value += Number(row[yField]) || 0;
      return acc;
    }, {})
  );

  const xScale = d3
    .scaleBand()
    .domain(aggregated.map((item) => item.label))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.3);

  const yMax = d3.max(aggregated, (item) => item.value) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale).ticks(5));

  svg
    .selectAll("rect")
    .data(aggregated)
    .join("rect")
    .attr("x", (item) => xScale(item.label))
    .attr("y", (item) => yScale(item.value))
    .attr("width", xScale.bandwidth())
    .attr("height", (item) => margin.top + innerHeight - yScale(item.value))
    .attr("rx", 6)
    .attr("fill", COLORS[0]);
};

const renderStackedBarChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const valueField = config.y_field || config.value_field || discoverNumericFields(data)[0];
  if (!valueField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const stackField =
    config.stack_field || Object.keys(data[0]).find((key) => key !== xField && key !== valueField && typeof data[0][key] === "string");
  const grouped = d3.group(data, (row) => row[xField] ?? "Sin categoría");
  const keys = Array.from(new Set(Array.from(grouped.values()).flat().map((row) => row[stackField] ?? "Total")));

  const stackedData = Array.from(grouped, ([key, rows]) => {
    const base = { x: key };
    keys.forEach((stackKey) => {
      base[stackKey] = rows
        .filter((row) => (row[stackField] ?? "Total") === stackKey)
        .reduce((sum, row) => sum + (Number(row[valueField]) || 0), 0);
    });
    return base;
  });

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(stackedData.map((item) => item.x))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.3);

  const stackGenerator = d3.stack().keys(keys);
  const series = stackGenerator(stackedData);

  const yMax = d3.max(series, (serie) => d3.max(serie, (d) => d[1])) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale).ticks(5));

  svg
    .append("g")
    .selectAll("g")
    .data(series)
    .join("g")
    .attr("fill", (_, index) => COLORS[index % COLORS.length])
    .selectAll("rect")
    .data((serie) => serie)
    .join("rect")
    .attr("x", (d) => xScale(d.data.x))
    .attr("y", (d) => yScale(d[1]))
    .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
    .attr("width", xScale.bandwidth())
    .attr("rx", 6);
};

const renderHeatmap = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const yField = config.y_field || Object.keys(data[0])[1];
  const valueField = config.value_field || discoverNumericFields(data)[0];

  const xKeys = Array.from(new Set(data.map((row) => row[xField] ?? "-")));
  const yKeys = Array.from(new Set(data.map((row) => row[yField] ?? "-")));

  const { width, height } = getBounding(container);
  const margin = { top: 40, right: 24, bottom: 40, left: 80 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3.scaleBand().domain(xKeys).range([margin.left, margin.left + innerWidth]).padding(0.1);
  const yScale = d3.scaleBand().domain(yKeys).range([margin.top, margin.top + innerHeight]).padding(0.1);

  const values = data.map((row) => Number(row[valueField]) || 0);
  const color = d3
    .scaleSequential(d3.interpolateBlues)
    .domain([d3.min(values) || 0, d3.max(values) || 1]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale));

  svg
    .append("g")
    .selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", (row) => xScale(row[xField] ?? "-"))
    .attr("y", (row) => yScale(row[yField] ?? "-"))
    .attr("width", xScale.bandwidth())
    .attr("height", yScale.bandwidth())
    .attr("rx", 8)
    .attr("fill", (row) => color(Number(row[valueField]) || 0));
};

const renderGauge = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const valueField = config.value_field || discoverNumericFields(data)[0];
  const value = d3.mean(data, (row) => Number(row[valueField]) || 0) || 0;
  const min = config.min ?? 0;
  const max = config.max ?? 100;
  const qualifier = config.target ?? config.threshold ?? 95;

  const { width, height } = getBounding(container);
  const radius = Math.min(width, height) / 2 - 20;
  const centerX = width / 2;
  const centerY = height - 20;

  const scale = d3.scaleLinear().domain([min, max]).range([-Math.PI / 2, Math.PI / 2]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const arcBackground = d3.arc().innerRadius(radius - 20).outerRadius(radius).startAngle(-Math.PI / 2).endAngle(Math.PI / 2);

  svg
    .append("path")
    .attr("d", arcBackground())
    .attr("fill", "#1e293b")
    .attr("transform", `translate(${centerX}, ${centerY})`);

  const arcValue = d3.arc().innerRadius(radius - 20).outerRadius(radius).startAngle(-Math.PI / 2).endAngle(scale(value));

  svg
    .append("path")
    .attr("d", arcValue())
    .attr("fill", value >= qualifier ? "#22c55e" : "#f97316")
    .attr("transform", `translate(${centerX}, ${centerY})`);

  const needleAngle = scale(value);

  const needleLine = d3
    .line()
    .x((d) => d.x)
    .y((d) => d.y);

  const needle = [
    { x: centerX, y: centerY },
    { x: centerX + Math.cos(needleAngle) * (radius - 10), y: centerY + Math.sin(needleAngle) * (radius - 10) },
  ];

  svg
    .append("path")
    .attr("d", needleLine(needle))
    .attr("stroke", "#f8fafc")
    .attr("stroke-width", 4)
    .attr("stroke-linecap", "round");

  svg
    .append("text")
    .attr("x", centerX)
    .attr("y", centerY + 28)
    .attr("class", "text-base font-semibold fill-white")
    .attr("text-anchor", "middle")
    .text(`${formatNumber(value)}${config.unit ? ` ${config.unit}` : ""}`);
};

const renderWaterfall = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const sequence = config.sequence || Object.keys(data[0]);
  const baseRow = data[0];
  const steps = sequence
    .map((key, index) => ({
      key,
      value: Number(baseRow[key]) || 0,
      type: index === 0 ? "initial" : index === sequence.length - 1 ? "total" : "delta",
    }))
    .filter((step) => !Number.isNaN(step.value));

  let cumulative = 0;
  const nodes = steps.map((step) => {
    const start = step.type === "initial" ? 0 : cumulative;
    cumulative = step.type === "delta" ? cumulative + step.value : step.value;
    return {
      ...step,
      start,
      end: step.type === "delta" ? cumulative : step.value,
    };
  });

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(nodes.map((node) => node.key))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.4);

  const yMin = Math.min(0, d3.min(nodes, (node) => Math.min(node.start, node.end)) || 0);
  const yMax = d3.max(nodes, (node) => Math.max(node.start, node.end)) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([yMin, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale));

  svg
    .selectAll("rect")
    .data(nodes)
    .join("rect")
    .attr("x", (node) => xScale(node.key))
    .attr("y", (node) => yScale(Math.max(node.start, node.end)))
    .attr("height", (node) => Math.abs(yScale(node.start) - yScale(node.end)))
    .attr("width", xScale.bandwidth())
    .attr("fill", (node, index) => {
      if (node.type === "total") return "#0ea5e9";
      return node.end >= node.start ? COLORS[index % COLORS.length] : "#f97316";
    })
    .attr("rx", 6);
};

const renderCards = (container, data, config) => {
  ensureVisible(container);
  const numericFields = config.fields || discoverNumericFields(data);
  if (!numericFields.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas</p>";
    return;
  }
  const row = data[0] || {};

  const wrapper = d3.select(container).html("");
  const grid = wrapper
    .append("div")
    .attr(
      "class",
      "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 h-full"
    );

  numericFields.forEach((field, index) => {
    grid
      .append("div")
      .attr(
        "class",
        "flex flex-col justify-center rounded-2xl bg-slate-900/90 dark:bg-slate-800/90 text-white px-4 py-6 shadow-lg"
      )
      .html(`
        <span class="text-[10px] uppercase tracking-[0.3em] text-slate-400 mb-2">${toTitle(field)}</span>
        <span class="text-2xl font-semibold">${formatNumber(Number(row[field]) || 0)}</span>
      `)
      .style("border-left", `4px solid ${COLORS[index % COLORS.length]}`);
  });
};

const renderAreaChart = (container, data, config) => {
  renderLineChart(container, data, config, true);
};

const renderLollipopChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const valueField = config.y_field || discoverNumericFields(data)[0];
  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const sorted = [...data].sort((a, b) => (Number(a[valueField]) || 0) - (Number(b[valueField]) || 0));

  const yScale = d3
    .scaleBand()
    .domain(sorted.map((row) => row[xField]))
    .range([margin.top, margin.top + innerHeight])
    .padding(0.5);

  const xScale = d3
    .scaleLinear()
    .domain([0, d3.max(sorted, (row) => Number(row[valueField]) || 0) || 1])
    .nice()
    .range([margin.left, margin.left + innerWidth]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale));

  svg
    .selectAll("line.lollipop")
    .data(sorted)
    .join("line")
    .attr("class", "lollipop")
    .attr("x1", xScale(0))
    .attr("x2", (row) => xScale(Number(row[valueField]) || 0))
    .attr("y1", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("y2", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("stroke", "#334155")
    .attr("stroke-width", 2);

  svg
    .selectAll("circle.lollipop")
    .data(sorted)
    .join("circle")
    .attr("class", "lollipop")
    .attr("cx", (row) => xScale(Number(row[valueField]) || 0))
    .attr("cy", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("r", 8)
    .attr("fill", (_, index) => COLORS[index % COLORS.length]);
};

const renderBulletChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const valueField = config.value_field || discoverNumericFields(data)[0];
  const targetField = config.target_field || config.target || "target";
  const row = data[0];
  const value = Number(row[valueField]) || 0;
  const target = Number(row[targetField]) || value * 1.1;
  const max = Math.max(value, target) * 1.15;

  const { width, height } = getBounding(container);
  const margin = { top: 32, right: 24, bottom: 32, left: 72 };

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const scale = d3.scaleLinear().domain([0, max]).range([margin.left, width - margin.right]);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", height / 2 - 18)
    .attr("width", scale(max) - margin.left)
    .attr("height", 36)
    .attr("rx", 12)
    .attr("fill", "#1e293b");

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", height / 2 - 12)
    .attr("width", Math.max(scale(value) - margin.left, 0))
    .attr("height", 24)
    .attr("rx", 10)
    .attr("fill", "#38bdf8");

  svg
    .append("line")
    .attr("x1", scale(target))
    .attr("x2", scale(target))
    .attr("y1", height / 2 - 22)
    .attr("y2", height / 2 + 22)
    .attr("stroke", "#f97316")
    .attr("stroke-width", 4)
    .attr("stroke-linecap", "round");

  svg
    .append("text")
    .attr("x", scale(value))
    .attr("y", height / 2 - 24)
    .attr("class", "text-xs font-semibold fill-white")
    .attr("text-anchor", "end")
    .text(formatNumber(value));

  svg
    .append("text")
    .attr("x", scale(target))
    .attr("y", height / 2 + 36)
    .attr("class", "text-xs font-semibold fill-white")
    .attr("text-anchor", "middle")
    .text(`Target ${formatNumber(target)}`);
};

const renderConnectedScatter = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const yField = config.y_field || discoverNumericFields(data)[0];
  const radiusField = config.radius_field || null;
  const labelField = config.label_field || xField;
  const showGrid = config.grid ?? true;
  const xLabel = config.x_label || toTitle(xField);
  const yLabel = config.y_label || toTitle(yField);

  const parsedData = data
    .map((row) => ({
      ...row,
      xValue: Number(row[xField]) || 0,
      yValue: Number(row[yField]) || 0,
      radiusValue: radiusField ? Number(row[radiusField]) || 0 : 0,
      labelValue: row[labelField],
    }))
    .sort((a, b) => a.xValue - b.xValue);

  const { width, height } = getBounding(container);
  const margin = { top: 40, right: 56, bottom: 64, left: 88 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleLinear()
    .domain(d3.extent(parsedData, (row) => row.xValue))
    .nice()
    .range([margin.left, margin.left + innerWidth]);

  const yScale = d3
    .scaleLinear()
    .domain(d3.extent(parsedData, (row) => row.yValue))
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const radiusScale = radiusField
    ? d3
        .scaleSqrt()
        .domain(d3.extent(parsedData, (row) => row.radiusValue))
        .range([6, 16])
    : () => 8;

  const line = d3
    .line()
    .curve(d3.curveCatmullRom.alpha(0.85))
    .x((row) => xScale(row.xValue))
    .y((row) => yScale(row.yValue));

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  if (showGrid) {
    svg
      .append("g")
      .attr("transform", `translate(0, ${margin.top + innerHeight})`)
      .attr("class", "pointer-events-none")
      .call(
        d3
          .axisBottom(xScale)
          .ticks(6)
          .tickSize(-innerHeight)
          .tickFormat("")
      )
      .call((axis) => axis.selectAll("line").attr("stroke", "rgba(148, 163, 184, 0.2)"))
      .call((axis) => axis.selectAll("path").remove());

    svg
      .append("g")
      .attr("transform", `translate(${margin.left}, 0)`)
      .attr("class", "pointer-events-none")
      .call(
        d3
          .axisLeft(yScale)
          .ticks(6)
          .tickSize(-innerWidth)
          .tickFormat("")
      )
      .call((axis) => axis.selectAll("line").attr("stroke", "rgba(148, 163, 184, 0.15)").attr("stroke-dasharray", "3 3"))
      .call((axis) => axis.selectAll("path").remove());
  }

  const xAxis = (g) =>
    g
      .attr("transform", `translate(0, ${margin.top + innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6, "%"))
      .call((axis) => axis.selectAll("text").attr("class", "fill-slate-400 text-[10px]"))
      .call((axis) => axis.selectAll("path,line").attr("stroke", "rgba(148, 163, 184, 0.35)"));

  const yAxis = (g) =>
    g
      .attr("transform", `translate(${margin.left}, 0)`)
      .call(d3.axisLeft(yScale).ticks(6, "%"))
      .call((axis) => axis.selectAll("text").attr("class", "fill-slate-400 text-[10px]"))
      .call((axis) => axis.selectAll("path,line").attr("stroke", "rgba(148, 163, 184, 0.35)"));

  svg.append("g").call(xAxis);
  svg.append("g").call(yAxis);

  svg
    .append("text")
    .attr("x", margin.left + innerWidth / 2)
    .attr("y", margin.top + innerHeight + 48)
    .attr("text-anchor", "middle")
    .attr("class", "text-xs font-semibold fill-slate-300")
    .text(xLabel);

  svg
    .append("text")
    .attr("transform", `translate(${margin.left - 56}, ${margin.top + innerHeight / 2}) rotate(-90)`)
    .attr("text-anchor", "middle")
    .attr("class", "text-xs font-semibold fill-slate-300")
    .text(yLabel);

  const path = svg
    .append("path")
    .datum(parsedData)
    .attr("fill", "none")
    .attr("stroke", "#38bdf8")
    .attr("stroke-width", 2.5)
    .attr("stroke-linejoin", "round")
    .attr("stroke-linecap", "round")
    .attr("d", line);

  const totalLength = path.node().getTotalLength();
  path
    .attr("stroke-dasharray", `${totalLength} ${totalLength}`)
    .attr("stroke-dashoffset", totalLength)
    .transition()
    .duration(1200)
    .ease(d3.easeCubicOut)
    .attr("stroke-dashoffset", 0);

  const nodes = svg
    .append("g")
    .selectAll("g")
    .data(parsedData)
    .join("g")
    .attr("transform", (row) => `translate(${xScale(row.xValue)}, ${yScale(row.yValue)})`);

  nodes
    .append("circle")
    .attr("r", 0)
    .attr("fill", "#0f172a")
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 2)
    .transition()
    .delay((_, index) => 200 + index * 60)
    .duration(600)
    .ease(d3.easeBackOut.overshoot(1.2))
    .attr("r", (row) => radiusScale(row.radiusValue));

  nodes
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", -6)
    .attr("opacity", 0)
    .attr("class", "text-[10px] font-semibold fill-white drop-shadow")
    .text((row) => row.labelValue)
    .transition()
    .delay((_, index) => 350 + index * 60)
    .duration(400)
    .attr("dy", (row) => -radiusScale(row.radiusValue) - 4)
    .attr("opacity", 1);
};

const renderUnsupportedChart = (container, type) => {
  container.innerHTML = `
    <div class="h-full w-full grid place-content-center text-xs text-slate-200 tracking-[0.2em] uppercase">
      ${type ? `Gráfico ${type} en desarrollo` : "Visualización no disponible"}
    </div>
  `;
};

const widgetRenderers = {
  "d3-line": (container, data, config) => renderLineChart(container, data, config),
  "d3-line-area": (container, data, config) => renderLineChart(container, data, config, true),
  "d3-bar": (container, data, config) => renderBarChart(container, data, config),
  "d3-bar-stacked": (container, data, config) => renderStackedBarChart(container, data, config),
  "d3-heatmap": (container, data, config) => renderHeatmap(container, data, config),
  "d3-gauge": (container, data, config) => renderGauge(container, data, config),
  "d3-waterfall": (container, data, config) => renderWaterfall(container, data, config),
  "d3-cards": (container, data, config) => renderCards(container, data, config),
  "d3-area": (container, data, config) => renderAreaChart(container, data, config),
  "d3-lollipop": (container, data, config) => renderLollipopChart(container, data, config),
  "d3-bullet": (container, data, config) => renderBulletChart(container, data, config),
  "d3-connected-scatter": (container, data, config) => renderConnectedScatter(container, data, config),
};

const renderChart = (widget, data, configParam) => {
  const container = widget.querySelector("[data-widget-content]");
  if (!container) return;
  const config = configParam || getWidgetConfig(widget);
  const type = widget.dataset.widgetType;
  const renderer = widgetRenderers[type];

  if (!data?.length) {
    container.innerHTML = `
      <div class="h-full w-full grid place-content-center text-xs text-slate-200 tracking-[0.2em] uppercase">
        Sin datos disponibles
      </div>
    `;
    return;
  }

  if (!window.d3) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Cargando librería D3...</p>";
    return;
  }

  if (renderer) {
    renderer(container, data, config);
  } else {
    renderUnsupportedChart(container, type);
  }
};

const renderTable = (widgetElement, data, options = {}) => {
  const show = options.show ?? false;
  const target = widgetElement.querySelector("[data-widget-table-wrapper]") || widgetElement;

  if (!show) {
    target.classList.add("hidden");
  }

  target.innerHTML = "";

  if (!data || !data.length) {
    const emptyMessage = widgetElement.dataset.emptyLabel || "Sin datos disponibles.";
    target.innerHTML = `<p class="text-sm text-slate-500 dark:text-slate-400">${emptyMessage}</p>`;
    return;
  }

  const table = document.createElement("table");
  table.className =
    "min-w-full text-[11px] text-left bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden";

  const thead = document.createElement("thead");
  thead.className =
    "bg-slate-50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-300 uppercase tracking-wide";
  const headerRow = document.createElement("tr");

  Object.keys(data[0]).forEach((key) => {
    const th = document.createElement("th");
    th.className = "px-4 py-3";
    th.textContent = key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  tbody.className = "divide-y divide-slate-100 dark:divide-slate-800";

  data.slice(0, 200).forEach((row) => {
    const tr = document.createElement("tr");
    tr.className =
      "hover:bg-slate-50/70 dark:hover:bg-slate-900/60 transition-colors";
    Object.values(row).forEach((value) => {
      const td = document.createElement("td");
      td.className = "px-4 py-3 text-slate-700 dark:text-slate-200";
      td.textContent = formatNumber(value);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  target.innerHTML = "";
  target.appendChild(table);

  if (show) {
    target.classList.remove("hidden");
  }
};

const attachTableToggle = (widget, data) => {
  const toggleButton = widget.querySelector("[data-toggle-table]");
  const tableWrapper = widget.querySelector("[data-widget-table-wrapper]");
  if (!toggleButton || !tableWrapper) return;

  const setButtonState = (label) => {
    toggleButton.innerHTML = label;
  };

  setButtonState(`
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Ver tabla
  `);
  tableWrapper.classList.add("hidden");

  toggleButton.onclick = () => {
    const isHidden = tableWrapper.classList.contains("hidden");
    if (isHidden) {
      renderTable(widget, data, { show: true });
      setButtonState(`
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M8 20h8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Ocultar tabla
      `);
    } else {
      tableWrapper.classList.add("hidden");
      setButtonState(`
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Ver tabla
      `);
    }
  };
};

const renderSummary = (meta, totals) => {
  const summaryContainer = document.querySelector("[data-summary-container]");
  const summaryGrid = document.querySelector("[data-summary-grid]");
  if (!summaryContainer || !summaryGrid) {
    return;
  }

  summaryGrid.innerHTML = "";

  const totalKeys = Object.keys(totals || {}).filter(
    (key) => typeof totals[key] === "number"
  );

  if (!totalKeys.length) {
    summaryContainer.classList.add("hidden");
    return;
  }

  totalKeys.forEach((key) => {
    const card = document.createElement("div");
    card.className =
      "rounded-2xl bg-slate-900 text-white dark:bg-slate-800 px-4 py-4 shadow-lg shadow-slate-900/20";
    card.innerHTML = `
        <p class="text-[10px] uppercase tracking-[0.25em] text-slate-300 mb-2">${toTitle(
      key
    )}</p>
        <p class="text-xl font-semibold">${formatNumber(totals[key])}</p>
      `;
    summaryGrid.appendChild(card);
  });

  summaryContainer.classList.remove("hidden");
};

const renderWidgets = (payload) => {
  const widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
  widgets.forEach((widget) => {
    const config = getWidgetConfig(widget);
    const cacheKey = widget.dataset.widgetId;
    widgetDataCache.set(cacheKey, { data: payload.data, config });

    renderChart(widget, payload.data, config);
    renderTable(widget, payload.data, { show: false });
    attachTableToggle(widget, payload.data);

    widget.querySelectorAll("[data-widget-note]").forEach((note) => note.remove());

    if (payload.notes && payload.notes.length) {
      const info = document.createElement("div");
      info.className =
        "px-6 py-4 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400";
      info.dataset.widgetNote = "true";
      const noteLabel = widget.dataset.noteLabel || "Notas";
      info.innerHTML = `<strong>${noteLabel}:</strong> ${payload.notes.join(
        " · "
      )}`;
      widget.appendChild(info);
    }
  });

  if (!resizeObserver && "ResizeObserver" in window) {
    resizeObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const widget = entry.target;
        const cacheKey = widget.dataset.widgetId;
        if (!cacheKey || !widgetDataCache.has(cacheKey)) {
          return;
        }
        const { data, config } = widgetDataCache.get(cacheKey);
        renderChart(widget, data, config);
      });
    });
  }

  if (resizeObserver) {
    widgets.forEach((widget) => resizeObserver.observe(widget));
  }
};

if (dashboardRoot) {
  const apiUrl = dashboardRoot.dataset.dashboardUrl;
  const reportSlug = dashboardRoot.dataset.reportSlug;

  const getCsrfToken = () => {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let i = 0; i < cookies.length; i += 1) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(`${name}=`)) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  };

  const toast = (message, type = "success") => {
    const container = document.createElement("div");
    container.className = `fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold tracking-wide ${
      type === "success"
        ? "bg-emerald-500 text-white"
        : "bg-rose-500 text-white"
    } animate-[fade-in_0.4s_ease-out]`;
    container.innerText = message;
    document.body.appendChild(container);
    setTimeout(() => {
      container.classList.add("animate-[fade-out_0.3s_ease-in_forwards]");
      container.addEventListener("animationend", () => container.remove());
    }, 2800);
  };

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug: reportSlug,
          limit: 200,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to load dashboard data");
      }

      const payload = await response.json();
      renderSummary(payload.meta || {}, payload.totals || {});
      renderWidgets(payload);
      toast("Datos del dashboard actualizados");
    } catch (error) {
      console.error(error);
      toast("Error al sincronizar datos", "error");
    }
  };

  window.addEventListener("orientationchange", () => {
    widgetDataCache.forEach((value, key) => {
      const widget = dashboardRoot.querySelector(`[data-widget-id="${key}"]`);
      if (widget) {
        renderChart(widget, value.data, value.config);
      }
    });
  });

  fetchDashboardData();
}



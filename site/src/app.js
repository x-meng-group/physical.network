const state = {
  datasets: [],
  meta: null,
  filters: {
    query: "",
    type: "all",
    format: "all",
  },
};

const formatLabels = {
  skeletonSwc: "SWC",
  mesh: "Mesh",
  pixelVoxelImage: "Image",
  treeGraph: "Tree",
};

const els = {
  heroStats: document.querySelector("#hero-stats"),
  heroThumbs: document.querySelector("#hero-thumbs"),
  grid: document.querySelector("#dataset-grid"),
  table: document.querySelector("#dataset-table"),
  search: document.querySelector("#search"),
  typeFilter: document.querySelector("#type-filter"),
  formatFilter: document.querySelector("#format-filter"),
  dialog: document.querySelector("#dataset-dialog"),
  dialogContent: document.querySelector("#dialog-content"),
  closeDialog: document.querySelector(".close-button"),
};

async function init() {
  const response = await fetch("public/data/datasets.json");
  const data = await response.json();
  state.datasets = data.datasets;
  state.meta = data.meta;

  renderHero();
  renderTypeOptions();
  render();
  bindEvents();
}

function bindEvents() {
  els.search.addEventListener("input", (event) => {
    state.filters.query = event.target.value.trim().toLowerCase();
    render();
  });

  els.typeFilter.addEventListener("change", (event) => {
    state.filters.type = event.target.value;
    render();
  });

  els.formatFilter.addEventListener("change", (event) => {
    state.filters.format = event.target.value;
    render();
  });

  els.closeDialog.addEventListener("click", () => els.dialog.close());
  els.dialog.addEventListener("click", (event) => {
    if (event.target === els.dialog) {
      els.dialog.close();
    }
  });
}

function renderHero() {
  const stats = state.meta.stats;
  const statItems = [
    ["Collections", stats.collections],
    ["SWC files", stats.swcFiles.toLocaleString()],
    ["Archive", `${stats.archiveMB.toLocaleString()} MB`],
    ["Uncompressed", `${stats.uncompressedGB} GB`],
  ];

  els.heroStats.innerHTML = statItems
    .map(([label, value]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`)
    .join("");

  els.heroThumbs.innerHTML = state.datasets
    .map((dataset) => `<img src="public/${dataset.assets.thumbnail}" alt="">`)
    .join("");
}

function renderTypeOptions() {
  const types = [...new Set(state.datasets.map((dataset) => dataset.originalDataType))].sort();
  els.typeFilter.insertAdjacentHTML(
    "beforeend",
    types.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join("")
  );
}

function render() {
  const datasets = filteredDatasets();
  renderCards(datasets);
  renderTable(datasets);
}

function filteredDatasets() {
  return state.datasets.filter((dataset) => {
    const queryTarget = [
      dataset.name,
      dataset.shortName,
      dataset.description,
      dataset.originalDataType,
      dataset.archive.folder,
      ...(dataset.tags || []),
    ]
      .join(" ")
      .toLowerCase();

    const matchesQuery = !state.filters.query || queryTarget.includes(state.filters.query);
    const matchesType =
      state.filters.type === "all" || dataset.originalDataType === state.filters.type;
    const matchesFormat =
      state.filters.format === "all" || dataset.formats[state.filters.format] === true;

    return matchesQuery && matchesType && matchesFormat;
  });
}

function renderCards(datasets) {
  if (!datasets.length) {
    els.grid.innerHTML = `<div class="empty">No datasets match the current filters.</div>`;
    return;
  }

  els.grid.innerHTML = datasets
    .map(
      (dataset) => `
        <article class="dataset-card" tabindex="0" data-slug="${dataset.slug}">
          <div class="card-media">
            <img src="public/${dataset.assets.thumbnail}" alt="${escapeHtml(dataset.name)} thumbnail">
          </div>
          <div class="card-body">
            <div class="tags">${dataset.tags.map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}</div>
            <h3>${escapeHtml(dataset.name)}</h3>
            <p>${escapeHtml(dataset.description)}</p>
            <div class="card-meta">
              <span class="pill yes">${escapeHtml(dataset.sampleCount)} samples</span>
              <span class="pill">${dataset.swcFileCount || 0} SWC files</span>
              <span class="pill">${escapeHtml(dataset.originalDataType)}</span>
            </div>
            <div class="format-list">${formatPills(dataset.formats)}</div>
          </div>
        </article>
      `
    )
    .join("");

  els.grid.querySelectorAll(".dataset-card").forEach((card) => {
    card.addEventListener("click", () => openDataset(card.dataset.slug));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openDataset(card.dataset.slug);
      }
    });
  });
}

function renderTable(datasets) {
  if (!datasets.length) {
    els.table.innerHTML = `<tr><td colspan="6" class="empty">No matching datasets.</td></tr>`;
    return;
  }

  els.table.innerHTML = datasets
    .map(
      (dataset) => `
        <tr data-slug="${dataset.slug}">
          <td><strong>${escapeHtml(dataset.name)}</strong><br><span>${escapeHtml(dataset.description)}</span></td>
          <td>${escapeHtml(dataset.sampleCount)}</td>
          <td>${dataset.swcFileCount || 0}</td>
          <td>${escapeHtml(dataset.originalDataType)}</td>
          <td><div class="format-list">${formatPills(dataset.formats)}</div></td>
          <td>${escapeHtml(dataset.archive.folder)}</td>
        </tr>
      `
    )
    .join("");

  els.table.querySelectorAll("tr[data-slug]").forEach((row) => {
    row.addEventListener("click", () => openDataset(row.dataset.slug));
  });
}

function formatPills(formats) {
  return Object.entries(formats)
    .map(([key, value]) => {
      const className = value === true ? "yes" : value === "na" ? "na" : "no";
      const suffix = value === true ? "" : value === "na" ? " N/A" : " no";
      return `<span class="pill ${className}">${formatLabels[key]}${suffix}</span>`;
    })
    .join("");
}

function openDataset(slug) {
  const dataset = state.datasets.find((item) => item.slug === slug);
  if (!dataset) {
    return;
  }

  const files = dataset.archive.representativeFiles.length
    ? dataset.archive.representativeFiles.map((file) => `<div>${escapeHtml(file)}</div>`).join("")
    : "<div>No representative files listed.</div>";

  els.dialogContent.innerHTML = `
    <div class="dialog-hero">
      <img src="public/${dataset.assets.thumbnail}" alt="${escapeHtml(dataset.name)} thumbnail">
      <div>
        <p class="eyebrow">${escapeHtml(dataset.shortName)}</p>
        <h2>${escapeHtml(dataset.name)}</h2>
        <p>${escapeHtml(dataset.description)}</p>
        <div class="format-list">${formatPills(dataset.formats)}</div>
      </div>
    </div>
    <div class="dialog-body">
      <div class="detail-grid">
        <div class="detail-item"><span>Samples</span><strong>${escapeHtml(dataset.sampleCount)}</strong></div>
        <div class="detail-item"><span>SWC files</span><strong>${dataset.swcFileCount || 0}</strong></div>
        <div class="detail-item"><span>Uncompressed</span><strong>${dataset.archive.uncompressedMB || 0} MB</strong></div>
        <div class="detail-item"><span>Original data</span><strong>${escapeHtml(dataset.originalDataType)}</strong></div>
        <div class="detail-item"><span>Archive folder</span><strong>${escapeHtml(dataset.archive.folder)}</strong></div>
        <div class="detail-item"><span>ZIP</span><strong>${escapeHtml(dataset.archive.zip)}</strong></div>
      </div>
      <div>
        <h3>Representative SWC Files</h3>
        <div class="file-list">${files}</div>
      </div>
      <div class="release-actions">
        <a class="button primary" href="${escapeAttribute(dataset.sourceLinks[0].url)}" rel="noreferrer">Original Source</a>
        <a class="button" href="${escapeAttribute(dataset.zenodo.recordUrl)}" rel="noreferrer">Zenodo Record</a>
      </div>
    </div>
  `;

  els.dialog.showModal();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

init().catch((error) => {
  document.body.innerHTML = `<main class="section"><h1>Unable to load site data</h1><p>${escapeHtml(error.message)}</p></main>`;
});

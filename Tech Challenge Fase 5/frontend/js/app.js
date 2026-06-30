const API_BASE = window.API_BASE || localStorage.getItem("api_base") || "";

const COMPONENT_ICONS = {
  user: "👤", web_browser: "🌐", mobile_app: "📱", api_gateway: "⚡",
  web_server: "🖥️", microservice: "🔧", database: "🗄️", cache: "⚡",
  message_queue: "📨", storage: "💾", cdn: "🌍", firewall: "🛡️",
  auth_service: "🔐", external_api: "🔌", monitoring: "📊", cloud_service: "☁️",
};

const STRIDE_META = [
  { key: "spoofing",               label: "S — Spoofing (Falsificação)",            color: "var(--stride-s)" },
  { key: "tampering",              label: "T — Tampering (Adulteração)",             color: "var(--stride-t)" },
  { key: "repudiation",            label: "R — Repudiation (Repúdio)",               color: "var(--stride-r)" },
  { key: "information_disclosure", label: "I — Information Disclosure (Divulgação)", color: "var(--stride-i)" },
  { key: "denial_of_service",      label: "D — Denial of Service (Negação)",         color: "var(--stride-d)" },
  { key: "elevation_of_privilege", label: "E — Elevation of Privilege (Elevação)",   color: "var(--stride-e)" },
];

const STRIDE_COLORS_HEX = {
  spoofing: "#8b5cf6", tampering: "#f97316", repudiation: "#06b6d4",
  information_disclosure: "#ec4899", denial_of_service: "#ef4444", elevation_of_privilege: "#eab308",
};

const LOCAL_DEFAULTS = {
  ollama:   { url: "http://localhost:11434",   model: "llava" },
  lmstudio: { url: "http://localhost:1234/v1", model: "local-model" },
};

// ─── State ────────────────────────────────────────────────────────────────────
let selectedFile = null;
let lastReport   = null;

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const dropzone        = document.getElementById("dropzone");
const fileInput       = document.getElementById("file-input");
const previewWrap     = document.getElementById("preview-wrap");
const previewImg      = document.getElementById("preview-img");
const previewName     = document.getElementById("preview-name");
const analyzeBtn      = document.getElementById("analyze-btn");
const providerSelect  = document.getElementById("provider-select");
const localConfig     = document.getElementById("local-config");
const localUrlInput   = document.getElementById("local-url");
const localModelInput = document.getElementById("local-model");
const uploadSection   = document.getElementById("upload-section");
const loadingSection  = document.getElementById("loading-section");
const resultsSection  = document.getElementById("results-section");
const toast           = document.getElementById("toast");
const toastBody       = document.getElementById("toast-body");

// ─── Init ─────────────────────────────────────────────────────────────────────
(async function init() {
  await loadProviders();
  updateLocalConfig();
})();

// ─── Provider loading ─────────────────────────────────────────────────────────
async function loadProviders() {
  try {
    const res = await fetch(`${API_BASE}/api/providers`);
    if (!res.ok) throw new Error();
    const providers = await res.json();
    providerSelect.innerHTML = "";
    providers.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.available ? p.name : `${p.name} (offline)`;
      opt.disabled = !p.available;
      providerSelect.appendChild(opt);
    });
    const first = providers.find(p => p.available);
    if (first) providerSelect.value = first.id;
  } catch { /* keep static defaults */ }
  updateLocalConfig();
}

providerSelect.addEventListener("change", () => {
  delete localUrlInput.dataset.userEdited;
  delete localModelInput.dataset.userEdited;
  updateLocalConfig();
});

function updateLocalConfig() {
  const provider = providerSelect.value;
  const isLocal  = provider === "ollama" || provider === "lmstudio";
  localConfig.style.display = isLocal ? "block" : "none";
  if (isLocal) {
    const d = LOCAL_DEFAULTS[provider];
    if (!localUrlInput.dataset.userEdited)   localUrlInput.value   = d.url;
    if (!localModelInput.dataset.userEdited) localModelInput.value = d.model;
    localUrlInput.placeholder   = d.url;
    localModelInput.placeholder = d.model;
  }
}

localUrlInput.addEventListener("input",   () => { localUrlInput.dataset.userEdited   = "1"; });
localModelInput.addEventListener("input", () => { localModelInput.dataset.userEdited = "1"; });

// ─── Drag and drop ────────────────────────────────────────────────────────────
dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", e => {
  e.preventDefault(); dropzone.classList.remove("drag-over");
  const f = e.dataTransfer.files[0]; if (f) setFile(f);
});
dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(file) {
  if (!file.type.startsWith("image/")) { showToast("Arquivo inválido", "Selecione PNG, JPG, JPEG ou WEBP."); return; }
  if (file.size > 20 * 1024 * 1024)   { showToast("Arquivo muito grande", "Máximo 20MB."); return; }
  selectedFile = file;
  analyzeBtn.disabled = false;
  const reader = new FileReader();
  reader.onload = e => {
    previewImg.src = e.target.result;
    previewName.textContent = `${file.name} — ${(file.size / 1024).toFixed(0)} KB`;
    previewWrap.classList.add("visible");
  };
  reader.readAsDataURL(file);
}

// ─── Analyze ──────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", runAnalysis);

async function runAnalysis() {
  if (!selectedFile) return;
  showLoading();

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("provider", providerSelect.value);
  const provider = providerSelect.value;
  if (provider === "ollama" || provider === "lmstudio") {
    const url   = localUrlInput.value.trim();
    const model = localModelInput.value.trim();
    if (url)   formData.append("local_url",   url);
    if (model) formData.append("local_model", model);
  }

  try {
    advanceStep(0);
    setTimeout(() => advanceStep(1), 3000);

    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Erro desconhecido");
    }

    const report = await res.json();
    lastReport = report;
    advanceStep(2);
    await delay(300);
    renderResults(report);
  } catch (err) {
    showUpload();
    showToast("Erro ao analisar imagem", err.message);
  }
}

// ─── Loading steps ────────────────────────────────────────────────────────────
const stepIds = ["step-1", "step-2", "step-3"];

function showLoading() {
  uploadSection.style.display  = "none";
  resultsSection.style.display = "none";
  loadingSection.style.display = "block";
  stepIds.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove("done", "active");
    el.querySelector(".step-icon").textContent = "·";
  });
  document.getElementById("step-1").classList.add("active");
  document.getElementById("step-1").querySelector(".step-icon").textContent = "⟳";
}

function advanceStep(index) {
  if (index > 0) {
    const prev = document.getElementById(stepIds[index - 1]);
    prev.classList.remove("active"); prev.classList.add("done");
    prev.querySelector(".step-icon").textContent = "✓";
  }
  if (index < stepIds.length) {
    const cur = document.getElementById(stepIds[index]);
    cur.classList.add("active");
    cur.querySelector(".step-icon").textContent = "⟳";
  }
}

// ─── Results rendering ────────────────────────────────────────────────────────
function renderResults(report) {
  loadingSection.style.display = "none";

  // Summary — render markdown paragraphs
  const summaryEl = document.getElementById("summary-text");
  summaryEl.innerHTML = "";
  renderMarkdownParagraphs(report.summary).forEach(p => summaryEl.appendChild(p));

  // Components
  const grid = document.getElementById("components-grid");
  grid.innerHTML = "";
  report.components.forEach(comp => {
    grid.appendChild(buildComponentCard(comp, computeComponentRisk(comp.id, report.stride_report)));
  });

  // STRIDE accordion
  const accordion = document.getElementById("stride-accordion");
  accordion.innerHTML = "";
  STRIDE_META.forEach(meta => {
    accordion.appendChild(buildStrideSection(meta, report.stride_report[meta.key] || []));
  });

  document.getElementById("provider-info").textContent =
    `Provider: ${report.provider_used} · Modelo: ${report.model_used}`;

  resultsSection.style.display = "block";
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

function renderMarkdownParagraphs(text) {
  return text.split(/\n{2,}/).map(block => {
    const p = document.createElement("p");
    // Convert **bold** → <strong> (content already safe via text nodes approach)
    p.innerHTML = esc(block.trim()).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return p;
  });
}

function computeComponentRisk(compId, strideReport) {
  const threats = Object.values(strideReport).flat().filter(t => t.component_id === compId);
  if (threats.some(t => t.risk_level === "critical")) return "critical";
  if (threats.some(t => t.risk_level === "high"))     return "high";
  if (threats.some(t => t.risk_level === "medium"))   return "medium";
  return "low";
}

function buildComponentCard(comp, risk) {
  const card = document.createElement("div");
  card.className = "component-card";
  card.innerHTML = `
    <span class="component-icon">${COMPONENT_ICONS[comp.type] || "☁️"}</span>
    <span class="component-name">${esc(comp.name)}</span>
    <span class="component-desc">${esc(comp.description)}</span>
    <span class="badge badge-${risk}">${risk.toUpperCase()} RISK</span>
  `;
  return card;
}

function buildStrideSection(meta, threats) {
  const section = document.createElement("div");
  section.className = "stride-section";

  const header = document.createElement("div");
  header.className = "stride-header";
  header.style.background = meta.color;
  header.innerHTML = `
    <span class="stride-header-left">
      <span>${esc(meta.label)}</span>
      <span class="stride-badge">${threats.length} ameaça${threats.length !== 1 ? "s" : ""}</span>
    </span>
    <span class="stride-chevron">▶</span>
  `;
  header.addEventListener("click", () => section.classList.toggle("open"));

  const body = document.createElement("div");
  body.className = "stride-body";

  if (threats.length === 0) {
    body.innerHTML = `<div class="threat-card" style="color:var(--text-secondary);font-size:.85rem;">Nenhuma ameaça identificada nesta categoria.</div>`;
  } else {
    threats.forEach(t => {
      const card = document.createElement("div");
      card.className = "threat-card";
      card.innerHTML = `
        <div class="threat-meta">
          <span class="threat-component">🔹 ${esc(t.component_name)}</span>
          <span class="badge badge-${t.risk_level}">${t.risk_level.toUpperCase()}</span>
        </div>
        <div class="threat-desc">${esc(t.threat)}</div>
        <div class="countermeasures-label">Contramedidas:</div>
        <ul class="countermeasures-list">
          ${t.countermeasures.map(c => `<li>${esc(c)}</li>`).join("")}
        </ul>
      `;
      body.appendChild(card);
    });
  }

  section.appendChild(header);
  section.appendChild(body);
  return section;
}

// ─── Actions ──────────────────────────────────────────────────────────────────
document.getElementById("download-btn").addEventListener("click", () => {
  if (!lastReport) return;
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: "application/json" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = "stride-report.json"; a.click();
  URL.revokeObjectURL(url);
});

document.getElementById("pdf-btn").addEventListener("click", () => {
  if (!lastReport) return;
  exportPDF(lastReport);
});

document.getElementById("reset-btn").addEventListener("click", () => {
  selectedFile = null; lastReport = null;
  analyzeBtn.disabled = true;
  previewWrap.classList.remove("visible");
  previewImg.src = ""; fileInput.value = "";
  showUpload();
});

function showUpload() {
  resultsSection.style.display = "none";
  loadingSection.style.display = "none";
  uploadSection.style.display  = "block";
}

// ─── PDF export ───────────────────────────────────────────────────────────────
function exportPDF(report) {
  const allThreats = Object.values(report.stride_report).flat();
  const critical   = allThreats.filter(t => t.risk_level === "critical").length;
  const high       = allThreats.filter(t => t.risk_level === "high").length;
  const date       = new Date().toLocaleDateString("pt-BR", { day:"2-digit", month:"2-digit", year:"numeric" });

  const riskBadge = r => {
    const colors = { low:"#10b981", medium:"#f59e0b", high:"#ef4444", critical:"#dc2626" };
    const fg     = (r === "low" || r === "medium") ? "#000" : "#fff";
    return `<span style="background:${colors[r]};color:${fg};padding:1px 7px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;">${r}</span>`;
  };

  const summaryHtml = esc(report.summary)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .split(/\n{2,}/).map(p => `<p>${p}</p>`).join("");

  const componentsHtml = report.components.map(c => {
    const risk = computeComponentRisk(c.id, report.stride_report);
    return `<tr>
      <td>${esc(c.name)}</td>
      <td style="color:#888;">${esc(c.type)}</td>
      <td>${esc(c.description)}</td>
      <td>${riskBadge(risk)}</td>
    </tr>`;
  }).join("");

  const strideHtml = STRIDE_META.map(meta => {
    const threats = report.stride_report[meta.key] || [];
    const color   = STRIDE_COLORS_HEX[meta.key];
    const rows    = threats.length === 0
      ? `<tr><td colspan="4" style="color:#888;font-style:italic;">Nenhuma ameaça identificada.</td></tr>`
      : threats.map(t => `<tr>
          <td>${esc(t.component_name)}</td>
          <td>${esc(t.threat)}</td>
          <td>${riskBadge(t.risk_level)}</td>
          <td>${t.countermeasures.map(c => esc(c)).join("<br>")}</td>
        </tr>`).join("");
    return `
      <h3 style="margin:24px 0 8px;padding:6px 12px;background:${color};color:#fff;border-radius:4px;font-size:13px;">
        ${esc(meta.label)} — ${threats.length} ameaça${threats.length !== 1 ? "s" : ""}
      </h3>
      <table>
        <thead><tr><th>Componente</th><th>Ameaça</th><th>Risco</th><th>Contramedidas</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }).join("");

  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Relatório STRIDE — ${date}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #111; padding: 2cm; }
    h1  { font-size: 20px; border-bottom: 2px solid #111; padding-bottom: 8px; margin-bottom: 4px; }
    h2  { font-size: 14px; margin: 20px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    h3  { font-size: 12px; }
    .meta { font-size: 11px; color: #666; margin-bottom: 20px; }
    .summary { background: #f4f7ff; border: 1px solid #c7d7f9; border-radius: 4px; padding: 12px 16px; margin-bottom: 8px; line-height: 1.6; }
    .summary p + p { margin-top: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 8px; }
    th { background: #f0f0f0; text-align: left; padding: 6px 8px; border: 1px solid #ddd; font-size: 11px; }
    td { padding: 5px 8px; border: 1px solid #e0e0e0; vertical-align: top; line-height: 1.4; }
    tr:nth-child(even) td { background: #fafafa; }
    @page { margin: 1.5cm; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <h1>Relatório de Modelagem de Ameaças STRIDE</h1>
  <div class="meta">
    Gerado em: ${date} &nbsp;|&nbsp; Provider: ${esc(report.provider_used)} &nbsp;|&nbsp;
    Modelo: ${esc(report.model_used)} &nbsp;|&nbsp;
    Total: ${allThreats.length} ameaças &nbsp;|&nbsp; Críticas: ${critical} &nbsp;|&nbsp; Altas: ${high}
  </div>

  <h2>Resumo Executivo</h2>
  <div class="summary">${summaryHtml}</div>

  <h2>Componentes Detectados (${report.components.length})</h2>
  <table>
    <thead><tr><th>Nome</th><th>Tipo</th><th>Descrição</th><th>Risco</th></tr></thead>
    <tbody>${componentsHtml}</tbody>
  </table>

  <h2>Análise STRIDE por Categoria</h2>
  ${strideHtml}

  <script>window.onload = () => { window.print(); }<\/script>
</body>
</html>`;

  const win = window.open("", "_blank", "width=900,height=700");
  win.document.write(html);
  win.document.close();
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(title, message) {
  document.getElementById("toast-title").textContent = title;
  toastBody.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 5000);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

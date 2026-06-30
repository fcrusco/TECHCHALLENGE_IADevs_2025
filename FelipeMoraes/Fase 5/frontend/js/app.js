const API_BASE = window.API_BASE || localStorage.getItem("api_base") || "http://localhost:8000";

const COMPONENT_ICONS = {
  user: "👤", web_browser: "🌐", mobile_app: "📱", api_gateway: "⚡",
  web_server: "🖥️", microservice: "🔧", database: "🗄️", cache: "⚡",
  message_queue: "📨", storage: "💾", cdn: "🌍", firewall: "🛡️",
  auth_service: "🔐", external_api: "🔌", monitoring: "📊", cloud_service: "☁️",
};

const STRIDE_META = [
  { key: "spoofing",              label: "S — Spoofing (Falsificação)",          color: "var(--stride-s)" },
  { key: "tampering",             label: "T — Tampering (Adulteração)",           color: "var(--stride-t)" },
  { key: "repudiation",           label: "R — Repudiation (Repúdio)",             color: "var(--stride-r)" },
  { key: "information_disclosure",label: "I — Information Disclosure (Divulgação)",color:"var(--stride-i)" },
  { key: "denial_of_service",     label: "D — Denial of Service (Negação)",       color: "var(--stride-d)" },
  { key: "elevation_of_privilege",label: "E — Elevation of Privilege (Elevação)", color: "var(--stride-e)" },
];

// ─── State ────────────────────────────────────────────────────────────────────
let selectedFile = null;
let lastReport = null;

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const dropzone      = document.getElementById("dropzone");
const fileInput     = document.getElementById("file-input");
const previewWrap   = document.getElementById("preview-wrap");
const previewImg    = document.getElementById("preview-img");
const previewName   = document.getElementById("preview-name");
const analyzeBtn    = document.getElementById("analyze-btn");
const providerSelect= document.getElementById("provider-select");
const uploadSection = document.getElementById("upload-section");
const loadingSection= document.getElementById("loading-section");
const resultsSection= document.getElementById("results-section");
const toast         = document.getElementById("toast");
const toastBody     = document.getElementById("toast-body");

const stepIds = ["step-1", "step-2", "step-3"];

// ─── Init ─────────────────────────────────────────────────────────────────────
(async function init() {
  await loadProviders();
})();

// ─── Provider loading ─────────────────────────────────────────────────────────
async function loadProviders() {
  try {
    const res = await fetch(`${API_BASE}/api/providers`);
    if (!res.ok) throw new Error("providers fetch failed");
    const providers = await res.json();

    providerSelect.innerHTML = "";
    providers.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.available ? p.name : `${p.name} (offline)`;
      opt.disabled = !p.available;
      providerSelect.appendChild(opt);
    });

    // Select first available
    const first = providers.find(p => p.available);
    if (first) providerSelect.value = first.id;
  } catch {
    // Backend not yet up — keep default option
  }
}

// ─── Drag and drop ────────────────────────────────────────────────────────────
dropzone.addEventListener("dragover", e => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

dropzone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
  if (!file.type.startsWith("image/")) {
    showToast("Arquivo inválido", "Selecione uma imagem PNG, JPG, JPEG ou WEBP.");
    return;
  }
  if (file.size > 20 * 1024 * 1024) {
    showToast("Arquivo muito grande", "O tamanho máximo permitido é 20MB.");
    return;
  }
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

  try {
    advanceStep(0); // step 1 done after 1s
    setTimeout(() => advanceStep(1), 3000); // step 2 at 3s

    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: formData });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Erro desconhecido");
    }

    const report = await res.json();
    lastReport = report;

    advanceStep(2);
    await delay(400);
    renderResults(report);
  } catch (err) {
    showUpload();
    showToast("Erro ao analisar imagem", err.message);
  }
}

// ─── Loading state ────────────────────────────────────────────────────────────
function showLoading() {
  uploadSection.classList.remove("visible");
  uploadSection.style.display = "none";
  resultsSection.classList.remove("visible");
  resultsSection.style.display = "none";
  loadingSection.style.display = "block";
  loadingSection.classList.add("visible");

  // Reset steps
  stepIds.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove("done", "active");
  });
  document.getElementById("step-1").classList.add("active");
  setStepIcon("step-1", "⟳");
  setStepIcon("step-2", "·");
  setStepIcon("step-3", "·");
}

function advanceStep(index) {
  if (index > 0) {
    const prev = document.getElementById(stepIds[index - 1]);
    prev.classList.remove("active");
    prev.classList.add("done");
    setStepIcon(stepIds[index - 1], "✓");
  }
  if (index < stepIds.length) {
    const cur = document.getElementById(stepIds[index]);
    cur.classList.add("active");
    setStepIcon(stepIds[index], "⟳");
  }
}

function setStepIcon(id, icon) {
  const el = document.getElementById(id);
  if (el) el.querySelector(".step-icon").textContent = icon;
}

// ─── Results rendering ────────────────────────────────────────────────────────
function renderResults(report) {
  loadingSection.classList.remove("visible");
  loadingSection.style.display = "none";

  // Summary
  document.getElementById("summary-text").textContent = report.summary;

  // Components
  const grid = document.getElementById("components-grid");
  grid.innerHTML = "";
  report.components.forEach(comp => {
    const risk = computeComponentRisk(comp.id, report.stride_report);
    grid.appendChild(buildComponentCard(comp, risk));
  });

  // STRIDE accordion
  const accordion = document.getElementById("stride-accordion");
  accordion.innerHTML = "";
  STRIDE_META.forEach(meta => {
    const threats = report.stride_report[meta.key] || [];
    accordion.appendChild(buildStrideSection(meta, threats));
  });

  // Provider info
  document.getElementById("provider-info").textContent =
    `Provider: ${report.provider_used} · Modelo: ${report.model_used}`;

  resultsSection.style.display = "block";
  resultsSection.classList.add("visible");
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

function computeComponentRisk(compId, strideReport) {
  const all = Object.values(strideReport).flat();
  const threats = all.filter(t => t.component_id === compId);
  if (threats.some(t => t.risk_level === "critical")) return "critical";
  if (threats.some(t => t.risk_level === "high"))     return "high";
  if (threats.some(t => t.risk_level === "medium"))   return "medium";
  if (threats.length > 0)                             return "low";
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
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "stride-report.json";
  a.click();
  URL.revokeObjectURL(url);
});

document.getElementById("reset-btn").addEventListener("click", () => {
  selectedFile = null;
  lastReport = null;
  analyzeBtn.disabled = true;
  previewWrap.classList.remove("visible");
  previewImg.src = "";
  fileInput.value = "";
  showUpload();
});

function showUpload() {
  resultsSection.classList.remove("visible");
  resultsSection.style.display = "none";
  loadingSection.classList.remove("visible");
  loadingSection.style.display = "none";
  uploadSection.style.display = "block";
  uploadSection.classList.add("visible");
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
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

# Spec: Frontend

## Visão Geral

SPA (Single Page Application) em HTML/CSS/JS puro. Sem framework, sem build step, sem node_modules.
Tema dark mode com paleta de segurança cibernética.

## Header

```
┌─────────────────────────────────────────────────────────┐
│  [LOGO FIAP]   Tech Challenge - Fase 5                  │
│                STRIDE Threat Modeling                   │
└─────────────────────────────────────────────────────────┘
```

- Logo FIAP: `../images/logo_fiap.png`, altura 48px, alinhado à esquerda
- Título: "Tech Challenge - Fase 5" em `h1`, subtítulo "STRIDE Threat Modeling" em `p`
- Fundo do header: `var(--bg-card)` com borda inferior sutil

## Paleta de Cores (CSS Custom Properties)

```css
:root {
  --bg-primary: #0a0e1a;      /* fundo geral */
  --bg-card: #111827;         /* cards e panels */
  --bg-elevated: #1f2937;     /* inputs, hover states */
  --border: #374151;          /* bordas sutis */
  --text-primary: #f9fafb;    /* texto principal */
  --text-secondary: #9ca3af;  /* texto secundário */
  --accent: #3b82f6;          /* azul — ações primárias */
  --accent-hover: #2563eb;
  --success: #10b981;         /* verde — low risk */
  --warning: #f59e0b;         /* amarelo — medium risk */
  --danger: #ef4444;          /* vermelho — high risk */
  --critical: #dc2626;        /* vermelho escuro — critical */
  --stride-s: #8b5cf6;        /* Spoofing — roxo */
  --stride-t: #f97316;        /* Tampering — laranja */
  --stride-r: #06b6d4;        /* Repudiation — ciano */
  --stride-i: #ec4899;        /* Information Disclosure — rosa */
  --stride-d: #ef4444;        /* Denial of Service — vermelho */
  --stride-e: #eab308;        /* Elevation of Privilege — amarelo */
}
```

## Layout das Seções

### Seção 1: Upload

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   Provider: [OpenAI ▾]                               │
│                                                      │
│  ┌─────────────────────────────────────────────┐     │
│  │                                             │     │
│  │   ☁  Arraste uma imagem aqui               │     │
│  │      ou clique para selecionar              │     │
│  │                                             │     │
│  │   PNG · JPG · JPEG · WEBP · máx 20MB       │     │
│  └─────────────────────────────────────────────┘     │
│                                                      │
│   [Preview da imagem quando selecionada]             │
│                                                      │
│              [ Analisar Diagrama ]                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Comportamentos:**
- Drag-and-drop: highlight com borda `var(--accent)` ao arrastar sobre a área
- Clique na área abre o file picker
- Preview: imagem redimensionada a max 300px height, mantendo aspect ratio
- Seletor de provider: `<select>` populado via `GET /api/providers`
- Providers indisponíveis aparecem desabilitados no select com "(offline)"
- Botão "Analisar" desabilitado se nenhum arquivo selecionado

### Seção 2: Loading State

Exibida enquanto aguarda resposta da API:

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│         ⟳  Analisando diagrama...                   │
│                                                      │
│   ✓ Identificando componentes de arquitetura         │
│   ⟳ Aplicando metodologia STRIDE...                 │
│   · Gerando relatório                                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Simulação de progresso em 3 etapas (1s, 3s depois do início, ao receber resposta).

### Seção 3: Resultado

Exibida após resposta bem-sucedida.

#### 3a. Resumo Executivo
Card com `summary` do backend. Background levemente destacado.

#### 3b. Componentes Detectados
Grid de cards, um por componente:
```
┌────────────────────┐
│ [ícone tipo]       │
│ API Gateway        │
│ Ponto de entrada   │
│ das req. externas  │
│                    │
│ ■ HIGH RISK        │
└────────────────────┘
```
Nível de risco calculado no frontend: componente é `critical` se tem ≥1 ameaça critical, `high` se tem ≥1 high, etc.

#### 3c. Relatório STRIDE por Categoria

Seis seções expansíveis (accordion), uma por categoria:

```
▶ S — Spoofing (Falsificação)   [3 ameaças]
▼ T — Tampering (Adulteração)   [2 ameaças]
  ┌──────────────────────────────────────────┐
  │ Componente: API Gateway                  │
  │ Ameaça: Manipulação de parâmetros HTTP   │
  │ Risco: HIGH                              │
  │ Contramedidas:                           │
  │   • Validação de input server-side       │
  │   • Assinar payloads críticos com HMAC   │
  └──────────────────────────────────────────┘
```

Cor do header da seção usa as variáveis `--stride-*`.

#### 3d. Ações
```
[ ↓ Baixar Relatório JSON ]   [ ↺ Nova Análise ]
```

## Ícones de Componentes

Usar emojis ou SVG inline simples (sem dependências externas):

| Tipo | Ícone |
|------|-------|
| user | 👤 |
| web_browser | 🌐 |
| mobile_app | 📱 |
| api_gateway | ⚡ |
| web_server | 🖥️ |
| microservice | 🔧 |
| database | 🗄️ |
| cache | ⚡ |
| message_queue | 📨 |
| storage | 💾 |
| cdn | 🌍 |
| firewall | 🛡️ |
| auth_service | 🔐 |
| external_api | 🔌 |
| monitoring | 📊 |
| cloud_service | ☁️ |

## Badges de Risco

```css
.badge-low      { background: var(--success); color: #000 }
.badge-medium   { background: var(--warning); color: #000 }
.badge-high     { background: var(--danger);  color: #fff }
.badge-critical { background: var(--critical); color: #fff; animation: pulse 1s infinite }
```

## Responsividade

- Desktop (>1024px): layout 2 colunas para componentes
- Tablet (768-1024px): 1 coluna, componentes em grid 2x
- Mobile (<768px): tudo em 1 coluna, header empilhado

## Mensagens de Erro

Toast notification no canto inferior direito:
```
┌──────────────────────────────────┐
│ ✕  Erro ao analisar imagem       │
│    Provider offline ou sem key   │
└──────────────────────────────────┘
```
Auto-dismiss após 5 segundos.

## Backend URL

```javascript
const API_BASE = "http://localhost:8000";
```
Configurável via `window.API_BASE` ou `localStorage.getItem('api_base')` para ambientes diferentes.

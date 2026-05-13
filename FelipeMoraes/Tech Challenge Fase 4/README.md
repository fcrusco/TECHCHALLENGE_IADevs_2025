# Tech Challenge Fase 4 — Análise de Vídeo Cirúrgico

Sistema modular de detecção e análise de vídeos cirúrgicos com YOLOv8, desenvolvido para o Tech Challenge Fase 4 (POSTECH IADT). Cobre quatro requisitos clínicos independentes, cada um com modelo próprio treinado, lógica de anomalia específica e relatórios automáticos em TXT, HTML e JSON.

---

## Modelos Gerados

| Modo CLI | Modelo | Classes Detectadas | Arquivo gerado |
|---|---|---|---|
| `instrumentos` | YOLOv8s fine-tuned | Pinca Grasper, Gancho, Tesoura, Clipador | `model/instrumentos/weights/best.pt` |
| `areas-criticas` | YOLOv8s fine-tuned | Ovario, Mama | `model/areas_criticas/weights/best.pt` |
| `sangramento` | YOLOv8s fine-tuned | Sangramento | `model/sangramento/weights/best.pt` |
| `automutilacao` | YOLOv8s fine-tuned | Faca_Lamina, Arma_Fogo | `model/automutilacao/weights/best.pt` |

---

## Datasets Utilizados

| Modelo | Dataset | Fonte | Endereço |
|---|---|---|---|
| `instrumentos` | Laparoscopic Instruments (Roboflow) | Roboflow Universe | https://universe.roboflow.com/laparoscopic-yolo/laparoscopy |
| `areas-criticas` | Breast Ultrasound Images | Kaggle | https://www.kaggle.com/datasets/aryashah2k/breast-ultrasound-images-dataset |
| `areas-criticas` | PCOS Detection (Ovário) | Kaggle | https://www.kaggle.com/datasets/anaghachoudhari/pcos-detection-using-ultrasound-images |
| `sangramento` | WCEBleedGen (Cápsula Endoscópica) | Kaggle | https://www.kaggle.com/datasets/darksoul007fedsdfds/wcebleedgen |
| `automutilacao` | Guns & Knives Detection | Kaggle | https://www.kaggle.com/datasets/iqmansingh/guns-knives-object-detection |

> **Roboflow:** requer chave de API gratuita em https://roboflow.com

---

## Requisitos do Sistema

- Python 3.10+
- PyTorch 2.x com suporte CUDA (recomendado para treinamento)
- GPU com mínimo 8 GB VRAM para `TRAIN_BATCH=8`
- ffmpeg instalado (necessário para re-encoding dos vídeos no notebook)

---

## Instalação

### 1. Criar ambiente virtual

```bash
python -m venv .venv
```

**Windows:**
```powershell
.\.venv\Scripts\activate
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciais

**Kaggle** — crie o arquivo `~/.kaggle/kaggle.json`:
```json
{"username": "seu_usuario", "key": "sua_chave_api"}
```

**Roboflow** — adicione a chave no arquivo `.env`:
```env
ROBOFLOW_API_KEY=sua_chave_aqui
```

---

## Configuração (`.env`)

O arquivo `.env` na raiz do projeto controla todos os parâmetros de treino e inferência. Os parâmetros por modelo sobrescrevem os globais.

```env
# Parâmetros globais de treinamento (fallback)
TRAIN_EPOCHS=150
TRAIN_IMGSZ=640
TRAIN_BATCH=8
TRAIN_PATIENCE=20
TRAIN_DEVICE=0            # 0 = primeira GPU | cpu = CPU
TRAIN_BASE_MODEL=yolov8s.pt

# Parâmetros individuais por modelo (exemplo: instrumentos)
INST_TRAIN_EPOCHS=150
INST_TRAIN_IMGSZ=800
INST_TRAIN_BATCH=8
INST_TRAIN_BASE_MODEL=yolov8s.pt

# Confiança de detecção por modelo
INST_CONFIDENCE=0.55
AREAS_CONFIDENCE=0.50
BLEED_CONFIDENCE=0.45
HARM_CONFIDENCE=0.40
```

---

## Execução via CLI (`app.py`)

### Download dos datasets

```bash
# Um modelo específico
python app.py download --mode instrumentos
python app.py download --mode areas-criticas
python app.py download --mode sangramento
python app.py download --mode automutilacao

# Todos de uma vez
python app.py download --mode todos
```

### Treinamento

```bash
# Um modelo específico
python app.py train --mode instrumentos
python app.py train --mode areas-criticas
python app.py train --mode sangramento
python app.py train --mode automutilacao

# Todos em sequência
python app.py train --mode todos
```

O modelo treinado é salvo em `model/{modo}/weights/best.pt`.

### Detecção em vídeo

```bash
# Detecção básica (abre janela de visualização)
python app.py detect --mode instrumentos   --video video.mp4
python app.py detect --mode areas-criticas --video video.mp4
python app.py detect --mode sangramento    --video video.mp4
python app.py detect --mode automutilacao  --video video.mp4

# Sem janela (modo headless — servidores, CI)
python app.py detect --mode sangramento --video video.mp4 --headless

# Com modelo alternativo
python app.py detect --mode instrumentos --video video.mp4 --model caminho/modelo.pt

# Todos os modelos em sequência sobre o mesmo vídeo
python app.py detect --mode todos --video video.mp4
```

### Saídas geradas por cada `detect`

```
saida/{modo}/
├── output.mp4        # Vídeo anotado com bounding boxes e barra de alerta
├── relatorio.txt     # Relatório completo em texto
├── relatorio.html    # Relatório visual com tabelas e nível de risco
└── relatorio.json    # Dados estruturados (integração com sistemas externos)
```

---

## Execução via Notebook (`analise_cirurgica.ipynb`)

O notebook integra download de vídeo, detecção e relatório em um único fluxo interativo.

### Pré-requisitos

- Jupyter instalado: `pip install jupyter` ou use a extensão Jupyter do VS Code
- Modelos já treinados em `model/{modo}/weights/best.pt`
- ffmpeg disponível no PATH (para exibição do vídeo no notebook)

### Passo a passo

**1.** Abra o notebook `analise_cirurgica.ipynb` no VS Code ou Jupyter Lab.

**2.** Na célula de **CONFIGURAÇÕES**, preencha:

```python
# Opção A — baixar do YouTube automaticamente:
YOUTUBE_URL = "https://www.youtube.com/watch?v=SEU_VIDEO"
VIDEO_LOCAL  = ""

# Opção B — usar vídeo local:
YOUTUBE_URL = ""
VIDEO_LOCAL  = "video_test.mp4"           # relativo à raiz do projeto
# VIDEO_LOCAL = r"C:\Videos\cirurgia.mp4" # ou caminho absoluto

# Modelo a executar:
MODO = "instrumentos"
# Opções: "todos" | "instrumentos" | "areas-criticas" | "sangramento" | "automutilacao"
```

**3.** Execute todas as células em sequência (**Run All**) ou célula a célula.

### O notebook executa automaticamente

| Célula | O que faz |
|---|---|
| Imports | Configura `sys.path` e importa módulos |
| Configurações | Lê `YOUTUBE_URL`, `VIDEO_LOCAL` e `MODO` |
| Configuração | Carrega `.env`, valida o modo, monta `_DETECTORS_CONFIG` |
| Fonte do Vídeo | Baixa do YouTube via `yt-dlp` **ou** usa arquivo local |
| Verificação dos Modelos | Confirma se `best.pt` existe para cada modo selecionado |
| Execução dos Detectores | Roda `detect_video()` em modo headless, coleta resultados |
| Geração do Relatório | Exibe tabelas markdown inline com métricas e anomalias |
| Exibição do Vídeo | Re-encoda para H.264 e exibe o vídeo anotado inline |

---

## Estrutura do Projeto

```
Tech Challenge Fase 4/
├── app.py                          # CLI principal (download / train / detect)
├── .env                            # Parâmetros de treino e detecção
├── requirements.txt
├── analise_cirurgica.ipynb         # Notebook interativo
│
├── download_dataset/               # Scripts de download e YAMLs
│   ├── download_instrumentos.py    # Roboflow: laparoscopic-yolo/laparoscopy
│   ├── download_areas_criticas.py  # Kaggle: breast-ultrasound + pcos-detection
│   ├── download_sangramento.py     # Kaggle: wcebleedgen
│   ├── download_automutilacao.py   # Kaggle: guns-knives-object-detection
│   ├── dataset_instrumentos.yaml
│   ├── dataset_areas_criticas.yaml
│   ├── dataset_sangramento.yaml
│   └── dataset_automutilacao.yaml
│
├── dataset/                        # Datasets de treino (gerados pelo download)
│   ├── dataset_instrumentos/
│   ├── dataset_areas_criticas/
│   ├── dataset_sangramento/
│   └── dataset_automutilacao/
│
├── model/                          # Modelos treinados
│   ├── instrumentos/weights/best.pt
│   ├── areas_criticas/weights/best.pt
│   ├── sangramento/weights/best.pt
│   └── automutilacao/weights/best.pt
│
├── saida/                          # Resultados das detecções
│   ├── instrumentos/
│   ├── areas_criticas/
│   ├── sangramento/
│   └── automutilacao/
│
└── src/
    ├── relatorio.py                # Geração de relatórios TXT / HTML / JSON
    └── detectors/
        ├── base.py                 # BaseDetector — lógica compartilhada e filtros
        ├── instrumentos.py         # InstrumentosDetector
        ├── areas_criticas.py       # AreasCriticasDetector
        ├── sangramento.py          # SangramentoDetector
        └── automutilacao.py        # AutomutilacaoDetector
```

---

## Lógica de Anomalias

### Instrumentos Cirúrgicos

| Tipo | Severidade | Gatilho |
|---|---|---|
| AUSÊNCIA | ALTO | 10 frames consecutivos sem instrumentos |
| AUSÊNCIA | CRÍTICO | 30 frames consecutivos sem instrumentos |
| EXCESSO | MÉDIO | Mais de 5 instrumentos simultâneos |
| VARIAÇÃO | MÉDIO | Delta > 3 em relação à média dos últimos 10 frames |

### Áreas Críticas (Ovário / Mama)

| Tipo | Severidade | Gatilho |
|---|---|---|
| AUSÊNCIA | ALTO | 10 frames sem estrutura anatômica visível |
| AUSÊNCIA | CRÍTICO | 30 frames sem estrutura anatômica visível |
| EXCESSO | MÉDIO | Mais de 2 estruturas detectadas simultaneamente |
| VARIAÇÃO | MÉDIO | Delta > 3 em relação à média recente |

### Sangramento

| Tipo | Severidade | Gatilho |
|---|---|---|
| SANGRAMENTO | MÉDIO | Primeiro frame com sangramento detectado |
| SANGRAMENTO | ALTO | 5 frames consecutivos com sangramento |
| SANGRAMENTO | CRÍTICO | 15 frames consecutivos com sangramento |

### Automutilação / Objetos Suspeitos

| Tipo | Severidade | Gatilho |
|---|---|---|
| OBJETO_SUSPEITO | MÉDIO | Primeiro frame com objeto cortante |
| OBJETO_SUSPEITO | ALTO | 3 frames consecutivos com objeto cortante |
| OBJETO_SUSPEITO | CRÍTICO | 8 frames consecutivos com objeto cortante |
| ARMA_DETECTADA | CRÍTICO | Qualquer frame com arma de fogo (imediato) |

---

## Critérios Clínicos Avaliados

Os relatórios consolidados (`--mode todos`) avaliam automaticamente quatro critérios clínicos:

| Critério | Modelos Envolvidos |
|---|---|
| Desvios em Procedimentos Obstétricos | `areas-criticas` + `sangramento` |
| Sinais de Complicações em Cirurgias Ginecológicas | `instrumentos` + `sangramento` + `areas-criticas` |
| Indicadores Visuais de Desconforto Psicológico | `automutilacao` (objetos cortantes) |
| Alertas para Possíveis Casos de Violência Doméstica | `automutilacao` (arma + objetos cortantes) |

---

## Relação com o Tech Challenge

| Requisito | Implementação |
|---|---|
| Detecção de instrumentos cirúrgicos | `--mode instrumentos` |
| Identificação de áreas críticas (ovário, mama) | `--mode areas-criticas` |
| Detecção de sangramento anômalo | `--mode sangramento` |
| Detecção de objetos suspeitos (automutilação/violência) | `--mode automutilacao` |
| Relatórios automáticos TXT / HTML / JSON | Todos os modos |
| Classificação de risco clínico (MÉDIO / ALTO / CRÍTICO) | Todos os modos |
| Notebook interativo com YouTube e vídeo local | `analise_cirurgica.ipynb` |
| Avaliação de critérios clínicos especializados | Relatório consolidado (`todos`) |

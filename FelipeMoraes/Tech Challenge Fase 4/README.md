# Tech Challenge Fase 4 — Análise de Vídeo Cirúrgico

Sistema modular de detecção e análise de vídeos cirúrgicos com YOLOv8, desenvolvido para o Tech Challenge Fase 4 (POSTECH IADT). Cobre quatro requisitos clínicos independentes, cada um com modelo próprio treinado, lógica de anomalia específica e relatórios automáticos.

---

## Modos de Detecção

| Modo | Classe(s) | Dataset (Kaggle) | Lógica de Alerta |
|---|---|---|---|
| `instrumentos` | Bisturi, Pinça, Tesoura Mayo Reta, Tesoura Mayo Curva | `dilavado/labeled-surgical-tools` | Ausência prolongada / excesso / variação brusca |
| `areas-criticas` | Ovário, Mama | `aryashah2k/breast-ultrasound-images-dataset` + `anaghachoudhari/pcos-detection-using-ultrasound-images` | Ausência de estruturas / múltiplas estruturas simultâneas |
| `sangramento` | Sangramento | `darksoul007fedsdfds/wcebleedgen` | Presença persistente (streak de frames) |
| `automutilacao` | Faca\_Lamina, Arma\_Fogo | `iqmansingh/guns-knives-object-detection` | Presença imediata (arma = CRÍTICO instantâneo) |

---

## Estrutura do Projeto

```
Tech Challenge Fase 4/
├── app.py                        # CLI principal
├── .env                          # Parâmetros de treino e detecção
├── requirements.txt
├── README.md
│
├── download_dataset/             # Scripts de download + YAMLs de configuração
│   ├── download_instrumentos.py
│   ├── download_areas_criticas.py
│   ├── download_sangramento.py
│   ├── download_automutilacao.py
│   ├── dataset_instrumentos.yaml
│   ├── dataset_areas_criticas.yaml
│   ├── dataset_sangramento.yaml
│   └── dataset_automutilacao.yaml
│
├── dataset/                      # Datasets de treino (gerados pelo download, não versionados)
│   ├── dataset_instrumentos/
│   ├── dataset_areas_criticas/
│   ├── dataset_sangramentos/
│   └── dataset_automutilacao/
│
├── model/                        # Modelos treinados (não versionados)
│   ├── instrumentos/weights/best.pt
│   ├── areas_criticas/weights/best.pt
│   ├── sangramento/weights/best.pt
│   └── automutilacao/weights/best.pt
│
└── src/
    ├── utils.py                  # Extração de frames
    ├── report.py                 # Geração de relatórios TXT / HTML / JSON
    └── detectors/
        ├── base.py               # BaseDetector — lógica compartilhada
        ├── instruments.py        # InstrumentDetector
        ├── critical_areas.py     # CriticalAreasDetector
        ├── bleeding.py           # BleedingDetector
        └── selfharm.py           # SelfHarmDetector
```

---

## Instalação

```bash
pip install -r requirements.txt
```

Requer credenciais do Kaggle configuradas em `~/.kaggle/kaggle.json` para o download dos datasets.

---

## Configuração (`.env`)

Todos os hiperparâmetros ficam no arquivo `.env` na raiz do projeto. Edite antes de treinar:

```env
# Treinamento
TRAIN_EPOCHS=50
TRAIN_IMGSZ=800
TRAIN_BATCH=8
TRAIN_PATIENCE=20
TRAIN_DEVICE=0          # 0 = GPU 0 | cpu = CPU
TRAIN_BASE_MODEL=yolov8m.pt

# Augmentações
AUGMENT_MOSAIC=1.0
AUGMENT_FLIPUD=0.3
AUGMENT_FLIPLR=0.5
AUGMENT_DEGREES=10.0
AUGMENT_TRANSLATE=0.1
AUGMENT_SCALE=0.5
AUGMENT_HSV_H=0.015
AUGMENT_HSV_S=0.7
AUGMENT_HSV_V=0.4

# Confiança por modo (substituem o padrão geral de 0.55)
INST_CONFIDENCE=0.55
AREAS_CONFIDENCE=0.50
BLEED_CONFIDENCE=0.45
HARM_CONFIDENCE=0.40
```

---

## Uso

### 1. Baixar datasets

**Um modo específico:**
```bash
python app.py download --mode instrumentos
python app.py download --mode areas-criticas
python app.py download --mode sangramento
python app.py download --mode automutilacao
```

**Todos de uma vez:**
```bash
python app.py download --mode todos
```

### 2. Treinar

```bash
python app.py train --mode instrumentos
python app.py train --mode areas-criticas
python app.py train --mode sangramento
python app.py train --mode automutilacao
```

O modelo treinado é salvo em `model/{modo}/weights/best.pt`.

### 3. Detectar em vídeo

```bash
python app.py detect --mode instrumentos   --video video.mp4
python app.py detect --mode areas-criticas --video video.mp4
python app.py detect --mode sangramento    --video video.mp4
python app.py detect --mode automutilacao  --video video.mp4
```

**Sem janela de visualização (servidor/CI):**
```bash
python app.py detect --mode sangramento --video video.mp4 --headless
```

**Com modelo alternativo:**
```bash
python app.py detect --mode instrumentos --video video.mp4 --model caminho/modelo.pt
```

### 4. Extrair frames de vídeo

```bash
python app.py extract --video video.mp4 --output frames/
```

---

## Saídas da Análise

Geradas na raiz do projeto após cada `detect`:

| Arquivo | Descrição |
|---|---|
| `output_{modo}.mp4` | Vídeo anotado com bounding boxes e barra de alerta |
| `report_{modo}.txt` | Relatório simplificado com lista de anomalias |
| `report_{modo}.html` | Relatório visual com tabela de risco clínico |
| `report_{modo}.json` | Dados estruturados para integração com sistemas hospitalares |

---

## Lógica de Anomalias por Modo

### Instrumentos
| Tipo | Severidade | Gatilho |
|---|---|---|
| AUSÊNCIA | ALTO | 10 frames consecutivos sem instrumentos |
| AUSÊNCIA | CRÍTICO | 30 frames consecutivos sem instrumentos |
| EXCESSO | MÉDIO | Mais de 5 instrumentos simultâneos |
| VARIAÇÃO | MÉDIO | Delta > 3 em relação à média dos últimos 10 frames |

### Áreas Críticas
| Tipo | Severidade | Gatilho |
|---|---|---|
| AUSÊNCIA | ALTO | 10 frames sem estrutura anatômica visível |
| AUSÊNCIA | CRÍTICO | 30 frames sem estrutura anatômica visível |
| EXCESSO | MÉDIO | Mais de 2 estruturas detectadas simultaneamente |

### Sangramento
| Tipo | Severidade | Gatilho |
|---|---|---|
| SANGRAMENTO | MÉDIO | Primeiro frame com sangramento detectado |
| SANGRAMENTO | ALTO | 5 frames consecutivos com sangramento |
| SANGRAMENTO | CRÍTICO | 15 frames consecutivos com sangramento |

### Automutilação
| Tipo | Severidade | Gatilho |
|---|---|---|
| OBJETO\_SUSPEITO | MÉDIO | Primeiro frame com objeto cortante |
| OBJETO\_SUSPEITO | ALTO | 3 frames consecutivos com objeto cortante |
| OBJETO\_SUSPEITO | CRÍTICO | 8 frames consecutivos com objeto cortante |
| ARMA\_DETECTADA | CRÍTICO | Qualquer frame com arma de fogo (imediato) |

---

## Requisitos do Sistema

- Python 3.10+
- PyTorch 2.x com CUDA (recomendado para treinamento)
- GPU com pelo menos 6 GB VRAM para `TRAIN_BATCH=8` e `TRAIN_IMGSZ=800`

---

## Relação com o Tech Challenge

| Requisito | Status |
|---|---|
| Detecção de instrumentos cirúrgicos | ✅ `--mode instrumentos` |
| Identificação de áreas críticas (ovário, mama) | ✅ `--mode areas-criticas` |
| Detecção de sangramento anômalo | ✅ `--mode sangramento` |
| Detecção de objetos suspeitos (automutilação) | ✅ `--mode automutilacao` |
| Relatórios automáticos TXT / HTML / JSON | ✅ todos os modos |
| Classificação de risco clínico (MÉDIO / ALTO / CRÍTICO) | ✅ todos os modos |

# Tech Challenge Fase 4 — Análise de Vídeo para Saúde da Mulher

Sistema de detecção de instrumentos cirúrgicos ginecológicos em vídeos, com geração de relatórios especializados de anomalias. Desenvolvido com YOLOv8 customizado para o contexto de cirurgias ginecológicas.

## Visão Geral

Este módulo implementa o requisito de **Análise de Vídeo Especializada para Saúde da Mulher** do Tech Challenge Fase 4 (POSTECH IADT). O sistema:

- Detecta instrumentos cirúrgicos ginecológicos frame a frame usando YOLOv8
- Identifica anomalias durante procedimentos (ausências prolongadas, excesso de instrumentos, variações bruscas)
- Gera relatórios automáticos em TXT, HTML e JSON com classificação de risco clínico

## Classes de Instrumentos Detectadas

| ID | Classe | Contexto Clínico |
|----|--------|-----------------|
| 0  | Scalpel (Bisturi) | Principal instrumento de incisão |
| 1  | Straight Dissection Clamp (Pinça reta) | Dissecção e hemostasia |
| 2  | Straight Mayo Scissor (Tesoura Mayo reta) | Corte de tecidos |
| 3  | Curved Mayo Scissor (Tesoura Mayo curva) | Corte em áreas de difícil acesso |

**Dataset:** [dilavado/labeled-surgical-tools](https://www.kaggle.com/datasets/dilavado/labeled-surgical-tools) — 3.009 imagens rotuladas

## Tipos de Anomalias Detectadas

| Tipo | Severidade | Trigger | Significado Clínico |
|------|-----------|---------|---------------------|
| AUSÊNCIA | ALTO | 10+ frames sem instrumentos | Possível troca não registrada ou queda de instrumento |
| AUSÊNCIA | CRÍTICO | 30+ frames sem instrumentos | Falha de controle cirúrgico — intervenção necessária |
| EXCESSO | MÉDIO | >5 instrumentos simultâneos | Falta de controle do campo operatório |
| VARIAÇÃO | MÉDIO | Delta > 3 da média recente | Possível manobra não planejada |

## Estrutura do Projeto

```
Tech Challenge Fase 4/
├── app.py                    # Aplicação principal (CLI)
├── dataset.yaml              # Configuração do dataset YOLO
├── requirements.txt          # Dependências
├── README.md
├── dataset/
│   ├── train/
│   │   ├── images/           # 2.170 imagens de treino
│   │   └── labels/           # Labels YOLO correspondentes
│   └── val/
│       ├── images/           # 851 imagens de validação
│       └── labels/
├── scripts/
│   └── download_dataset.py   # Download automático do Kaggle
├── src/
│   ├── utils.py              # Extração de frames
│   └── report.py             # Geração de relatórios (TXT/HTML/JSON)
├── instrument_detector/      # Criado após treino
│   └── weights/
│       └── best.pt           # Melhor modelo treinado
└── yolov8s.pt                # Modelo base pré-treinado
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

### 1. Baixar e Organizar Dataset

Requer credenciais Kaggle configuradas (`~/.kaggle/kaggle.json`):

```bash
python app.py download
```

### 2. Treinar o Modelo

```bash
python app.py train
```

Configurações padrão:
- Modelo base: YOLOv8 Small (`yolov8s.pt`)
- Épocas: 50 (com early stopping patience=20)
- Tamanho de imagem: 640×640
- Batch size: 8
- Saída: `instrument_detector/weights/best.pt`

### 3. Analisar Vídeo

```bash
python app.py detect --video path/to/video.mp4
```

**Com modelo customizado:**
```bash
python app.py detect --video path/to/video.mp4 --model instrument_detector/weights/best.pt
```

**Sem janela de visualização (servidor/CI):**
```bash
python app.py detect --video path/to/video.mp4 --headless
```

### 4. Extrair Frames de Vídeo

```bash
python app.py extract --video path/to/video.mp4 --output output_frames/
```

## Saídas da Análise

Após `python app.py detect`, são gerados na raiz do projeto:

| Arquivo | Formato | Conteúdo |
|---------|---------|---------|
| `output_detected.mp4` | Vídeo | Vídeo anotado com bounding boxes e alertas |
| `report.txt` | Texto | Relatório simplificado com lista de anomalias |
| `report.html` | HTML | Relatório visual com tabela de anomalias e avaliação de risco |
| `report.json` | JSON | Dados estruturados para integração com outros sistemas |

### Exemplo de Relatório JSON

```json
{
  "metadata": {
    "video_file": "cirurgia.mp4",
    "analysis_date": "2026-05-07T14:30:00",
    "fps": 25.0,
    "system": "YOLOv8 - Ginecological Surgical Instrument Detector"
  },
  "summary": {
    "total_frames": 1500,
    "total_detections": 3200,
    "avg_detections_per_frame": 2.13,
    "anomaly_count": 12,
    "anomaly_rate_pct": 0.8,
    "risk_level": "BAIXO",
    "by_type": {
      "AUSÊNCIA": 3,
      "EXCESSO": 2,
      "VARIAÇÃO": 7
    }
  },
  "anomalies": [
    {
      "frame": 145,
      "timestamp": "00:05",
      "severity": "ALTO",
      "type": "AUSÊNCIA",
      "description": "Ausência prolongada de instrumentos (10 frames consecutivos)"
    }
  ]
}
```

## Requisitos do Sistema

- Python 3.8+
- PyTorch 2.x com CUDA (recomendado para treinamento)
- OpenCV
- Ultralytics YOLOv8

## Relação com o Tech Challenge

Este módulo atende os requisitos de:

**Análise de Vídeo Especializada:**
- ✅ Cirurgias: detecção de instrumentos e anomalias cirúrgicas
- ✅ YOLOv8 customizado para instrumentos cirúrgicos ginecológicos

**Relatórios automáticos especializados:**
- ✅ Desvios em procedimentos cirúrgicos (ausências e variações)
- ✅ Sinais de complicações em cirurgias ginecológicas (excesso de instrumentos)
- ✅ Classificação de risco clínico (BAIXO / MÉDIO / ALTO / CRÍTICO)
- ✅ Exportação JSON para integração com sistemas hospitalares

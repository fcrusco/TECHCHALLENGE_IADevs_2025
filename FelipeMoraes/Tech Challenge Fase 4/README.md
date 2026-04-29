# Surgical Instrument Detection App

Aplicação para detecção de instrumentos cirúrgicos em vídeos usando YOLOv8.

## Estrutura do Projeto

```
Videos/
├── app.py                 # Aplicação principal (CLI)
├── requirements.txt       # Dependências do projeto
├── README.md              # Este arquivo
├── dataset/              # Dataset (imagens e rótulos)
│   ├── dataset.yaml      # Configuração do dataset
│   ├── train/            # Dados de treino
│   ├── val/              # Dados de validação
│   └── raw/              # Dados brutos (KIT dataset)
├── dist/                 # Executável compilado
│   └── app.exe          # Executable standalone
├── scripts/             # Scripts auxiliares
│   └── download_dataset.py  # Download e organização do dataset
├── src/                 # Código-fonte reutilizável
│   └── utils.py         # Funções utilitárias
└── runs/               # Resultados de treinamento (criado automaticamente)
    └── detect/instrument_detector/
        └── weights/
            └── best.pt  # Melhor modelo treinado
```

## Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Baixar e Organizar Dataset

```bash
python app.py download
```

## Uso

### Treinar o Modelo

```bash
python app.py train
```

**Parâmetros configuráveis em `app.py`:**
- `epochs`: Número de épocas (padrão: 50)
- `imgsz`: Tamanho da imagem (padrão: 640)
- `batch`: Tamanho do batch (padrão: 8)

### Detectar Instrumentos em Vídeo

```bash
python app.py detect --video path/to/video.mp4
```

**Opções:**
- `--video`: Caminho para o vídeo (obrigatório)
- `--model`: Caminho para o modelo treinado (padrão: `runs/detect/instrument_detector/weights/best.pt`)

### Extrair Frames de Vídeo

```bash
python app.py extract --video path/to/video.mp4 --output output_folder/
```

**Opções:**
- `--video`: Caminho para o vídeo (obrigatório)
- `--output`: Pasta de saída (obrigatório)

## Usando o Executável

O arquivo `dist/app.exe` é uma versão compilada standalone:

```bash
dist\app.exe download
dist\app.exe train
dist\app.exe detect --video path/to/video.mp4
dist\app.exe extract --video path/to/video.mp4 --output output_folder/
```

## Classes de Instrumentos

- `grasper` - Pinça
- `scissors` - Tesoura
- `forceps` - Fórceps
- `needle_holder` - Porta-agulha

## Requisitos do Sistema

- Python 3.8+
- CUDA (opcional, para GPU)
- OpenCV
- PyTorch
- Ultralytics YOLOv8

## Estrutura de Arquivos Removidos

Os seguintes arquivos foram consolidados no `app.py`:
- ❌ `detect_video.py` → Integrado em `app.py`
- ❌ `train.py` → Integrado em `app.py`
- ❌ `main.py` → Arquivo vazio, removido
- ❌ `download_kaggle.py` → Integrado em `download_dataset.py`
- ❌ `download_yolo_dataset.py` → Integrado em `download_dataset.py`
- ❌ `setup-dataset.py` → Integrado em `download_dataset.py`
- ❌ `prepare_dataset.py` → Integrado em `download_dataset.py`
- ❌ `convert_to_yolo.py` → Funcionalidade deprecada
- ❌ `process.py` → Arquivo de teste, removido

## Próximas Melhorias

- [ ] Adicionar interface gráfica (GUI)
- [ ] Suporte para múltiplos formatos de vídeo
- [ ] Dashboard de métricas de treinamento
- [ ] Exportar detecções para JSON/CSV


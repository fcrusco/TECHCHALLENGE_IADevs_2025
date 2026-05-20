# Tech Challenge Fase 4 — Análise de Áudio e Vídeo para a Saúde da Mulher

Implementação de modelos de detecção em vídeo e áudio voltados para consultas, cirurgias e temas relacionados à saúde da mulher, conforme solicitado pelo trabalho da Fase 4 (POSTECH IADT).

---

## Datasets utilizados

| Dataset | Uso | Tamanho | Fonte |
|---|---|---|---|
| GynSurge — Instrument Segmentation | Modelo `instrumentos` | ~2,5 GB | [ITEC / Univ. Klagenfurt](https://ftp.itec.aau.at/datasets/GynSurge/) |
| GynSurge — Anatomy Segmentation | Modelo `areas-criticas` | ~350 MB | [ITEC / Univ. Klagenfurt](https://ftp.itec.aau.at/datasets/GynSurge/) |
| WCEBleedGen | Modelo `sangramento` | ~1 GB | [Kaggle](https://www.kaggle.com/datasets/darksoul007fedsdfds/wcebleedgen) |
| Áudios sintéticos (OpenAI TTS) | Pipeline de áudio | ~10 MB | Gerado via `python app.py download --mode audio` |

---

## Vídeos de teste

Os vídeos de cirurgia laparoscópica usados nos testes estão disponíveis publicamente em:
**https://www.laparoscopyhospital.com/Free_laparoscopic_gynecological_videos.htm**

Execute `python download_videos_teste.py` para baixá-los automaticamente na pasta `videos/`.

| Arquivo | Descrição |
|---|---|
| `video_01.mp4` | Salpingectomia bilateral laparoscópica |
| `video_02.mp4` | Cisto ovariano — laparoscopia |
| `video_03.mp4` | Cistectomia de cisto dermoide |
| `video_04.mp4` | Histerectomia laparoscópica total (TLH) com Enseal |
| `video_05.mp4` | Procedimento laparoscópico ginecológico |
| `video_06.wmv` | Procedimento laparoscópico ginecológico |
| `video_07.wmv` | Cistectomia ovariana laparoscópica |

---

## Modelos implementados

### Vídeo — YOLOv8 (3 modelos)

| Modelo | O que detecta |
|---|---|
| `instrumentos` | Pinça Grasper, Tesoura, Pinça Bipolar, Gancho |
| `areas-criticas` | Útero, Tuba Uterina, Ovário |
| `sangramento` | Regiões de sangramento ativo |

### Áudio

Pipeline de análise clínica para consultas médicas em saúde da mulher:
extração de features acústicas (`librosa`) → transcrição (`OpenAI Whisper`) → classificação de risco e recomendações (`GPT-4o`).

---

## Antes de começar

### 1. Instalar o FFmpeg

O FFmpeg é obrigatório para a extração de áudio dos vídeos cirúrgicos (usado em `app.py` e `video_analisador/start_video.py`). Sem ele, a análise de áudio é ignorada silenciosamente.

**Windows — via winget (recomendado):**
```bash
winget install --id Gyan.FFmpeg --source winget --accept-source-agreements --accept-package-agreements
```
> Após a instalação, **reinicie o terminal** para que o `ffmpeg` seja reconhecido no PATH.

---

### 2. Instalar dependências Python

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

### 3. Configurar `.env`

Crie ou edite o arquivo `.env` na raiz do projeto (veja a seção [Parâmetros `.env`](#parâmetros-env) abaixo).
O campo obrigatório para áudio e parecer médico é:

```env
OPENAI_API_KEY=sk-...
```

### 4. Gerar dataset de áudio (sintético via OpenAI TTS)

```bash
python app.py download --mode audio
```

Gera 12 áudios MP3 em `dataset/dataset_audio/` simulando consultas médicas com diferentes perfis de risco.

### 5. Baixar vídeos de exemplo

```bash
python download_videos_teste.py
```

Baixa vídeos cirúrgicos de domínio público e salva em `videos/` como `video_01.mp4` … `video_07.mp4` (+ `video_06.wmv`, `video_07.wmv`).

---

## Demonstração completa — Notebook

A implementação completa está demonstrada no notebook **`analise_cirurgica.ipynb`**.

Ele executa os 3 modelos de vídeo, a análise clínica de áudio e gera o relatório consolidado em um único fluxo interativo.

**Configuração na célula inicial do notebook:**

```python
VIDEO_LOCAL   = "videos/video_01.mp4"   # caminho para o vídeo
TIPO_CONSULTA = "ginecologica"           # ginecologica | pre_natal | pos_parto | violencia
```

Execute **Run All** e todos os resultados serão gerados automaticamente na pasta `saida/`.

---

## Interfaces Gradio (frontends)

```bash
# Análise de áudio — http://localhost:7860
python app.py audio --frontend

# Análise de vídeo — http://localhost:7861
python app.py video
```

Ambas as interfaces permitem enviar o arquivo, escolher o modelo/tipo de consulta e baixar os relatórios gerados ao final. O **parecer médico via GPT-4o** é exibido diretamente na tela após a análise.

---

## CLI — Download de datasets

> Os modelos já foram treinados em máquina local. Os comandos abaixo são para reprodução completa do pipeline.

```bash
python app.py download --mode instrumentos     # GynSurge Instrument Segmentation (~2.5 GB)
python app.py download --mode areas-criticas   # GynSurge Anatomy Segmentation (~350 MB)
python app.py download --mode sangramento      # Kaggle WCEBleedGen (requer kaggle.json)
python app.py download --mode audio            # OpenAI TTS — 12 áudios sintéticos
```

Para `sangramento`, configure `~/.kaggle/kaggle.json` com suas credenciais Kaggle.

---

## CLI — Treinamento dos modelos

```bash
python app.py train --mode instrumentos
python app.py train --mode areas-criticas
python app.py train --mode sangramento
```

Os pesos treinados são salvos em `model/{modelo}/weights/best.pt`.

---

## CLI — Detecção em vídeo

```bash
# Modelo individual
python app.py detect --mode instrumentos   --video videos/video_01.mp4
python app.py detect --mode areas-criticas --video videos/video_01.mp4
python app.py detect --mode sangramento    --video videos/video_01.mp4

# Todos os modelos em sequência + relatório consolidado
python app.py detect --mode todos --video videos/video_01.mp4
```

---

## Parâmetros `.env`

```env
# ── API ────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...          # Whisper + GPT-4o + TTS (dataset de áudio)

# ── Treinamento — parâmetros globais ──────────────────────────────────────────
TRAIN_EPOCHS=150
TRAIN_IMGSZ=640
TRAIN_BATCH=8
TRAIN_PATIENCE=20
TRAIN_DEVICE=0                 # 0 = GPU | cpu = CPU
TRAIN_BASE_MODEL=yolov8m.pt
TRAIN_WORKERS=0                # 0 obrigatório no Windows (evita WinError 1455)

# ── Treinamento — por modelo ──────────────────────────────────────────────────
INST_TRAIN_EPOCHS=150          INST_TRAIN_IMGSZ=800    INST_TRAIN_BASE_MODEL=yolov8s.pt
AREAS_TRAIN_EPOCHS=150         AREAS_TRAIN_IMGSZ=640   AREAS_TRAIN_BASE_MODEL=yolov8s.pt
BLEED_TRAIN_EPOCHS=100         BLEED_TRAIN_IMGSZ=640   BLEED_TRAIN_BASE_MODEL=yolov8s.pt

# ── Detecção ──────────────────────────────────────────────────────────────────
DETECT_CONFIDENCE=0.55
DETECT_IOU=0.45

# Confiança por modelo
INST_CONFIDENCE=0.55
AREAS_CONFIDENCE=0.50
BLEED_CONFIDENCE=0.45

# ── Filtros geométricos (pós-processamento de bounding boxes) ─────────────────
FILTER_MIN_BOX_AREA=0.002      # descarta boxes < 0.2% do frame
FILTER_MAX_BOX_AREA=0.50       # descarta boxes > 50% do frame
FILTER_EDGE_MARGIN=0.008       # margem de borda (remove watermarks de extremidade)
FILTER_OVERLAY_TOP=0.22        # remove HUD/legenda superior
FILTER_OVERLAY_BOTTOM=0.80     # remove HUD/legenda inferior

# ── Limiares de anomalia ──────────────────────────────────────────────────────
ANOMALY_ABSENCE_WARN=10        # frames sem estrutura → severidade ALTO
ANOMALY_ABSENCE_CRITICAL=30    # frames sem estrutura → severidade CRÍTICO
BLEED_WARN_FRAMES=5            # frames consecutivos com sangramento → ALTO
BLEED_CRITICAL_FRAMES=15       # frames consecutivos com sangramento → CRÍTICO
```

---

## Relatórios e saídas geradas

Todos os arquivos são gerados na pasta `saida/`:

```
saida/
├── instrumentos/
│   ├── relatorio.txt          # Relatório completo em texto
│   ├── relatorio.html         # Relatório visual com tabelas e nível de risco
│   ├── resultado.mp4          # Vídeo anotado com bounding boxes (H.264)
│   └── parecer_medico.txt     # Parecer médico gerado por GPT-4o
├── areas_criticas/            # Mesma estrutura acima
├── sangramento/               # Mesma estrutura acima
├── audio/
│   └── relatorio_audio.txt    # Transcrição, nível de risco, sinais, recomendações
├── relatorio_geral.txt        # Relatório consolidado (todos os modelos)
└── relatorio_geral.html       # Versão visual do relatório consolidado
```

---

## Parecer médico via IA (GPT-4o)

Ao final de cada análise (frontend ou notebook), o sistema envia automaticamente os resultados de detecção para o GPT-4o e gera um **parecer médico estruturado** em português.

**O que é enviado para a IA:**

- Duração do vídeo, total de frames e FPS
- Por modelo: total de detecções, classes identificadas com frequência e janela temporal
- Linha do tempo de anomalias (até 25 eventos) com severidade e descrição
- Para instrumentos: timeline de uso de cada instrumento (primeiro uso, último uso, segmentos)

**Estrutura do parecer gerado:**

1. Resumo Executivo
2. Análise dos Achados por Modelo de Detecção
3. Avaliação de Risco Clínico
4. Eventos e Anomalias Relevantes
5. Recomendações
6. Considerações Finais

O parecer é salvo em `saida/{modelo}/parecer_medico.txt` e exibido na interface e no notebook.

> O parecer é gerado por sistema de apoio à decisão baseado em IA. A validação clínica é de responsabilidade exclusiva do médico responsável pelo caso.

import os
import json
import numpy as np
import librosa
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# SYSTEM PROMPTS — features acústicas + transcrição

SYSTEM_PROMPTS = {
    "ginecologica": """Você é um assistente clínico especializado em saúde ginecológica feminina.
Você receberá DOIS inputs combinados:
1. A transcrição da fala da paciente
2. Features acústicas extraídas do áudio (tom, energia, pausas, velocidade)

Use AMBOS para identificar:
- Tom emocional pela voz: pitch elevado/instável indica ansiedade; voz baixa e monótona indica tristeza ou dissociação
- Hesitação real: pausas longas (>1s) frequentes, velocidade de fala reduzida ao abordar certos temas
- Energia vocal reduzida pode indicar exaustão emocional ou depressão
- Alto jitter/shimmer (irregularidade vocal) é marcador fisiológico de estresse agudo
- Conteúdo do texto combinado com padrão acústico inconsistente ("estou bem" dito com voz trêmula = sinal de alerta)
- Possíveis indicadores de violência doméstica ou sexual velados na combinação fala+voz

Retorne EXATAMENTE neste formato JSON, sem markdown, sem explicações adicionais:
{
  "nivel_risco": "ALTO" | "MÉDIO" | "BAIXO",
  "sinais_detectados": "Lista detalhada dos sinais identificados, citando tanto o conteúdo verbal quanto os padrões acústicos relevantes",
  "recomendacoes": "Recomendações clínicas para o profissional de saúde"
}""",

    "pre_natal": """Você é um assistente clínico especializado em acompanhamento pré-natal.
Você receberá DOIS inputs combinados:
1. A transcrição da fala da gestante
2. Features acústicas extraídas do áudio (tom, energia, pausas, velocidade)

Use AMBOS para identificar:
- Ansiedade gestacional: pitch elevado, fala acelerada, muitas pausas de hesitação
- Depressão gestacional: voz monótona (baixa variação de pitch), energia vocal baixa, fala lenta
- Isolamento social/falta de suporte: conteúdo verbal combinado com tom de voz resignado
- Violência doméstica: voz trêmula ou baixa ao mencionar parceiro, pausas ao falar sobre relacionamento
- Estresse financeiro: mudança de padrão acústico ao abordar temas financeiros
- Sintomas físicos relatados (tontura, dores, sangramentos) com análise do tom ao relatar

Retorne EXATAMENTE neste formato JSON, sem markdown, sem explicações adicionais:
{
  "nivel_risco": "ALTO" | "MÉDIO" | "BAIXO",
  "sinais_detectados": "Lista detalhada dos sinais identificados, citando tanto o conteúdo verbal quanto os padrões acústicos relevantes",
  "recomendacoes": "Recomendações clínicas para o profissional de saúde"
}""",

    "pos_parto": """Você é um assistente clínico especializado em saúde materna pós-parto.
Você receberá DOIS inputs combinados:
1. A transcrição da fala da paciente
2. Features acústicas extraídas do áudio (tom, energia, pausas, velocidade)

Use AMBOS para identificar:
- Depressão pós-parto: voz plana/monótona (baixíssima variação de pitch), energia vocal persistentemente baixa, fala lenta
- Psicose pós-parto: padrão de fala fragmentado, aceleração súbita, incoerência entre conteúdo e tom
- Ansiedade pós-parto severa: pitch elevado, fala rápida, pausas curtas e frequentes
- Baby blues (transitório) vs depressão (persistente): avaliar pelo padrão acústico geral
- Dificuldade de vínculo: tom apático ao falar sobre o bebê, ausência de variação emocional positiva
- Exaustão extrema: energia vocal muito baixa, fala arrastada

Retorne EXATAMENTE neste formato JSON, sem markdown, sem explicações adicionais:
{
  "nivel_risco": "ALTO" | "MÉDIO" | "BAIXO",
  "sinais_detectados": "Lista detalhada dos sinais identificados, citando tanto o conteúdo verbal quanto os padrões acústicos relevantes",
  "recomendacoes": "Recomendações clínicas para o profissional de saúde"
}""",

    "violencia": """Você é um assistente clínico especializado no atendimento a mulheres vítimas de violência.
Você receberá DOIS inputs combinados:
1. A transcrição da fala da paciente
2. Features acústicas extraídas do áudio (tom, energia, pausas, velocidade)

Use AMBOS com extrema sensibilidade para identificar:
- Padrões vocais de trauma: voz trêmula (alto jitter), pitch caindo ao relatar eventos específicos
- Minimização verbal COM voz tensa: "não foi tão grave" dito com frequência fundamental elevada = contradição sinal de alerta máximo
- Pausas longas ao mencionar agressor: indica medo ou controle do relato
- Velocidade de fala reduzida drasticamente em tópicos específicos: dissociação ou trauma
- Voz baixa/sussurrada: pode indicar medo de ser ouvida
- Mudanças abruptas de energia vocal: ativação do sistema nervoso ao abordar o abuso
- Nível de perigo imediato: avaliar urgência pela combinação conteúdo + estado emocional acústico

IMPORTANTE: Este é um contexto de alta sensibilidade. Qualquer contradição entre o que é dito e como é dito deve ser tratada como sinal de alerta.

Retorne EXATAMENTE neste formato JSON, sem markdown, sem explicações adicionais:
{
  "nivel_risco": "ALTO" | "MÉDIO" | "BAIXO",
  "sinais_detectados": "Lista detalhada dos sinais identificados, citando tanto o conteúdo verbal quanto os padrões acústicos relevantes",
  "recomendacoes": "Recomendações clínicas para o profissional de saúde"
}"""
}


# EXTRAÇÃO DE FEATURES ACÚSTICAS com librosa

def extract_acoustic_features(audio_path: str) -> dict:
    """
    Extrai features acústicas clínicas relevantes usando librosa.

    Features extraídas:
    - Pitch (F0): frequência fundamental média, variação e estabilidade
    - Energia (RMS): intensidade vocal média e variação
    - Pausas: contagem e duração estimada de segmentos de silêncio
    - Velocidade de fala: taxa de atividade vocal (Voice Activity Rate)
    - Jitter proxy: irregularidade do pitch (desvio padrão / média)
    - MFCCs: coeficientes cepstrais — timbre e qualidade vocal geral
    - Spectral Centroid: brilho vocal (correlaciona com tensão/relaxamento)
    """
    y, sr = librosa.load(audio_path, sr=16000, mono=True)

    features = {}

    # ── 1. PITCH (F0) ──────────────────────────────────────────────────────
    # Usando pyin para estimativa robusta de F0
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),   # ~65 Hz — limite inferior feminino
        fmax=librosa.note_to_hz('C7'),   # ~2093 Hz — limite superior
        sr=sr
    )

    f0_voiced = f0[voiced_flag]  # só frames com voz detectada

    if len(f0_voiced) > 0:
        features["pitch_medio_hz"] = round(float(np.mean(f0_voiced)), 2)
        features["pitch_desvio_padrao"] = round(float(np.std(f0_voiced)), 2)
        features["pitch_variacao_relativa"] = round(
            float(np.std(f0_voiced) / np.mean(f0_voiced)), 4
        )
        # Jitter proxy: irregularidade frame a frame do pitch
        diff_f0 = np.abs(np.diff(f0_voiced))
        features["jitter_proxy"] = round(float(np.mean(diff_f0) / np.mean(f0_voiced)), 4)
    else:
        features["pitch_medio_hz"] = None
        features["pitch_desvio_padrao"] = None
        features["pitch_variacao_relativa"] = None
        features["jitter_proxy"] = None

    #  2. ENERGIA (RMS)
    rms = librosa.feature.rms(y=y)[0]
    features["energia_media_rms"] = round(float(np.mean(rms)), 5)
    features["energia_desvio_padrao"] = round(float(np.std(rms)), 5)
    features["energia_variacao_relativa"] = round(
        float(np.std(rms) / (np.mean(rms) + 1e-8)), 4
    )

    # 3. PAUSAS E VOICE ACTIVITY 
    # Threshold: frames abaixo de 10% da energia máxima = silêncio
    silence_threshold = 0.1 * np.max(rms)
    silence_frames = np.sum(rms < silence_threshold)
    total_frames = len(rms)
    hop_length = 512
    frame_duration_s = hop_length / sr

    features["taxa_silencio"] = round(float(silence_frames / total_frames), 4)
    features["taxa_voz_ativa"] = round(float(1 - silence_frames / total_frames), 4)

    # Contagem de pausas contínuas > 0.5s
    is_silence = rms < silence_threshold
    pauses = []
    in_pause = False
    pause_start = 0
    for i, s in enumerate(is_silence):
        if s and not in_pause:
            in_pause = True
            pause_start = i
        elif not s and in_pause:
            duration = (i - pause_start) * frame_duration_s
            if duration > 0.5:
                pauses.append(round(duration, 2))
            in_pause = False

    features["numero_pausas_longas"] = len(pauses)
    features["duracao_media_pausa_s"] = round(float(np.mean(pauses)), 2) if pauses else 0.0
    features["duracao_maxima_pausa_s"] = round(float(np.max(pauses)), 2) if pauses else 0.0

    # 4. VELOCIDADE DE FALA
    # Zero-crossing rate correlaciona com fricativas/consoantes → proxy de articulação
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    features["taxa_zero_crossing_media"] = round(float(np.mean(zcr)), 5)

    # Duração total do áudio
    features["duracao_total_s"] = round(float(len(y) / sr), 2)

    # 5. SPECTRAL CENTROID 
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    features["centroide_espectral_medio"] = round(float(np.mean(spec_centroid)), 2)
    features["centroide_espectral_desvio"] = round(float(np.std(spec_centroid)), 2)

    # 6. MFCCs (primeiros 5 coeficientes) 
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=5)
    for i, coef in enumerate(mfccs):
        features[f"mfcc_{i+1}_media"] = round(float(np.mean(coef)), 3)

    return features


def format_acoustic_report(features: dict) -> str:
    """
    Converte o dict de features em texto interpretável para o LLM,
    com referências clínicas sobre o que cada valor indica.
    """
    lines = ["=== ANÁLISE ACÚSTICA DO ÁUDIO ===\n"]

    dur = features.get("duracao_total_s", 0)
    lines.append(f"Duração total: {dur}s")

    # Pitch
    p_med = features.get("pitch_medio_hz")
    p_std = features.get("pitch_desvio_padrao")
    p_var = features.get("pitch_variacao_relativa")
    jitter = features.get("jitter_proxy")

    if p_med:
        interpretacao_pitch = ""
        if p_med < 150:
            interpretacao_pitch = "(voz grave — pode indicar exaustão, depressão ou dissociação)"
        elif p_med > 250:
            interpretacao_pitch = "(voz aguda — pode indicar ansiedade ou medo)"
        else:
            interpretacao_pitch = "(pitch na faixa normal feminina)"

        lines.append(f"\nPITCH (Frequência Fundamental):")
        lines.append(f"  - Média: {p_med} Hz {interpretacao_pitch}")
        lines.append(f"  - Desvio padrão: {p_std} Hz")

        if p_var is not None:
            if p_var < 0.10:
                var_interp = "(voz muito monótona — marcador de depressão ou dissociação emocional)"
            elif p_var > 0.35:
                var_interp = "(pitch muito variável — pode indicar estado emocional instável ou ansiedade)"
            else:
                var_interp = "(variação de pitch normal)"
            lines.append(f"  - Variação relativa: {p_var} {var_interp}")

        if jitter is not None:
            if jitter > 0.05:
                jitter_interp = "(alta irregularidade vocal — marcador fisiológico de estresse agudo ou medo)"
            else:
                jitter_interp = "(irregularidade vocal dentro do normal)"
            lines.append(f"  - Jitter proxy: {jitter} {jitter_interp}")

    # Energia
    e_med = features.get("energia_media_rms")
    e_var = features.get("energia_variacao_relativa")

    if e_med is not None:
        lines.append(f"\nENERGIA VOCAL (RMS):")
        if e_med < 0.02:
            e_interp = "(energia muito baixa — voz fraca, pode indicar exaustão extrema ou depressão severa)"
        elif e_med > 0.1:
            e_interp = "(energia elevada — voz intensa, pode indicar agitação ou ansiedade)"
        else:
            e_interp = "(energia vocal normal)"
        lines.append(f"  - Média: {e_med} {e_interp}")

        if e_var is not None:
            if e_var > 1.0:
                ev_interp = "(alta variação — alternância entre fala intensa e quase inaudível, possível instabilidade emocional)"
            else:
                ev_interp = "(variação de energia normal)"
            lines.append(f"  - Variação relativa: {e_var} {ev_interp}")

    # Pausas
    n_pausas = features.get("numero_pausas_longas", 0)
    dur_med_pausa = features.get("duracao_media_pausa_s", 0)
    dur_max_pausa = features.get("duracao_maxima_pausa_s", 0)
    taxa_silencio = features.get("taxa_silencio", 0)
    taxa_voz = features.get("taxa_voz_ativa", 0)

    lines.append(f"\nPAUSAS E SILÊNCIOS:")
    lines.append(f"  - Taxa de atividade vocal: {round(taxa_voz*100,1)}% do áudio")
    lines.append(f"  - Taxa de silêncio: {round(taxa_silencio*100,1)}% do áudio")

    if n_pausas > 0:
        if n_pausas > 10:
            pausas_interp = "(muitas pausas — forte indicador de hesitação, medo ou dificuldade em relatar)"
        elif n_pausas > 5:
            pausas_interp = "(pausas moderadas — alguma hesitação presente)"
        else:
            pausas_interp = "(pausas em quantidade normal)"

        lines.append(f"  - Pausas longas (>0.5s): {n_pausas} ocorrências {pausas_interp}")
        lines.append(f"  - Duração média das pausas: {dur_med_pausa}s")
        lines.append(f"  - Pausa mais longa detectada: {dur_max_pausa}s")

        if dur_max_pausa > 3.0:
            lines.append(f"  ⚠ ALERTA: pausa de {dur_max_pausa}s — silêncio prolongado pode indicar bloqueio emocional ou dissociação")

    # Spectral Centroid
    sc_med = features.get("centroide_espectral_medio")
    if sc_med:
        lines.append(f"\nBRILHO VOCAL (Centroide Espectral):")
        if sc_med > 3000:
            sc_interp = "(voz tensa/aguda — indicador de ativação do sistema nervoso simpático)"
        elif sc_med < 1500:
            sc_interp = "(voz abafada/grave — pode indicar exaustão ou estados dissociativos)"
        else:
            sc_interp = "(timbre vocal normal)"
        lines.append(f"  - Média: {sc_med} Hz {sc_interp}")

    lines.append("\n=== FIM DA ANÁLISE ACÚSTICA ===")

    return "\n".join(lines)

# CLASSE PRINCIPAL

class AudioAnalyzer:

    def transcribe(self, audio_path: str) -> str:
        """Transcreve áudio usando Whisper via API da OpenAI."""
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt",
                response_format="text"
            )
        return transcription

    def analyze_text(self, transcription: str, acoustic_report: str, consultation_type: str) -> dict:
        """Analisa transcrição + features acústicas com GPT-4o usando prompt especializado."""
        system_prompt = SYSTEM_PROMPTS.get(consultation_type, SYSTEM_PROMPTS["ginecologica"])

        user_content = f"""Analise a seguinte consulta médica com base na transcrição E nos dados acústicos do áudio:

{acoustic_report}

=== TRANSCRIÇÃO DA FALA ===
{transcription}

Lembre-se: contradições entre o que é DITO e como é DITO (padrão acústico) são sinais clínicos importantes."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.2,
            max_tokens=800
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(raw)
        return parsed

    def analyze(self, audio_path: str, consultation_type: str) -> dict:
        """Pipeline completo: extração acústica + transcrição + análise clínica integrada."""

        # 1. Extração de features acústicas (local, sem API)
        try:
            features = extract_acoustic_features(audio_path)
            acoustic_report = format_acoustic_report(features)
        except Exception as e:
            acoustic_report = f"Análise acústica não disponível: {str(e)}"
            features = {}

        # 2. Transcrição via Whisper
        transcricao = self.transcribe(audio_path)

        if not transcricao or len(transcricao.strip()) < 10:
            return {
                "transcricao": "Não foi possível transcrever o áudio. Verifique a qualidade da gravação.",
                "nivel_risco": "—",
                "sinais_detectados": "—",
                "recomendacoes": "—"
            }

        # 3. Análise clínica integrada (texto + acústica)
        analise = self.analyze_text(transcricao, acoustic_report, consultation_type)

        return {
            "transcricao": transcricao,
            "nivel_risco": analise.get("nivel_risco", "—"),
            "sinais_detectados": analise.get("sinais_detectados", "—"),
            "recomendacoes": analise.get("recomendacoes", "—")
        }
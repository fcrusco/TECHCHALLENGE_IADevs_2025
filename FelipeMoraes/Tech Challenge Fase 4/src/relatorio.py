import json
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# Critérios especializados — mapeamento modelo → critério clínico
# ---------------------------------------------------------------------------

_SPECIALTY_CRITERIA = [
    {
        "title": "Riscos em Saúde Materna e Ginecológica",
        "objective": "Detectar precocemente riscos em saúde materna e ginecológica",
        "description": "Monitoramento de estruturas ginecológicas (útero, tuba uterina, ovário) e sangramento anômalo durante procedimentos obstétricos e cirúrgicos.",
        "recommendation": "Acionar equipe obstétrica e ginecológica para avaliação imediata das anomalias detectadas.",
        "detectors": {"areas_criticas", "sangramento"},
    },
    {
        "title": "Bem-Estar Psicológico Feminino",
        "objective": "Monitorar bem-estar psicológico feminino",
        "description": "Monitoramento de eventos hemorrágicos e complicações cirúrgicas que podem impactar negativamente o bem-estar e a recuperação psicológica pós-operatória da paciente.",
        "recommendation": "Acionar equipe de suporte psicológico e protocolo de acompanhamento pós-operatório especializado.",
        "detectors": {"sangramento"},
        "anomaly_types": {"SANGRAMENTO"},
    },
    {
        "title": "Detecção de Anomalias em Tempo Real",
        "objective": "Aplicar técnicas de detecção de anomalias em tempo real para monitoramento preventivo específico",
        "description": "Monitoramento contínuo frame a frame com classificação automática de severidade (MÉDIO / ALTO / CRÍTICO): ausências de estruturas anatômicas, sangramentos persistentes e variações bruscas de campo cirúrgico.",
        "recommendation": "Revisar os segmentos sinalizados e acionar protocolo de monitoramento preventivo.",
        "detectors": {"areas_criticas", "sangramento"},
    },
]


def _evaluate_criteria(model_results):
    """Retorna lista de (criterio, triggered, findings) para cada critério especializado."""
    results_by_folder = {r["model_folder"]: r for r in model_results}
    evaluated = []

    for criterion in _SPECIALTY_CRITERIA:
        findings = []
        filter_types = criterion.get("anomaly_types")

        for folder in criterion["detectors"]:
            r = results_by_folder.get(folder)
            if not r:
                continue
            anomalies = r["anomalies"]
            if filter_types:
                anomalies = [a for a in anomalies if isinstance(a, dict) and a.get("type") in filter_types]
            if anomalies:
                critico = _count_by_severity(anomalies, "CRÍTICO")
                alto    = _count_by_severity(anomalies, "ALTO")
                medio   = _count_by_severity(anomalies, "MÉDIO")
                findings.append({
                    "folder": folder,
                    "count": len(anomalies),
                    "critico": critico,
                    "alto": alto,
                    "medio": medio,
                })

        evaluated.append({
            "criterion": criterion,
            "triggered": len(findings) > 0,
            "findings": findings,
        })

    return evaluated


def generate_report(output_path, total_frames, total_detections, anomalies,
                    fps=20, video_path=None, class_summary=None):
    avg = total_detections / total_frames if total_frames > 0 else 0
    anomaly_rate = (len(anomalies) / total_frames) * 100 if total_frames > 0 else 0
    duration = _frame_to_time(total_frames, fps)

    _generate_text_report(output_path, total_frames, total_detections, anomalies,
                          fps, video_path, avg, anomaly_rate, duration, class_summary)
    print(f"Relatório TXT salvo em: {output_path}")

    html_path = output_path.replace(".txt", ".html")
    _generate_html_report(html_path, total_frames, total_detections, anomalies,
                          fps, video_path, avg, anomaly_rate, duration, class_summary)
    print(f"Relatório HTML salvo em: {html_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_risk_level(anomaly_rate):
    if anomaly_rate > 20:
        return "CRÍTICO", "#dc3545"
    elif anomaly_rate > 10:
        return "ALTO", "#fd7e14"
    elif anomaly_rate > 5:
        return "MÉDIO", "#ffc107"
    return "BAIXO", "#28a745"


def _frame_to_time(frame, fps):
    if not frame or fps <= 0:
        return "00:00"
    total_seconds = int(frame) // max(int(fps), 1)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def _count_by_type(anomalies, atype):
    return sum(1 for a in anomalies if isinstance(a, dict) and a.get("type") == atype)


def _count_by_severity(anomalies, severity):
    return sum(1 for a in anomalies if isinstance(a, dict) and a.get("severity") == severity)


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def _generate_text_report(output_path, total_frames, total_detections, anomalies,
                           fps, video_path, avg, anomaly_rate, duration, class_summary):
    risk_label, _ = _get_risk_level(anomaly_rate)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  RELATÓRIO DE ANÁLISE CIRÚRGICA ESPECIALIZADA\n")
        f.write("  Saúde da Mulher - Tech Challenge Fase 4\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Data/Hora:  {now}\n")
        if video_path:
            f.write(f"Vídeo:      {os.path.basename(video_path)}\n")
        f.write(f"Duração:    {duration}\n")
        f.write(f"FPS:        {fps:.1f}\n\n")

        f.write("--- RESUMO ESTATÍSTICO ---\n")
        f.write(f"Frames analisados:    {total_frames}\n")
        f.write(f"Detecções totais:     {total_detections}\n")
        f.write(f"Média por frame:      {avg:.2f}\n")
        f.write(f"Anomalias detectadas: {len(anomalies)}\n")
        f.write(f"Taxa de anomalia:     {anomaly_rate:.2f}%\n")
        f.write(f"Nível de risco:       {risk_label}\n\n")

        if anomalies:
            critico = _count_by_severity(anomalies, "CRÍTICO")
            alto    = _count_by_severity(anomalies, "ALTO")
            medio   = _count_by_severity(anomalies, "MÉDIO")
            f.write("--- DISTRIBUIÇÃO POR SEVERIDADE ---\n")
            f.write(f"  CRÍTICO: {critico}\n")
            f.write(f"  ALTO:    {alto}\n")
            f.write(f"  MÉDIO:   {medio}\n\n")

        if class_summary:
            f.write("--- OBJETOS/CLASSES DETECTADOS ---\n")
            for name, info in sorted(class_summary.items(), key=lambda x: -x[1]["count"]):
                first_ts = _frame_to_time(info["first_frame"], fps)
                last_ts  = _frame_to_time(info["last_frame"], fps)
                f.write(
                    f"  {name:<25} {info['count']:>5}x"
                    f" | {first_ts} → {last_ts}"
                    f" | {info['frames_pct']:.1f}% dos frames\n"
                )
            f.write("\n")

        f.write("--- LINHA DO TEMPO DE ANOMALIAS ---\n")
        if not anomalies:
            f.write("  Nenhuma anomalia detectada.\n")
        else:
            for a in anomalies:
                if isinstance(a, dict):
                    frame    = a.get("frame", 0)
                    ts       = _frame_to_time(frame, fps)
                    severity = a.get("severity", "-")
                    atype    = a.get("type", "-")
                    desc     = a.get("description", "")
                    f.write(f"  {ts} | Frame {frame:>5} | [{severity:<8}] | {atype:<12} | {desc}\n")
                else:
                    f.write(f"  {str(a)}\n")

        absences   = _count_by_type(anomalies, "AUSÊNCIA")
        excesses   = _count_by_type(anomalies, "EXCESSO")
        variations = _count_by_type(anomalies, "VARIAÇÃO")

        f.write("\n--- AVALIAÇÃO CLÍNICA ---\n")
        f.write(f"Ausências prolongadas:    {absences}\n")
        f.write(f"Excessos detectados:      {excesses}\n")
        f.write(f"Variações bruscas:        {variations}\n\n")

        f.write("--- RECOMENDAÇÕES ---\n")
        if anomaly_rate > 20:
            f.write("ATENÇÃO CRÍTICA: Alta taxa de anomalias. Revisão imediata necessária.\n")
        elif anomaly_rate > 10:
            f.write("ATENÇÃO: Taxa elevada. Revisão por especialista recomendada.\n")
        elif anomaly_rate > 5:
            f.write("OBSERVAÇÃO: Anomalias dentro de limite aceitável, mas merecem atenção.\n")
        else:
            f.write("Procedimento dentro dos parâmetros normais.\n")

        if absences > 0:
            f.write(f"- Revisar {absences} segmentos com ausência prolongada.\n")
        if excesses > 0:
            f.write(f"- Verificar {excesses} frames com excesso detectado.\n")
        if variations > 0:
            f.write(f"- Investigar {variations} variações bruscas.\n")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_SEV_COLORS = {"CRÍTICO": "#dc3545", "ALTO": "#fd7e14", "MÉDIO": "#ffc107", "BAIXO": "#28a745"}

_BASE_CSS = """
  html, body { color-scheme: light !important; }
  body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5 !important; color: #1e1a1d !important; }
  .container { max-width: 1000px; margin: auto; background: #ffffff !important; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); color: #1e1a1d !important; }
  h1 { color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 10px; margin-top: 0; }
  h2 { color: #1a3a5c; margin-top: 30px; border-left: 4px solid #1a3a5c; padding-left: 10px; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 25px; background: #f8f9fa; padding: 10px 15px; border-radius: 4px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
  .stat-card { background: #f8f9fa; border-left: 4px solid #1a3a5c; padding: 15px; border-radius: 4px; }
  .stat-card .value { font-size: 1.8em; font-weight: bold; color: #1a3a5c; }
  .stat-card .label { font-size: 0.82em; color: #666; margin-top: 4px; }
  .risk-badge { display: inline-block; color: white; padding: 6px 16px; border-radius: 20px; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9em; }
  th { background: #1a3a5c; color: white; padding: 10px 12px; text-align: left; }
  td { padding: 8px 12px; border-bottom: 1px solid #eee; }
  tr:hover td { background: #f8f9fa; }
  .bar-wrap { display: flex; align-items: center; gap: 8px; }
  .bar { background: #1a3a5c; height: 10px; border-radius: 3px; }
  .recommendations { background: #e8f4fd; border-left: 4px solid #1a3a5c; padding: 15px 20px; border-radius: 4px; margin-top: 15px; }
  .no-data { color: #999; font-style: italic; }
  .footer { margin-top: 30px; text-align: center; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 15px; }
"""


def _generate_html_report(path, total_frames, total_detections, anomalies,
                           fps, video_path, avg, anomaly_rate, duration, class_summary):
    risk_label, risk_color = _get_risk_level(anomaly_rate)
    video_name = os.path.basename(video_path) if video_path else "N/A"
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    absences   = _count_by_type(anomalies, "AUSÊNCIA")
    excesses   = _count_by_type(anomalies, "EXCESSO")
    variations = _count_by_type(anomalies, "VARIAÇÃO")
    critico    = _count_by_severity(anomalies, "CRÍTICO")
    alto       = _count_by_severity(anomalies, "ALTO")
    medio      = _count_by_severity(anomalies, "MÉDIO")

    # Anomaly rows
    rows = ""
    for a in anomalies:
        if isinstance(a, dict):
            frame    = a.get("frame", "-")
            severity = a.get("severity", "-")
            atype    = a.get("type", "-")
            desc     = a.get("description", "")
            ts       = _frame_to_time(frame, fps)
            sc       = _SEV_COLORS.get(severity, "#6c757d")
            rows += (
                f"<tr>"
                f"<td><strong>{ts}</strong></td><td>{frame}</td>"
                f"<td><span style='color:{sc};font-weight:bold'>{severity}</span></td>"
                f"<td>{atype}</td><td>{desc}</td>"
                f"</tr>\n"
            )
        else:
            rows += f"<tr><td colspan='5'>{str(a)}</td></tr>\n"

    # Class detections rows
    cls_rows = ""
    if class_summary:
        for name, info in sorted(class_summary.items(), key=lambda x: -x[1]["count"]):
            first_ts = _frame_to_time(info["first_frame"], fps)
            last_ts  = _frame_to_time(info["last_frame"], fps)
            pct      = info["frames_pct"]
            bar_w    = min(int(pct) * 2, 200)
            cls_rows += (
                f"<tr>"
                f"<td><strong>{name}</strong></td>"
                f"<td>{info['count']}</td>"
                f"<td>{first_ts}</td>"
                f"<td>{last_ts}</td>"
                f"<td><div class='bar-wrap'>"
                f"<div class='bar' style='width:{bar_w}px'></div>"
                f"<span>{pct}%</span></div></td>"
                f"</tr>\n"
            )

    class_section = (
        "<p class='no-data'>Nenhum objeto identificado neste modelo.</p>"
        if not class_summary else
        f"""<table>
      <thead><tr><th>Classe</th><th>Ocorrências</th><th>Primeiro visto</th><th>Último visto</th><th>Frequência</th></tr></thead>
      <tbody>{cls_rows}</tbody>
    </table>"""
    )

    anomaly_section = (
        "<p class='no-data'>Nenhuma anomalia detectada durante o procedimento.</p>"
        if not anomalies else
        f"""<table>
      <thead><tr><th>Timestamp</th><th>Frame</th><th>Severidade</th><th>Tipo</th><th>Descrição</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""
    )

    recs = []
    if anomaly_rate > 20:
        recs.append("<p><strong style='color:#dc3545'>ATENÇÃO CRÍTICA:</strong> Alta taxa de anomalias. Revisão imediata necessária.</p>")
    elif anomaly_rate > 10:
        recs.append("<p><strong style='color:#fd7e14'>ATENÇÃO:</strong> Taxa elevada. Revisão por especialista recomendada.</p>")
    elif anomaly_rate > 5:
        recs.append("<p><strong style='color:#ffc107'>OBSERVAÇÃO:</strong> Anomalias dentro de limite aceitável.</p>")
    else:
        recs.append("<p style='color:#28a745'>Procedimento dentro dos parâmetros normais. Nenhuma ação recomendada.</p>")

    items = []
    if absences > 0:
        items.append(f"<li><strong>Ausências ({absences}):</strong> Revisar segmentos sem detecção.</li>")
    if excesses > 0:
        items.append(f"<li><strong>Excessos ({excesses}):</strong> Verificar frames com excesso detectado.</li>")
    if variations > 0:
        items.append(f"<li><strong>Variações ({variations}):</strong> Investigar transições abruptas.</li>")
    if items:
        recs.append("<ul>" + "".join(items) + "</ul>")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<title>Relatório de Análise Cirúrgica</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="container">
  <h1>Relatório de Análise Cirúrgica Especializada</h1>
  <p style="color:#555;margin-top:-10px">Saúde da Mulher — Tech Challenge Fase 4 (YOLOv8)</p>
  <div class="meta">
    <strong>Vídeo:</strong> {video_name} &nbsp;|&nbsp;
    <strong>Duração:</strong> {duration} &nbsp;|&nbsp;
    <strong>FPS:</strong> {fps:.1f} &nbsp;|&nbsp;
    <strong>Data/Hora:</strong> {now}
  </div>

  <h2>Resumo Estatístico</h2>
  <div class="grid-3">
    <div class="stat-card"><div class="value">{total_frames}</div><div class="label">Frames Analisados</div></div>
    <div class="stat-card"><div class="value">{total_detections}</div><div class="label">Detecções Totais</div></div>
    <div class="stat-card"><div class="value">{avg:.2f}</div><div class="label">Média por Frame</div></div>
    <div class="stat-card"><div class="value">{len(anomalies)}</div><div class="label">Anomalias Detectadas</div></div>
    <div class="stat-card"><div class="value">{anomaly_rate:.1f}%</div><div class="label">Taxa de Anomalia</div></div>
    <div class="stat-card"><div class="value"><span class="risk-badge" style="background:{risk_color}">{risk_label}</span></div><div class="label">Nível de Risco Clínico</div></div>
  </div>

  <h2>Distribuição por Severidade</h2>
  <div class="grid-3">
    <div class="stat-card"><div class="value" style="color:#dc3545">{critico}</div><div class="label">Crítico</div></div>
    <div class="stat-card"><div class="value" style="color:#fd7e14">{alto}</div><div class="label">Alto</div></div>
    <div class="stat-card"><div class="value" style="color:#ffc107">{medio}</div><div class="label">Médio</div></div>
  </div>

  <h2>Objetos Detectados</h2>
  {class_section}

  <h2>Linha do Tempo de Anomalias</h2>
  {anomaly_section}

  <h2>Distribuição de Tipos</h2>
  <div class="grid-3">
    <div class="stat-card"><div class="value" style="color:#dc3545">{absences}</div><div class="label">Ausências Prolongadas</div></div>
    <div class="stat-card"><div class="value" style="color:#fd7e14">{excesses}</div><div class="label">Excessos Detectados</div></div>
    <div class="stat-card"><div class="value" style="color:#ffc107">{variations}</div><div class="label">Variações Bruscas</div></div>
  </div>

  <h2>Avaliação de Risco Clínico</h2>
  <div class="recommendations">{"".join(recs)}</div>

  <div class="footer">Gerado automaticamente — Sistema de Análise Cirúrgica · Tech Challenge Fase 4 · POSTECH IADT</div>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def _generate_json_report(path, total_frames, total_detections, anomalies,
                           fps, video_path, avg, anomaly_rate, duration, class_summary):
    risk_label, _ = _get_risk_level(anomaly_rate)

    anomaly_list = []
    for a in anomalies:
        if isinstance(a, dict):
            frame = a.get("frame", 0)
            anomaly_list.append({
                "frame": frame,
                "timestamp": _frame_to_time(frame, fps),
                "severity": a.get("severity"),
                "type": a.get("type"),
                "description": a.get("description"),
            })
        else:
            anomaly_list.append({"description": str(a)})

    class_data = {}
    for name, info in (class_summary or {}).items():
        class_data[name] = {
            "count": info["count"],
            "first_seen": _frame_to_time(info["first_frame"], fps),
            "first_frame": info["first_frame"],
            "last_seen": _frame_to_time(info["last_frame"], fps),
            "last_frame": info["last_frame"],
            "frames_pct": info["frames_pct"],
        }

    report_data = {
        "metadata": {
            "video_file": os.path.basename(video_path) if video_path else None,
            "analysis_date": datetime.now().isoformat(),
            "duration": duration,
            "fps": fps,
            "system": "YOLOv8 - Sistema de Análise Cirúrgica — Tech Challenge Fase 4",
        },
        "summary": {
            "total_frames": total_frames,
            "total_detections": total_detections,
            "avg_detections_per_frame": round(avg, 2),
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": round(anomaly_rate, 2),
            "risk_level": risk_label,
            "by_severity": {
                "CRÍTICO": _count_by_severity(anomalies, "CRÍTICO"),
                "ALTO":    _count_by_severity(anomalies, "ALTO"),
                "MÉDIO":   _count_by_severity(anomalies, "MÉDIO"),
            },
            "by_type": {
                "AUSÊNCIA": _count_by_type(anomalies, "AUSÊNCIA"),
                "EXCESSO":  _count_by_type(anomalies, "EXCESSO"),
                "VARIAÇÃO": _count_by_type(anomalies, "VARIAÇÃO"),
            },
        },
        "class_detections": class_data,
        "anomalies": anomaly_list,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Relatório consolidado (todos os modelos)
# ---------------------------------------------------------------------------

def generate_combined_report(output_path, model_results, video_path=None):
    """Gera relatório consolidado com resultados de todos os modelos."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    video_name = os.path.basename(video_path) if video_path else "N/A"

    total_anomalies = sum(len(r["anomalies"]) for r in model_results)
    total_frames = model_results[0]["frame_count"] if model_results else 0
    fps = model_results[0]["fps"] if model_results else 20
    duration = _frame_to_time(total_frames, fps)

    _combined_text(output_path, model_results, video_name, now, total_frames, total_anomalies, fps, duration)
    print(f"Relatório consolidado TXT: {output_path}")

    html_path = output_path.replace(".txt", ".html")
    _combined_html(html_path, model_results, video_name, now, total_frames, total_anomalies, fps, duration)
    print(f"Relatório consolidado HTML: {html_path}")


def _combined_text(path, model_results, video_name, now, total_frames, total_anomalies, fps, duration):
    overall_rate = (total_anomalies / total_frames) * 100 if total_frames else 0
    risk_label, _ = _get_risk_level(overall_rate)

    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  RELATÓRIO CONSOLIDADO — TECH CHALLENGE FASE 4\n")
        f.write("  Análise de Vídeo Especializada para Saúde da Mulher\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Data/Hora:  {now}\n")
        f.write(f"Vídeo:      {video_name}\n")
        f.write(f"Duração:    {duration}\n")
        f.write(f"Frames:     {total_frames}\n")
        f.write(f"Modelos:    {len(model_results)}\n\n")

        f.write("--- AVALIAÇÃO GERAL ---\n")
        f.write(f"  Total de anomalias: {total_anomalies}\n")
        f.write(f"  Taxa geral:         {overall_rate:.2f}%\n")
        f.write(f"  Nível de risco:     {risk_label}\n\n")

        for r in model_results:
            if r["model_folder"] == "instrumentos" and r.get("instrument_timeline"):
                f.write("--- INSTRUMENTOS CIRÚRGICOS UTILIZADOS ---\n")
                for name, info in sorted(r["instrument_timeline"].items(), key=lambda x: -x[1]["count"]):
                    if info["count"] > 0:
                        segs     = len(info["segments"])
                        first_ts = _frame_to_time(info["first_frame"], fps)
                        last_ts  = _frame_to_time(info["last_frame"],  fps)
                        f.write(f"  {name:<25} {info['count']:>5}x | {info['frames_pct']:.1f}% | {segs} seg(s) | {first_ts} → {last_ts}\n")
                    else:
                        f.write(f"  {name:<25}  não detectado\n")
                f.write("\n")
                break

        f.write("--- OBJETIVOS DO TECH CHALLENGE ---\n")
        for i, ev in enumerate(_evaluate_criteria(model_results), 1):
            c = ev["criterion"]
            status = "ACIONADO" if ev["triggered"] else "SEM OCORRÊNCIAS"
            f.write(f"  [OBJ.{i}] [{status}] {c['title']}\n")
            f.write(f"  Objetivo: {c.get('objective', c['title'])}\n")
            if ev["triggered"]:
                for fd in ev["findings"]:
                    f.write(
                        f"    → {fd['folder']}: {fd['count']} ocorrência(s) "
                        f"[CRÍTICO:{fd['critico']} ALTO:{fd['alto']} MÉDIO:{fd['medio']}]\n"
                    )
                f.write(f"    Recomendação: {c['recommendation']}\n")
            f.write("\n")

        for r in model_results:
            anomaly_rate = (len(r["anomalies"]) / r["frame_count"]) * 100 if r["frame_count"] else 0
            mlabel, _ = _get_risk_level(anomaly_rate)
            f.write(f"--- {r['model_folder'].upper()} ---\n")
            f.write(f"  Detecções totais: {r['detections']}\n")
            if r["model_folder"] == "instrumentos":
                f.write("  Modo: rastreamento (sem detecção de anomalias)\n")
            else:
                f.write(f"  Anomalias:        {len(r['anomalies'])}\n")
                f.write(f"  Taxa de anomalia: {anomaly_rate:.2f}%\n")
                f.write(f"  Nível de risco:   {mlabel}\n")

            cs = r.get("class_summary", {})
            if cs:
                f.write("  Objetos detectados:\n")
                for name, info in sorted(cs.items(), key=lambda x: -x[1]["count"]):
                    first_ts = _frame_to_time(info["first_frame"], fps)
                    last_ts  = _frame_to_time(info["last_frame"],  fps)
                    f.write(
                        f"    {name:<25} {info['count']:>5}x"
                        f" | {first_ts} → {last_ts}"
                        f" | {info['frames_pct']:.1f}% dos frames\n"
                    )

            if r["anomalies"]:
                f.write("  Linha do tempo:\n")
                for a in r["anomalies"]:
                    if isinstance(a, dict):
                        frame    = a.get("frame", 0)
                        ts       = _frame_to_time(frame, fps)
                        severity = a.get("severity", "-")
                        atype    = a.get("type", "-")
                        desc     = a.get("description", "")
                        f.write(f"    {ts} | Frame {frame:>5} | [{severity:<8}] | {atype:<12} | {desc}\n")
            f.write("\n")


def _combined_html(path, model_results, video_name, now, total_frames, total_anomalies, fps, duration):
    overall_rate = (total_anomalies / total_frames) * 100 if total_frames else 0
    risk_label, risk_color = _get_risk_level(overall_rate)

    model_sections = ""
    all_rows = ""

    for r in model_results:
        anomaly_rate = (len(r["anomalies"]) / r["frame_count"]) * 100 if r["frame_count"] else 0
        mlabel, mcolor = _get_risk_level(anomaly_rate)
        avg = r["detections"] / r["frame_count"] if r["frame_count"] else 0
        cs  = r.get("class_summary", {})

        cls_rows = ""
        if cs:
            for name, info in sorted(cs.items(), key=lambda x: -x[1]["count"]):
                first_ts = _frame_to_time(info["first_frame"], fps)
                last_ts  = _frame_to_time(info["last_frame"],  fps)
                pct      = info["frames_pct"]
                bar_w    = min(int(pct) * 2, 200)
                cls_rows += (
                    f"<tr><td>{name}</td><td>{info['count']}</td>"
                    f"<td>{first_ts}</td><td>{last_ts}</td>"
                    f"<td><div class='bar-wrap'>"
                    f"<div class='bar' style='width:{bar_w}px'></div>"
                    f"<span>{pct}%</span></div></td></tr>\n"
                )

        cls_table = (
            "<p class='no-data' style='padding:10px 15px;margin:0'>Nenhum objeto identificado.</p>"
            if not cs else
            f"<table style='font-size:0.85em'><thead><tr>"
            f"<th>Classe</th><th>Ocorrências</th><th>Primeiro</th><th>Último</th><th>Frequência</th>"
            f"</tr></thead><tbody>{cls_rows}</tbody></table>"
        )

        for a in r["anomalies"]:
            if isinstance(a, dict):
                frame    = a.get("frame", "-")
                severity = a.get("severity", "-")
                atype    = a.get("type",     "-")
                desc     = a.get("description", "")
                ts       = _frame_to_time(frame, fps)
                sc       = _SEV_COLORS.get(severity, "#6c757d")
                all_rows += (
                    f"<tr><td>{r['model_folder']}</td><td><strong>{ts}</strong></td><td>{frame}</td>"
                    f"<td><span style='color:{sc};font-weight:bold'>{severity}</span></td>"
                    f"<td>{atype}</td><td>{desc}</td></tr>\n"
                )

        anomaly_badge = (
            "<span class='badge' style='background:#6c757d'>rastreamento</span>"
            if r["model_folder"] == "instrumentos" else
            f"<span class='badge' style='background:{mcolor}'>{mlabel}</span>"
        )
        anomaly_stat = "—" if r["model_folder"] == "instrumentos" else str(len(r["anomalies"]))
        rate_stat    = "—" if r["model_folder"] == "instrumentos" else f"{anomaly_rate:.1f}%"

        model_sections += f"""
    <div class="model-section">
      <div class="model-header">
        <span class="model-title">{r['model_folder'].replace('_', ' ').title()}</span>
        {anomaly_badge}
      </div>
      <div class="model-stats">
        <span>Detecções: <strong>{r['detections']}</strong></span>
        <span>Anomalias: <strong>{anomaly_stat}</strong></span>
        <span>Taxa: <strong>{rate_stat}</strong></span>
        <span>Média/frame: <strong>{avg:.2f}</strong></span>
      </div>
      {cls_table}
    </div>"""

    all_anomaly_section = (
        "<p class='no-data'>Nenhuma anomalia detectada em nenhum modelo.</p>"
        if not total_anomalies else
        f"""<table>
      <thead><tr><th>Modelo</th><th>Timestamp</th><th>Frame</th><th>Severidade</th><th>Tipo</th><th>Descrição</th></tr></thead>
      <tbody>{all_rows}</tbody>
    </table>"""
    )

    # Objectives cards (numbered, with objective subtitle)
    criteria_cards = ""
    for i, ev in enumerate(_evaluate_criteria(model_results), 1):
        c = ev["criterion"]
        if ev["triggered"]:
            border, bg, badge_bg, badge_txt = "#dc3545", "#fff5f5", "#dc3545", "ACIONADO"
            findings_html = "".join(
                f"<li><strong>{fd['folder']}</strong>: {fd['count']} ocorrência(s) — "
                f"<span style='color:#dc3545'>CRÍTICO:{fd['critico']}</span> "
                f"<span style='color:#fd7e14'>ALTO:{fd['alto']}</span> "
                f"<span style='color:#ffc107'>MÉDIO:{fd['medio']}</span></li>"
                for fd in ev["findings"]
            )
            rec_html = f"<p style='margin:8px 0 0;font-size:0.85em;color:#555'><strong>Recomendação:</strong> {c['recommendation']}</p>"
        else:
            border, bg, badge_bg, badge_txt = "#28a745", "#f0fff4", "#28a745", "SEM OCORRÊNCIAS"
            findings_html = rec_html = ""

        obj_sub = (
            f"<p style='margin:3px 0 0;font-size:0.78em;color:#777;font-style:italic'>{c['objective']}</p>"
            if c.get("objective") else ""
        )

        criteria_cards += f"""
    <div style="border-left:4px solid {border};background:{bg};padding:14px 18px;border-radius:4px;margin:10px 0">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
        <div>
          <span style="font-size:0.74em;font-weight:bold;color:#888;text-transform:uppercase;letter-spacing:0.08em">Objetivo {i}</span><br>
          <strong style="font-size:0.97em">{c['title']}</strong>
          {obj_sub}
        </div>
        <span style="background:{badge_bg};color:white;padding:2px 10px;border-radius:10px;font-size:0.78em;font-weight:bold;white-space:nowrap;margin-left:15px;flex-shrink:0">{badge_txt}</span>
      </div>
      <p style="margin:8px 0 0;font-size:0.84em;color:#555">{c['description']}</p>
      {"<ul style='margin:8px 0 0;padding-left:18px;font-size:0.85em'>" + findings_html + "</ul>" if findings_html else ""}
      {rec_html}
    </div>"""

    # Instrument timeline section
    instruments_html = ""
    for r in model_results:
        if r["model_folder"] == "instrumentos" and r.get("instrument_timeline"):
            rows_inst = ""
            for name, info in sorted(r["instrument_timeline"].items(), key=lambda x: -x[1]["count"]):
                first_ts  = _frame_to_time(info["first_frame"], fps) if info["count"] else "—"
                last_ts   = _frame_to_time(info["last_frame"],  fps) if info["count"] else "—"
                n_seg     = len(info["segments"]) if info["count"] else 0
                pct       = info["frames_pct"]
                bar_w     = min(int(pct) * 2, 200)
                count_str = str(info["count"]) if info["count"] else "—"
                seg_str   = str(n_seg) if n_seg else "—"
                rows_inst += (
                    f"<tr><td><strong>{name}</strong></td><td>{count_str}</td>"
                    f"<td>{first_ts}</td><td>{last_ts}</td><td>{seg_str}</td>"
                    f"<td><div class='bar-wrap'>"
                    f"<div class='bar' style='width:{bar_w}px'></div>"
                    f"<span>{pct:.1f}%</span></div></td></tr>\n"
                )
            instruments_html = f"""
  <h2>Instrumentos Cirúrgicos Utilizados</h2>
  <p style="color:#555;font-size:0.88em;margin-top:-8px">Modo rastreamento — identifica quais instrumentos foram utilizados e quando, sem classificação de anomalias.</p>
  <table>
    <thead><tr><th>Instrumento</th><th>Detecções</th><th>Primeiro Uso</th><th>Último Uso</th><th>Segmentos</th><th>Frequência</th></tr></thead>
    <tbody>{rows_inst}</tbody>
  </table>"""
            break

    combined_css = _BASE_CSS + """
  .badge { display: inline-block; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.82em; font-weight: bold; }
  .model-section { border: 1px solid #e0e0e0; border-radius: 6px; margin: 15px 0; overflow: hidden; }
  .model-header { background: #1a3a5c; color: white; padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; }
  .model-title { font-weight: bold; font-size: 1em; text-transform: uppercase; letter-spacing: 0.05em; }
  .model-stats { display: flex; gap: 25px; padding: 10px 15px; background: #f8f9fa; font-size: 0.88em; flex-wrap: wrap; }
"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<title>Relatório Consolidado — Tech Challenge Fase 4</title>
<style>{combined_css}</style>
</head>
<body>
<div class="container" style="max-width:1100px">
  <h1>Relatório Consolidado — Tech Challenge Fase 4</h1>
  <p style="color:#555;margin-top:-10px">Análise de Vídeo Especializada para Saúde da Mulher — YOLOv8 · 4 Modelos</p>
  <div class="meta">
    <strong>Vídeo:</strong> {video_name} &nbsp;|&nbsp;
    <strong>Duração:</strong> {duration} &nbsp;|&nbsp;
    <strong>Frames:</strong> {total_frames} &nbsp;|&nbsp;
    <strong>Data/Hora:</strong> {now}
  </div>

  <h2>Visão Geral</h2>
  <div class="grid-3">
    <div class="stat-card"><div class="value">{total_frames}</div><div class="label">Frames Analisados</div></div>
    <div class="stat-card"><div class="value">{len(model_results)}</div><div class="label">Modelos Executados</div></div>
    <div class="stat-card"><div class="value">{total_anomalies}</div><div class="label">Anomalias Totais</div></div>
    <div class="stat-card"><div class="value">{overall_rate:.1f}%</div><div class="label">Taxa Geral</div></div>
    <div class="stat-card" style="grid-column:span 2"><div class="value"><span class="risk-badge" style="background:{risk_color}">{risk_label}</span></div><div class="label">Risco Geral Consolidado</div></div>
  </div>

  <h2>Objetivos do Tech Challenge</h2>
  {criteria_cards}

  {instruments_html}

  <h2>Resultados por Modelo</h2>
  {model_sections}

  <h2>Linha do Tempo — Todas as Anomalias</h2>
  {all_anomaly_section}

  <div class="footer">Gerado automaticamente — Sistema de Análise Cirúrgica · Tech Challenge Fase 4 · POSTECH IADT</div>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _combined_json(path, model_results, video_name, now, total_frames, total_anomalies, fps, duration):
    overall_rate = (total_anomalies / total_frames) * 100 if total_frames else 0
    risk_label, _ = _get_risk_level(overall_rate)

    models_data = []
    for r in model_results:
        anomaly_rate = (len(r["anomalies"]) / r["frame_count"]) * 100 if r["frame_count"] else 0
        mlabel, _ = _get_risk_level(anomaly_rate)

        anomaly_list = []
        for a in r["anomalies"]:
            if isinstance(a, dict):
                frame = a.get("frame", 0)
                anomaly_list.append({
                    "frame": frame,
                    "timestamp": _frame_to_time(frame, fps),
                    "severity": a.get("severity"),
                    "type": a.get("type"),
                    "description": a.get("description"),
                })

        cs = r.get("class_summary", {})
        class_data = {}
        for name, info in cs.items():
            class_data[name] = {
                "count": info["count"],
                "first_seen": _frame_to_time(info["first_frame"], fps),
                "first_frame": info["first_frame"],
                "last_seen": _frame_to_time(info["last_frame"], fps),
                "last_frame": info["last_frame"],
                "frames_pct": info["frames_pct"],
            }

        timeline_data = {}
        for name, info in r.get("instrument_timeline", {}).items():
            timeline_data[name] = {
                "count": info["count"],
                "frames_pct": info["frames_pct"],
                "first_frame": info.get("first_frame"),
                "first_seen": _frame_to_time(info["first_frame"], fps) if info.get("first_frame") else None,
                "last_frame": info.get("last_frame"),
                "last_seen": _frame_to_time(info["last_frame"], fps) if info.get("last_frame") else None,
                "segments": info.get("segments", []),
            }

        entry = {
            "model": r["model_folder"],
            "total_detections": r["detections"],
            "class_detections": class_data,
            "anomalies": anomaly_list,
        }
        if r["model_folder"] == "instrumentos":
            entry["tracking_mode"] = True
            entry["instrument_timeline"] = timeline_data
        else:
            entry["anomaly_count"] = len(r["anomalies"])
            entry["anomaly_rate_pct"] = round(anomaly_rate, 2)
            entry["risk_level"] = mlabel
        models_data.append(entry)

    objectives_data = []
    for i, ev in enumerate(_evaluate_criteria(model_results), 1):
        c = ev["criterion"]
        objectives_data.append({
            "number": i,
            "title": c["title"],
            "objective": c.get("objective", c["title"]),
            "description": c["description"],
            "triggered": ev["triggered"],
            "recommendation": c["recommendation"] if ev["triggered"] else None,
            "findings": [
                {
                    "model": fd["folder"],
                    "occurrences": fd["count"],
                    "by_severity": {"CRÍTICO": fd["critico"], "ALTO": fd["alto"], "MÉDIO": fd["medio"]},
                }
                for fd in ev["findings"]
            ],
        })

    report_data = {
        "metadata": {
            "video_file": video_name,
            "analysis_date": datetime.now().isoformat(),
            "duration": duration,
            "fps": fps,
            "system": "YOLOv8 — Análise de Vídeo para Saúde da Mulher · Tech Challenge Fase 4",
        },
        "summary": {
            "total_frames": total_frames,
            "total_anomalies": total_anomalies,
            "overall_anomaly_rate_pct": round(overall_rate, 2),
            "overall_risk_level": risk_label,
            "models_count": len(model_results),
        },
        "tech_challenge_objectives": objectives_data,
        "models": models_data,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

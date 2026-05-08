import json
import os
from datetime import datetime


def generate_report(output_path, total_frames, total_detections, anomalies, fps=20, video_path=None):
    avg = total_detections / total_frames if total_frames > 0 else 0
    anomaly_rate = (len(anomalies) / total_frames) * 100 if total_frames > 0 else 0

    _generate_text_report(output_path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate)
    print(f"Relatório TXT salvo em: {output_path}")

    html_path = output_path.replace(".txt", ".html")
    _generate_html_report(html_path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate)
    print(f"Relatório HTML salvo em: {html_path}")

    json_path = output_path.replace(".txt", ".json")
    _generate_json_report(json_path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate)
    print(f"Relatório JSON salvo em: {json_path}")


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


def _anomaly_to_str(a):
    if isinstance(a, dict):
        frame = a.get("frame", "-")
        severity = a.get("severity", "-")
        desc = a.get("description", "")
        return f"Frame {frame} [{severity}]: {desc}"
    return str(a)


def _count_by_type(anomalies, atype):
    return sum(1 for a in anomalies if isinstance(a, dict) and a.get("type") == atype)


def _generate_text_report(output_path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate):
    risk_label, _ = _get_risk_level(anomaly_rate)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("  RELATÓRIO DE ANÁLISE CIRÚRGICA ESPECIALIZADA\n")
        f.write("  Saúde da Mulher - Detecção de Instrumentos\n")
        f.write("=" * 50 + "\n\n")

        f.write(f"Data/Hora: {now}\n")
        if video_path:
            f.write(f"Vídeo: {os.path.basename(video_path)}\n")
        f.write(f"FPS: {fps}\n\n")

        f.write("--- RESUMO ESTATÍSTICO ---\n")
        f.write(f"Frames analisados:    {total_frames}\n")
        f.write(f"Detecções totais:     {total_detections}\n")
        f.write(f"Média por frame:      {avg:.2f}\n")
        f.write(f"Anomalias detectadas: {len(anomalies)}\n")
        f.write(f"Taxa de anomalia:     {anomaly_rate:.2f}%\n")
        f.write(f"Nível de risco:       {risk_label}\n\n")

        f.write("--- ANOMALIAS DETECTADAS ---\n")
        if not anomalies:
            f.write("Nenhuma anomalia detectada.\n")
        else:
            for a in anomalies:
                f.write(_anomaly_to_str(a) + "\n")

        absences = _count_by_type(anomalies, "AUSÊNCIA")
        excesses = _count_by_type(anomalies, "EXCESSO")
        variations = _count_by_type(anomalies, "VARIAÇÃO")

        f.write("\n--- AVALIAÇÃO CLÍNICA ---\n")
        f.write(f"Ausências prolongadas:  {absences}\n")
        f.write(f"Excessos de instrumentos: {excesses}\n")
        f.write(f"Variações bruscas:      {variations}\n\n")

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
            f.write(f"- Revisar {absences} segmentos com ausência prolongada de instrumentos.\n")
        if excesses > 0:
            f.write(f"- Verificar {excesses} frames com excesso de instrumentos no campo.\n")
        if variations > 0:
            f.write(f"- Investigar {variations} variações bruscas no número de instrumentos.\n")


def _generate_html_report(path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate):
    risk_label, risk_color = _get_risk_level(anomaly_rate)
    video_name = os.path.basename(video_path) if video_path else "N/A"
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    absences = _count_by_type(anomalies, "AUSÊNCIA")
    excesses = _count_by_type(anomalies, "EXCESSO")
    variations = _count_by_type(anomalies, "VARIAÇÃO")

    rows = ""
    for a in anomalies:
        if isinstance(a, dict):
            frame = a.get("frame", "-")
            severity = a.get("severity", "-")
            atype = a.get("type", "-")
            desc = a.get("description", "")
            ts = _frame_to_time(frame, fps)
            sev_colors = {"CRÍTICO": "#dc3545", "ALTO": "#fd7e14", "MÉDIO": "#ffc107", "BAIXO": "#28a745"}
            sc = sev_colors.get(severity, "#6c757d")
            rows += (
                f"<tr>"
                f"<td>{frame}</td>"
                f"<td>{ts}</td>"
                f"<td><span style='color:{sc};font-weight:bold'>{severity}</span></td>"
                f"<td>{atype}</td>"
                f"<td>{desc}</td>"
                f"</tr>\n"
            )
        else:
            rows += f"<tr><td colspan='5'>{str(a)}</td></tr>\n"

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
        items.append(f"<li><strong>Ausências prolongadas ({absences}):</strong> Revisar segmentos sem instrumentos — possível troca não registrada ou queda de instrumento.</li>")
    if excesses > 0:
        items.append(f"<li><strong>Excessos ({excesses}):</strong> Verificar frames com muitos instrumentos — possível falta de controle do campo cirúrgico.</li>")
    if variations > 0:
        items.append(f"<li><strong>Variações bruscas ({variations}):</strong> Investigar transições abruptas — possível manobra não planejada.</li>")
    if items:
        recs.append("<ul>" + "".join(items) + "</ul>")

    anomaly_section = (
        "<p class='no-anomalies'>Nenhuma anomalia detectada durante o procedimento.</p>"
        if not anomalies else
        f"""<table>
      <thead><tr><th>Frame</th><th>Timestamp</th><th>Severidade</th><th>Tipo</th><th>Descrição</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Análise Cirúrgica</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; color: #333; }}
  .container {{ max-width: 1000px; margin: auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
  h1 {{ color: #1a3a5c; border-bottom: 3px solid #1a3a5c; padding-bottom: 10px; margin-top: 0; }}
  h2 {{ color: #1a3a5c; margin-top: 30px; border-left: 4px solid #1a3a5c; padding-left: 10px; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 25px; background: #f8f9fa; padding: 10px 15px; border-radius: 4px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
  .stat-card {{ background: #f8f9fa; border-left: 4px solid #1a3a5c; padding: 15px; border-radius: 4px; }}
  .stat-card .value {{ font-size: 1.8em; font-weight: bold; color: #1a3a5c; }}
  .stat-card .label {{ font-size: 0.82em; color: #666; margin-top: 4px; }}
  .risk-badge {{ display: inline-block; background: {risk_color}; color: white; padding: 6px 16px; border-radius: 20px; font-size: 1em; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9em; }}
  th {{ background: #1a3a5c; color: white; padding: 10px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f8f9fa; }}
  .recommendations {{ background: #e8f4fd; border-left: 4px solid #1a3a5c; padding: 15px 20px; border-radius: 4px; margin-top: 15px; }}
  .no-anomalies {{ color: #28a745; font-style: italic; }}
  .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 0.8em; border-top: 1px solid #eee; padding-top: 15px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Relatório de Análise Cirúrgica Especializada</h1>
  <p style="color:#555;margin-top:-10px">Saúde da Mulher — Detecção de Instrumentos Cirúrgicos Ginecológicos (YOLOv8)</p>

  <div class="meta">
    <strong>Vídeo:</strong> {video_name} &nbsp;|&nbsp;
    <strong>Data/Hora:</strong> {now} &nbsp;|&nbsp;
    <strong>FPS:</strong> {fps}
  </div>

  <h2>Resumo Estatístico</h2>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="value">{total_frames}</div>
      <div class="label">Frames Analisados</div>
    </div>
    <div class="stat-card">
      <div class="value">{total_detections}</div>
      <div class="label">Detecções Totais</div>
    </div>
    <div class="stat-card">
      <div class="value">{avg:.2f}</div>
      <div class="label">Média por Frame</div>
    </div>
    <div class="stat-card">
      <div class="value">{len(anomalies)}</div>
      <div class="label">Anomalias Detectadas</div>
    </div>
    <div class="stat-card">
      <div class="value">{anomaly_rate:.1f}%</div>
      <div class="label">Taxa de Anomalia</div>
    </div>
    <div class="stat-card">
      <div class="value"><span class="risk-badge">{risk_label}</span></div>
      <div class="label">Nível de Risco Clínico</div>
    </div>
  </div>

  <h2>Distribuição de Anomalias</h2>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="value" style="color:#dc3545">{absences}</div>
      <div class="label">Ausências Prolongadas</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:#fd7e14">{excesses}</div>
      <div class="label">Excessos de Instrumentos</div>
    </div>
    <div class="stat-card">
      <div class="value" style="color:#ffc107">{variations}</div>
      <div class="label">Variações Bruscas</div>
    </div>
  </div>

  <h2>Linha do Tempo de Anomalias</h2>
  {anomaly_section}

  <h2>Avaliação de Risco Clínico</h2>
  <div class="recommendations">
    {"".join(recs)}
  </div>

  <div class="footer">
    Gerado automaticamente pelo Sistema de Análise Cirúrgica — Tech Challenge Fase 4 · POSTECH IADT
  </div>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _generate_json_report(path, total_frames, total_detections, anomalies, fps, video_path, avg, anomaly_rate):
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

    report_data = {
        "metadata": {
            "video_file": os.path.basename(video_path) if video_path else None,
            "analysis_date": datetime.now().isoformat(),
            "fps": fps,
            "system": "YOLOv8 - Ginecological Surgical Instrument Detector",
        },
        "summary": {
            "total_frames": total_frames,
            "total_detections": total_detections,
            "avg_detections_per_frame": round(avg, 2),
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": round(anomaly_rate, 2),
            "risk_level": risk_label,
            "by_type": {
                "AUSÊNCIA": _count_by_type(anomalies, "AUSÊNCIA"),
                "EXCESSO": _count_by_type(anomalies, "EXCESSO"),
                "VARIAÇÃO": _count_by_type(anomalies, "VARIAÇÃO"),
            },
        },
        "anomalies": anomaly_list,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

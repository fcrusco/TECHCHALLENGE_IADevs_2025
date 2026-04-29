def generate_report(output_path, total_frames, total_detections, anomalies):
    avg = total_detections / total_frames if total_frames > 0 else 0

    with open(output_path, "w") as f:
        f.write("=== RELATÓRIO DE ANÁLISE ===\n\n")
        f.write(f"Frames analisados: {total_frames}\n")
        f.write(f"Detecções totais: {total_detections}\n")
        f.write(f"Média por frame: {avg:.2f}\n")
        f.write(f"Anomalias detectadas: {len(anomalies)}\n\n")

        f.write("=== LISTA DE ANOMALIAS ===\n")
        for a in anomalies:
            f.write(a + "\n")

    print(f"📄 Relatório salvo em: {output_path}")
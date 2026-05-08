import argparse
import os
import shutil
import importlib.util
from ultralytics import YOLO
import cv2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
history = []
WINDOW = 10

# Thresholds for anomaly detection
ABSENCE_WARN_FRAMES = 10
ABSENCE_CRITICAL_FRAMES = 30
EXCESS_THRESHOLD = 5
VARIATION_THRESHOLD = 3
CONFIDENCE_THRESHOLD = 0.55
SURGICAL_CLASSES = [0, 1, 2, 3]  # Scalpel, Clamp, Straight Scissor, Curved Scissor

# Geometric filter limits
MIN_BOX_AREA_RATIO  = 0.002  # box must cover at least 0.2% of frame
MAX_BOX_AREA_RATIO  = 0.50   # box must not cover more than 50% of frame
MIN_ASPECT_RATIO    = 1.5    # instruments are elongated; 1.5 tolerates diagonal orientations
EDGE_MARGIN_RATIO   = 0.008  # boxes starting within 0.8% of frame edge = overlay
OVERLAY_ZONE_TOP    = 0.22   # top 22% of frame is watermark/logo territory
OVERLAY_ZONE_BOTTOM = 0.80   # bottom 20% of frame is subtitle/text territory


def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils_module = import_from_file("utils", os.path.join(PROJECT_ROOT, "src", "utils.py"))
extract_frames = utils_module.extract_frames

report_module = import_from_file("report", os.path.join(PROJECT_ROOT, "src", "report.py"))
generate_report = report_module.generate_report


def download_dataset():
    download_module = import_from_file(
        "download_dataset",
        os.path.join(PROJECT_ROOT, "scripts", "download_dataset.py")
    )
    download_module.main()


def train_model():
    dataset_yaml = os.path.join(PROJECT_ROOT, "dataset.yaml")

    if not os.path.exists(dataset_yaml):
        print(f"O arquivo dataset.yaml não foi encontrado em: {dataset_yaml}")
        return

    output_dir = os.path.join(PROJECT_ROOT, "instrument_detector")
    if os.path.exists(output_dir):
        print(f"Limpando treino anterior: {output_dir}")
        shutil.rmtree(output_dir)

    try:
        print("Iniciando treinamento YOLOv8 para detecção de instrumentos ginecológicos...")
        model = YOLO("yolov8s.pt")

        model.train(
            data=dataset_yaml,
            epochs=80,
            imgsz=640,
            batch=16,
            name="instrument_detector",
            patience=20,
            device=0,
            exist_ok=True,
            project=PROJECT_ROOT,
            # Augmentation
            mosaic=1.0,
            flipud=0.3,
            fliplr=0.5,
            degrees=10.0,
            translate=0.1,
            scale=0.5,
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
        )

        print("Treinamento YOLOv8 concluído!")
        print(f"Modelo salvo em: {os.path.join(PROJECT_ROOT, 'instrument_detector', 'weights', 'best.pt')}")

    except Exception as e:
        print(f"Erro no treinamento: {e}")


def _find_trained_model():
    """Search for a trained model in all standard output locations."""
    candidates = [
        os.path.join(PROJECT_ROOT, "instrument_detector", "weights", "best.pt"),
        os.path.join(PROJECT_ROOT, "runs", "instrument_detector", "weights", "best.pt"),
        os.path.join(PROJECT_ROOT, "runs", "detect", "instrument_detector", "weights", "best.pt"),
    ]

    # Also scan runs/detect/ for any instrument_detector* run
    runs_detect = os.path.join(PROJECT_ROOT, "runs", "detect")
    if os.path.exists(runs_detect):
        subdirs = sorted(
            [d for d in os.listdir(runs_detect)
             if os.path.isdir(os.path.join(runs_detect, d)) and d.startswith("instrument_detector")],
            reverse=True,
        )
        for sd in subdirs:
            candidates.append(os.path.join(runs_detect, sd, "weights", "best.pt"))

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _filter_surgical_boxes(results, frame_w, frame_h):
    """Discard detections that cannot geometrically be surgical instruments.

    Rules applied (in order):
      1. Area too small (<0.2% of frame) or too large (>50%) → noise / background
      2. Aspect ratio < 1.8 → too square; instruments are always elongated
      3. Box touches frame edge → video overlay (logos/text always start at the edge)
      4. Box is wide (landscape) AND center is in top/bottom overlay zone → text banner
    """
    if not results or len(results) == 0:
        return results

    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return results

    frame_area = frame_w * frame_h
    edge_px = max(frame_w, frame_h) * EDGE_MARGIN_RATIO
    xyxy = boxes.xyxy.cpu().numpy()

    keep = []
    for i, (x1, y1, x2, y2) in enumerate(xyxy):
        w   = float(x2 - x1)
        h   = float(y2 - y1)
        cx  = (x1 + x2) / 2.0
        cy  = (y1 + y2) / 2.0
        area_ratio = (w * h) / frame_area
        aspect     = max(w, h) / max(min(w, h), 1.0)

        # 1. Area sanity check
        if area_ratio < MIN_BOX_AREA_RATIO:
            continue
        if area_ratio > MAX_BOX_AREA_RATIO:
            continue

        # 2. Shape: instruments are always elongated
        if aspect < MIN_ASPECT_RATIO:
            continue

        # 3. Box touches any frame edge → almost certainly a video overlay
        if x1 < edge_px or y1 < edge_px or x2 > frame_w - edge_px or y2 > frame_h - edge_px:
            continue

        # 4. Wide (landscape) box centred in the top or bottom overlay zone → text banner
        is_landscape = w > h
        in_overlay   = cy < frame_h * OVERLAY_ZONE_TOP or cy > frame_h * OVERLAY_ZONE_BOTTOM
        if is_landscape and in_overlay:
            continue

        keep.append(i)

    results[0].boxes = results[0].boxes[keep]
    return results


def _make_anomaly(frame, atype, severity, description):
    return {
        "frame": frame,
        "type": atype,
        "severity": severity,
        "description": description,
    }


def detect_video(video_path, model_path=None, headless=False, save_output=True):
    global history
    history = []

    if not os.path.exists(video_path):
        print(f"Vídeo não encontrado: {video_path}")
        return

    if model_path is None:
        model_path = _find_trained_model()
        if model_path:
            print(f"Usando modelo treinado: {model_path}")
        else:
            print("ERRO: Nenhum modelo treinado encontrado.")
            print("Execute primeiro: python app.py train")
            return

    if not os.path.exists(model_path):
        print(f"ERRO: Modelo não encontrado em: {model_path}")
        return

    try:
        model = YOLO(model_path)

        # Force PT-BR class names on the loaded model so plot() renders in Portuguese
        NAMES_PTBR = {
            0: "Bisturi",
            1: "Pinca de Dissecao",
            2: "Tesoura Mayo Reta",
            3: "Tesoura Mayo Curva",
        }
        if len(model.names) == 4:
            model.model.names = NAMES_PTBR
        else:
            print(f"AVISO: modelo carregado tem {len(model.names)} classes, esperado 4.")
            print(f"  Classes do modelo: {model.names}")
            print("  Treine novamente com: python app.py train")

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Não foi possível abrir o vídeo: {video_path}")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 20

        out = None
        if save_output:
            output_video = os.path.join(PROJECT_ROOT, "output_detected.mp4")
            out = cv2.VideoWriter(
                output_video,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height),
            )

        frame_count = 0
        detections_count = 0
        anomalies = []
        no_instrument_streak = 0

        print("Iniciando análise inteligente de instrumentos cirúrgicos...")
        print(f"Vídeo: {os.path.basename(video_path)} | {width}x{height} @ {fps:.1f}fps")

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame is None or frame.size == 0:
                continue

            frame_count += 1
            results = model(
                frame,
                conf=CONFIDENCE_THRESHOLD,
                iou=0.45,
                classes=SURGICAL_CLASSES,
                verbose=False,
            )
            results = _filter_surgical_boxes(results, width, height)

            num_instruments = 0
            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None and len(boxes):
                    num_instruments = len(boxes)
                    detections_count += num_instruments

            history.append(num_instruments)
            if len(history) > WINDOW:
                history.pop(0)

            avg_recent = sum(history) / len(history)

            # Track absence streak
            if num_instruments == 0:
                no_instrument_streak += 1
            else:
                no_instrument_streak = 0

            alert_text = ""
            alert_color = (0, 255, 0)
            anomaly = None

            # Critical absence (>30 consecutive frames)
            if no_instrument_streak == ABSENCE_CRITICAL_FRAMES:
                anomaly = _make_anomaly(
                    frame_count, "AUSÊNCIA", "CRÍTICO",
                    f"Ausência crítica de instrumentos ({no_instrument_streak} frames consecutivos) — "
                    "possível falha de controle cirúrgico"
                )
                alert_text = "ALERTA CRÍTICO: AUSÊNCIA PROLONGADA"
                alert_color = (0, 0, 200)

            # Warning absence (>10 consecutive frames, not yet critical)
            elif no_instrument_streak == ABSENCE_WARN_FRAMES:
                anomaly = _make_anomaly(
                    frame_count, "AUSÊNCIA", "ALTO",
                    f"Ausência prolongada de instrumentos ({no_instrument_streak} frames consecutivos) — "
                    "possível troca não registrada"
                )
                alert_text = "ALERTA: AUSÊNCIA PROLONGADA"
                alert_color = (0, 0, 255)

            # Excess instruments
            elif num_instruments > EXCESS_THRESHOLD:
                anomaly = _make_anomaly(
                    frame_count, "EXCESSO", "MÉDIO",
                    f"Excesso de instrumentos no campo cirúrgico ({num_instruments} detectados) — "
                    "verificar controle do campo operatório"
                )
                alert_text = f"ALERTA: EXCESSO ({num_instruments} instrumentos)"
                alert_color = (0, 165, 255)

            # Sudden variation
            elif len(history) >= WINDOW:
                delta = abs(num_instruments - avg_recent)
                if delta > VARIATION_THRESHOLD:
                    anomaly = _make_anomaly(
                        frame_count, "VARIAÇÃO", "MÉDIO",
                        f"Variação brusca no número de instrumentos (delta={delta:.1f}, média={avg_recent:.1f}) — "
                        "possível manobra não planejada"
                    )
                    alert_text = "ANOMALIA: VARIAÇÃO BRUSCA"
                    alert_color = (255, 0, 255)

            if anomaly:
                anomalies.append(anomaly)

            # Draw overlay
            annotated_frame = results[0].plot() if (results and len(results) > 0) else frame.copy()

            _draw_hud(annotated_frame, frame_count, num_instruments, avg_recent, alert_text, alert_color, height)

            if out:
                out.write(annotated_frame)

            if not headless:
                cv2.imshow("Análise Cirúrgica - Instrumentos Ginecológicos", annotated_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

        cap.release()
        if out:
            out.release()
        if not headless:
            cv2.destroyAllWindows()

        avg = detections_count / frame_count if frame_count > 0 else 0
        anomaly_rate = (len(anomalies) / frame_count) * 100 if frame_count > 0 else 0

        report_path = os.path.join(PROJECT_ROOT, "report.txt")
        generate_report(report_path, frame_count, detections_count, anomalies, fps=fps, video_path=video_path)

        print("\n=== RESULTADO FINAL ===")
        print(f"Frames analisados: {frame_count}")
        print(f"Detecções totais:  {detections_count}")
        print(f"Média por frame:   {avg:.2f}")
        print(f"Anomalias:         {len(anomalies)}")
        print(f"Taxa de anomalia:  {anomaly_rate:.2f}%")
        print(f"\nArquivos gerados:")
        print(f"  Vídeo anotado: output_detected.mp4")
        print(f"  Relatório TXT: report.txt")
        print(f"  Relatório HTML: report.html")
        print(f"  Relatório JSON: report.json")

    except Exception as e:
        print(f"Erro na detecção: {e}")
        raise


def _draw_hud(frame, frame_count, num_instruments, avg_recent, alert_text, alert_color, height):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (340, 110), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    det_color = (0, 255, 0) if num_instruments > 0 else (80, 80, 80)
    cv2.putText(frame, f"Detectados: {num_instruments}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, det_color, 2)
    cv2.putText(frame, f"Media (10q): {avg_recent:.1f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    cv2.putText(frame, f"Quadro: {frame_count}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 160, 160), 2)

    if alert_text:
        bar_h = 50
        cv2.rectangle(frame, (0, height - bar_h), (frame.shape[1], height), (0, 0, 0), -1)
        cv2.putText(frame, alert_text, (10, height - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, alert_color, 3)


def extract_frames_from_video(video_path, output_dir):
    extract_frames(video_path, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Análise de Instrumentos Cirúrgicos Ginecológicos (YOLOv8)"
    )
    parser.add_argument(
        "action",
        choices=["download", "train", "detect", "extract"],
        help="Ação a executar",
    )
    parser.add_argument("--video", help="Caminho para o vídeo a analisar")
    parser.add_argument("--output", help="Pasta de saída para extração de frames")
    parser.add_argument("--model", default=None, help="Caminho para o modelo (.pt)")
    parser.add_argument("--headless", action="store_true",
                        help="Executar sem janela de visualização (para servidores)")

    args = parser.parse_args()

    if args.action == "download":
        download_dataset()

    elif args.action == "train":
        train_model()

    elif args.action == "detect":
        if not args.video:
            print("Erro: --video é obrigatório para a ação 'detect'")
            parser.print_help()
            return
        detect_video(args.video, args.model, args.headless)

    elif args.action == "extract":
        if not args.video or not args.output:
            print("Erro: --video e --output são obrigatórios para a ação 'extract'")
            parser.print_help()
            return
        extract_frames_from_video(args.video, args.output)


if __name__ == "__main__":
    main()

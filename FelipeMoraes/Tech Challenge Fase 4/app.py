import argparse
import os
import importlib.util
from ultralytics import YOLO
import cv2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
history = []
WINDOW = 10

def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

utils_module = import_from_file("utils", os.path.join(PROJECT_ROOT, "src", "utils.py"))
extract_frames = utils_module.extract_frames

report_module = import_from_file("report", os.path.join(PROJECT_ROOT, "src", "report.py"))
generate_report = report_module.generate_report

# Download do Dataset
def download_dataset():
    download_module = import_from_file(
        "download_dataset",
        os.path.join(PROJECT_ROOT, "scripts", "download_dataset.py")
    )
    download_module.main()

# Treinamento do Modelo
def train_model():
    dataset_yaml = os.path.join(PROJECT_ROOT, "dataset.yaml")

    if not os.path.exists(dataset_yaml):
        print(f"O arquivo dataset.yaml não foi encontrado")
        return

    try:
        print("Treinando modelo YOLO...")
        model = YOLO("yolov8s.pt")

        model.train(
            data=dataset_yaml,
            epochs=50,
            imgsz=640,
            batch=8,
            name="instrument_detector",
            patience=20,
            device=0,
            exist_ok=True,
            project=PROJECT_ROOT
        )

        print("Treinamento YOLO concluído!")

    except Exception as e:
        print(f"Erro encontrado: {e}")

# Detecção
def detect_video(
        video_path,
        model_path=None,
        headless=False,
        save_output=True
):
    global history

    if not os.path.exists(video_path):
        print("Vídeo não encontrado")
        return

    if model_path is None:
        runs_dir = os.path.join(PROJECT_ROOT, "runs", "detect")
        if os.path.exists(runs_dir):
            subdirs = [d for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d)) and d.startswith("instrument_detector")]
            if subdirs:
                subdirs.sort(reverse=True)
                latest = subdirs[0]
                model_path = os.path.join(runs_dir, latest, "weights", "best.pt")
                print(f"Usando modelo: {model_path}")
            else:
                print("Nenhum modelo treinado encontrado. Usando yolov8n.pt")
                model_path = "yolov8n.pt"
        else:
            print("Diretório runs/detect não encontrado. Usando yolov8n.pt")
            model_path = "yolov8n.pt"

    if not os.path.exists(model_path):
        print("Modelo não encontrado")
        return

    try:
        model = YOLO(model_path)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print("Não foi possível abrir o vídeo...")
            return

        width = int(cap.get(3))
        height = int(cap.get(4))
        fps = cap.get(5) or 20

        out = None
        if save_output:
            out = cv2.VideoWriter(
                "output_detected.mp4",
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (width, height)
            )

        frame_count = 0
        detections_count = 0
        anomalies = []

        no_instrument_streak = 0

        print("Iniciando análise inteligente...")

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            if frame is None or frame.size == 0:
                continue

            frame_count += 1
            results = model(frame, conf=0.5, iou=0.5)

            num_instruments = 0

            if results and len(results) > 0:
                boxes = results[0].boxes

                if boxes is not None:
                    confs = boxes.conf.cpu().numpy()
                    num_instruments = sum(c > 0.6 for c in confs)
                    detections_count += num_instruments

            # Histórico
            history.append(num_instruments)

            if len(history) > WINDOW:
                history.pop(0)

            avg_recent = sum(history) / len(history)

            # Anomalia
            alert_text = ""
            alert_color = (0, 255, 0)

            # Ausência Prolongada
            if num_instruments == 0:
                no_instrument_streak += 1
            else:
                no_instrument_streak = 0

            if no_instrument_streak >= 10:
                alert_text = "ALERTA: AUSÊNCIA PROLONGADA"
                alert_color = (0, 0, 255)
                anomalies.append(f"Frame {frame_count}: ausência prolongada")

            # Excesso
            elif num_instruments > 5:
                alert_text = f"ALERTA: EXCESSO ({num_instruments})"
                alert_color = (0, 165, 255)
                anomalies.append(f"Frame {frame_count}: excesso")

            # Variação Brusca
            elif len(history) >= WINDOW:
                if abs(num_instruments - avg_recent) > 3:
                    alert_text = "ANOMALIA: VARIAÇÃO BRUSCA"
                    alert_color = (255, 0, 255)
                    anomalies.append(f"Frame {frame_count}: variação brusca")

            # Overlay
            annotated_frame = frame.copy()

            if results and len(results) > 0:
                annotated_frame = results[0].plot()

            cv2.putText(
                annotated_frame,
                f"Instruments: {num_instruments}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )

            cv2.putText(
                annotated_frame,
                f"Frame: {frame_count}",
                (10, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            # Média Recente
            cv2.putText(
                annotated_frame,
                f"Avg: {avg_recent:.2f}",
                (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (200, 200, 200),
                2
            )

            if alert_text:
                cv2.putText(
                    annotated_frame,
                    alert_text,
                    (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    alert_color,
                    3
                )

            # salvar
            if out:
                out.write(annotated_frame)

            # mostrar
            if not headless:
                cv2.imshow("Detecção Inteligente", annotated_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

        cap.release()

        if out:
            out.release()

        if not headless:
            cv2.destroyAllWindows()

        # Relatório Otimizado
        avg = detections_count / frame_count if frame_count > 0 else 0
        anomaly_rate = (len(anomalies) / frame_count) * 100 if frame_count > 0 else 0

        generate_report(
            "report.txt",
            frame_count,
            detections_count,
            anomalies
        )

        print("\nRESULTADO FINAL")
        print(f"Frames: {frame_count}")
        print(f"Detecções: {detections_count}")
        print(f"Média/frame: {avg:.2f}")
        print(f"Anomalias: {len(anomalies)}")
        print(f"Taxa de anomalia: {anomaly_rate:.2f}%")

        print("output_detected.mp4 gerado")
        print("report.txt gerado")

    except Exception as e:
        print(f"Erro: {e}")


# Extração
def extract_frames_from_video(video_path, output_dir):
    extract_frames(video_path, output_dir)

# CLI
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("action", choices=["download", "train", "detect", "extract"])
    parser.add_argument("--video")
    parser.add_argument("--output")
    parser.add_argument("--model", default=None)
    parser.add_argument("--headless", action="store_true")

    args = parser.parse_args()

    if args.action == "download":
        download_dataset()

    elif args.action == "train":
        train_model()

    elif args.action == "detect":
        detect_video(args.video, args.model, args.headless)

    elif args.action == "extract":
        extract_frames_from_video(args.video, args.output)


if __name__ == "__main__":
    main()
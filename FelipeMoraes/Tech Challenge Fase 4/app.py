import argparse
import os
import importlib.util
from ultralytics import YOLO
import cv2

# Get the absolute path to the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# =========================
# Dynamic import helper
# =========================
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =========================
# Imports dinâmicos
# =========================
utils_module = import_from_file("utils", os.path.join(PROJECT_ROOT, "src", "utils.py"))
extract_frames = utils_module.extract_frames

report_module = import_from_file("report", os.path.join(PROJECT_ROOT, "src", "report.py"))
generate_report = report_module.generate_report


# =========================
# Dataset
# =========================
def download_dataset():
    download_module = import_from_file(
        "download_dataset",
        os.path.join(PROJECT_ROOT, "scripts", "download_dataset.py")
    )
    download_module.main()


# =========================
# Train
# =========================
def train_model():
    dataset_yaml = os.path.join(PROJECT_ROOT, "dataset.yaml")

    if not os.path.exists(dataset_yaml):
        print(f"❌ dataset.yaml não encontrado")
        return

    try:
        print("🚀 Treinando modelo...")
        model = YOLO("yolov8n.pt")

        model.train(
            data=dataset_yaml,
            epochs=50,
            imgsz=640,
            batch=8,
            name="instrument_detector",
            patience=10
        )

        print("✅ Treinamento concluído!")

    except Exception as e:
        print(f"❌ Erro: {e}")


# =========================
# Detect
# =========================
def detect_video(
        video_path,
        model_path="runs/detect/instrument_detector/weights/best.pt",
        headless=False,
        save_output=True
):
    if not os.path.exists(video_path):
        print("❌ Vídeo não encontrado")
        return

    if not os.path.exists(model_path):
        print("❌ Modelo não encontrado")
        return

    try:
        model = YOLO(model_path)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print("❌ Não abriu o vídeo")
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

        # 🔥 lógica temporal
        no_instrument_streak = 0

        print("▶️ Iniciando análise...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            results = model(frame)

            num_instruments = 0

            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None:
                    num_instruments = len(boxes)
                    detections_count += num_instruments

            # =========================
            # ANOMALIA
            # =========================
            alert_text = ""
            alert_color = (0, 255, 0)

            if num_instruments == 0:
                no_instrument_streak += 1
            else:
                no_instrument_streak = 0

            if no_instrument_streak >= 10:
                alert_text = "ALERTA: AUSÊNCIA PROLONGADA"
                alert_color = (0, 0, 255)
                anomalies.append(f"Frame {frame_count}: ausência prolongada")

            elif num_instruments > 5:
                alert_text = f"ALERTA: EXCESSO ({num_instruments})"
                alert_color = (0, 165, 255)
                anomalies.append(f"Frame {frame_count}: excesso")

            # =========================
            # Overlay
            # =========================
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
                cv2.imshow("Detecção", annotated_frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

        cap.release()

        if out:
            out.release()

        if not headless:
            cv2.destroyAllWindows()

        # =========================
        # RELATÓRIO
        # =========================
        generate_report(
            "report.txt",
            frame_count,
            detections_count,
            anomalies
        )

        print("📁 output_detected.mp4 gerado")

    except Exception as e:
        print(f"❌ Erro: {e}")


# =========================
# Extract
# =========================
def extract_frames_from_video(video_path, output_dir):
    extract_frames(video_path, output_dir)


# =========================
# CLI
# =========================
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("action", choices=["download", "train", "detect", "extract"])
    parser.add_argument("--video")
    parser.add_argument("--output")
    parser.add_argument("--model", default="runs/detect/instrument_detector/weights/best.pt")
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
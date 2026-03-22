import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.assistant.pipeline import MedicalAssistantPipeline


def generate_graph_image():
    print("Inicializando pipeline...")
    pipeline = MedicalAssistantPipeline(user_id="debug")

    print("Gerando imagem do LangGraph...")

    graph = pipeline.graph

    output_path = Path("docs/langgraph_real.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    png_bytes = graph.get_graph().draw_mermaid_png()

    with open(output_path, "wb") as f:
        f.write(png_bytes)

    print(f"Imagem gerada com sucesso em: {output_path}")


if __name__ == "__main__":
    generate_graph_image()
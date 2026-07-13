"""Detecção local de componentes de arquitetura via modelo de visão treinado
(YOLOv8n, ver training/vision/). Substitui a chamada a uma VLM externa
(GPT-4o/Ollama/LM Studio) na etapa de identificação de componentes por
inferência de um modelo supervisionado treinado especificamente para essa
tarefa — ver training/vision/README ou a seção "Modelo Treinado Visão" do
README principal.

Import de ultralytics/torch fica dentro das funções (não no topo do módulo)
para não exigir essa dependência pesada de quem não usa esta opção.
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VISION_WEIGHTS_PATH = Path(__file__).parent.parent / "training" / "vision" / "output" / "stride-vision-yolov8n.pt"

TYPE_NOUN_PT = {
    "user": "Usuário",
    "web_server": "Servidor Web",
    "api_gateway": "API Gateway",
    "load_balancer": "Load Balancer",
    "application_server": "Servidor de Aplicação",
    "database": "Banco de Dados",
    "cache": "Cache",
    "message_queue": "Fila de Mensagens",
    "authentication_service": "Serviço de Autenticação",
    "cdn": "CDN",
    "firewall": "Firewall",
    "storage": "Armazenamento",
    "microservice": "Microsserviço",
    "container": "Container",
    "function": "Função Serverless",
    "network": "Rede",
    "external_service": "Serviço Externo",
    "monitoring": "Monitoramento",
    "dns": "DNS",
    "vpn": "VPN",
}

# Descrições curtas e semânticas por tipo — mesmo estilo/tamanho do
# TYPE_DESCRIPTIONS usado em training/architectures.py para gerar o dataset
# de fine-tuning do modelo STRIDE (training/seed_kb.py). Usadas no lugar de
# uma frase de "confiança de detecção" porque o modelo STRIDE foi treinado
# vendo descrições assim — uma frase fora desse padrão (fora de distribuição)
# tende a fazer o modelo fugir do formato esperado na resposta (já visto
# gerar uma resposta 25x maior que o normal quando a descrição destoava).
TYPE_DESCRIPTIONS_PT = {
    "user": "Usuário final que interage com o sistema",
    "web_server": "Servidor web que serve conteúdo HTTP/HTTPS",
    "api_gateway": "Gateway de API que roteia e gerencia requisições",
    "load_balancer": "Balanceador de carga que distribui tráfego entre instâncias",
    "application_server": "Servidor de aplicação que processa a lógica de negócio",
    "database": "Banco de dados relacional ou NoSQL",
    "cache": "Camada de cache em memória",
    "message_queue": "Fila de mensagens para comunicação assíncrona",
    "authentication_service": "Serviço de autenticação e autorização",
    "cdn": "Rede de distribuição de conteúdo (CDN)",
    "firewall": "Firewall de rede ou WAF filtrando tráfego",
    "storage": "Serviço de armazenamento de arquivos ou objetos",
    "microservice": "Microsserviço da arquitetura distribuída",
    "container": "Container executando um serviço da aplicação",
    "function": "Função serverless executada sob demanda",
    "network": "Componente de rede da infraestrutura",
    "external_service": "Integração com serviço externo de terceiros",
    "monitoring": "Serviço de monitoramento, logging e observabilidade",
    "dns": "Serviço de resolução de nomes (DNS)",
    "vpn": "Conexão VPN entre redes",
}

_EXTERNAL_TYPES = {"user", "external_service"}

_model_singleton: Any = None


def is_available() -> bool:
    return VISION_WEIGHTS_PATH.exists()


def _get_model():
    global _model_singleton
    if _model_singleton is None:
        from ultralytics import YOLO  # import pesado — só quando esta opção é usada

        if not VISION_WEIGHTS_PATH.exists():
            raise FileNotFoundError(
                f"Modelo de visão treinado não encontrado em {VISION_WEIGHTS_PATH}. "
                "Rode training/vision/generate_dataset.py + training/vision/train.py primeiro."
            )
        logger.info("[vision_local] Carregando modelo YOLO de %s", VISION_WEIGHTS_PATH)
        _model_singleton = YOLO(str(VISION_WEIGHTS_PATH))
    return _model_singleton


def detect_components_local(image_bytes: bytes, conf: float = 0.35) -> list[dict]:
    """Detecta componentes de arquitetura na imagem usando o modelo treinado localmente.

    Retorna uma lista de dicts compatíveis com ArchitectureComponent
    (agents/state.py): name, type, description, trust_boundary, connections,
    is_external. Não infere conexões nem fluxos de dados — só componentes
    (é o que o edital do hackathon pede explicitamente para esta etapa).
    """
    from PIL import Image

    model = _get_model()
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    results = model.predict(img, conf=conf, verbose=False)[0]

    counts: dict[str, int] = {}
    components: list[dict] = []
    for box in results.boxes:
        type_name = model.names[int(box.cls[0])]
        confidence = float(box.conf[0])
        counts[type_name] = counts.get(type_name, 0) + 1
        noun = TYPE_NOUN_PT.get(type_name, type_name)
        name = f"{noun} #{counts[type_name]}" if counts[type_name] > 1 else noun

        components.append({
            "name": name,
            "type": type_name,
            "description": TYPE_DESCRIPTIONS_PT.get(type_name, type_name),
            "trust_boundary": "public_internet" if type_name in _EXTERNAL_TYPES else "private",
            "connections": [],
            "is_external": type_name in _EXTERNAL_TYPES,
        })

    logger.info("[vision_local] %d componentes detectados", len(components))
    for c in components:
        logger.info("[vision_local]   %s (%s)", c["name"], c["type"])

    return components

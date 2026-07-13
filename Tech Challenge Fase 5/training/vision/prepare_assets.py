"""Organiza ícones oficiais (AWS/Azure/GCP) baixados pelo usuário nas pastas
training/vision/assets/icons/<classe>/ usadas por shapes.render_icon().

Não baixa nada da internet — o usuário baixa os pacotes oficiais manualmente
(links abaixo) e aponta este script para a pasta extraída. Ele varre
recursivamente por nome de arquivo usando um mapa de palavras-chave por
classe (AWS e Azure têm convenções de nome diferentes, cobrimos as duas).

Pacotes oficiais (gratuitos para uso em diagramas de arquitetura):
- AWS:   https://aws.amazon.com/architecture/icons/
- Azure: https://learn.microsoft.com/en-us/azure/architecture/icons/
- GCP:   https://cloud.google.com/icons (opcional — o PDF do hackathon só usa AWS/Azure)

Uso:
    cd training/vision
    python prepare_assets.py --source "C:/caminho/para/Asset-Package_04302021"
    python prepare_assets.py --source "C:/caminho/para/Azure_Public_Service_Icons"

Rode uma vez por pacote baixado (AWS, depois Azure) — os ícones se acumulam
nas mesmas pastas de classe. Ao final, regenere o dataset:
    python generate_dataset.py && python train.py
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import shapes

ASSETS_DIR = shapes.ASSETS_DIR

# Palavras-chave (case-insensitive, casam com substring do nome do arquivo)
# usadas para identificar o ícone certo dentro dos pacotes oficiais AWS/Azure.
# Uma classe pode combinar com ícones de serviços diferentes (ex.: "database"
# casa com RDS da AWS e com SQL Database do Azure) — isso é bom, dá variedade.
KEYWORD_MAP: dict[str, list[str]] = {
    "user": ["user", "person", "client", "users"],
    "web_server": ["ec2", "app-service", "app_service", "webapp", "web-app", "virtual-machine"],
    "api_gateway": ["api-gateway", "apigateway", "api-management", "api_management"],
    "load_balancer": ["load-balancer", "load_balancer", "elastic-load-balancing", "alb"],
    "application_server": ["ec2", "elastic-beanstalk", "app-service", "app_service"],
    "database": ["rds", "dynamodb", "sql-database", "sql_database", "cosmos-db", "database"],
    "cache": ["elasticache", "redis", "cache"],
    "message_queue": ["sqs", "simple-queue-service", "service-bus", "service_bus", "queue"],
    "authentication_service": ["cognito", "iam", "active-directory", "azure-ad", "entra"],
    "cdn": ["cloudfront", "cdn", "content-delivery"],
    "firewall": ["waf", "shield", "firewall", "network-security-group", "-nsg"],
    "storage": ["s3", "simple-storage-service", "blob-storage", "blob_storage", "storage-account"],
    "microservice": ["ecs", "eks", "kubernetes-service", "container-service"],
    "container": ["fargate", "container-registry", "container-instances", "ecr"],
    "function": ["lambda", "functions", "azure-functions"],
    "network": ["vpc", "virtual-network", "virtual-private-cloud", "vnet"],
    "external_service": ["saas", "third-party", "marketplace"],
    "monitoring": ["cloudwatch", "monitor", "azure-monitor", "x-ray"],
    "dns": ["route-53", "route53", "dns"],
    "vpn": ["vpn", "virtual-private-network"],
}

RASTER_EXTS = {".png", ".jpg", ".jpeg"}


def _convert_svg(svg_path: Path, out_path: Path, size: int = 256) -> bool:
    try:
        import cairosvg  # import lazy — opcional (pip install cairosvg)
    except ImportError:
        return False
    cairosvg.svg2png(url=str(svg_path), write_to=str(out_path), output_width=size, output_height=size)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="Pasta onde o pacote de ícones foi extraído")
    parser.add_argument("--max-per-class", type=int, default=6)
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_dir():
        raise SystemExit(f"Pasta não encontrada: {source}")

    all_files = [p for p in source.rglob("*") if p.suffix.lower() in RASTER_EXTS | {".svg"}]
    print(f"{len(all_files)} arquivos de ícone encontrados em {source}")

    report: dict[str, int] = {}
    for class_name in shapes.CLASSES:
        keywords = KEYWORD_MAP.get(class_name, [])
        class_dir = ASSETS_DIR / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        existing = len(list(class_dir.glob("*.png")))

        matches = [f for f in all_files if any(kw in f.stem.lower() for kw in keywords)]
        added = 0
        for f in matches:
            if existing + added >= args.max_per_class:
                break
            out_path = class_dir / f"{source.name}_{f.stem}.png"
            if out_path.exists():
                continue
            if f.suffix.lower() == ".svg":
                if not _convert_svg(f, out_path):
                    continue  # sem cairosvg instalado — pula SVGs, mantém só rasters
            else:
                shutil.copy(f, out_path)
            added += 1

        report[class_name] = existing + added

    print("\nÍcones por classe (training/vision/assets/icons/<classe>/):")
    for class_name, n in report.items():
        flag = "  <-- sem ícone, vai cair no desenho procedural" if n == 0 else ""
        print(f"  {class_name:<24} {n}{flag}")


if __name__ == "__main__":
    main()

"""Instâncias de arquitetura sintéticas usadas para montar os exemplos de
fine-tuning STRIDE.

Cada template é uma lista de *tipos* de componente (compatível com o
ComponentType do backend) que forma um sistema coerente e realista. Cada
template é instanciado para vários sistemas fictícios com nomes em português
("domínios"), de forma que o mesmo padrão estrutural gere exemplos de treino
com variação lexical.
"""

TYPE_DESCRIPTIONS = {
    "user": "Usuário final que interage com o sistema",
    "web_browser": "Navegador web usado pelo cliente para acessar a aplicação",
    "mobile_app": "Aplicativo móvel nativo usado pelo cliente",
    "api_gateway": "Gateway de API que roteia e gerencia as requisições",
    "web_server": "Servidor web que serve o conteúdo HTTP/HTTPS",
    "microservice": "Microsserviço da arquitetura distribuída",
    "database": "Banco de dados relacional ou NoSQL",
    "cache": "Camada de cache em memória",
    "message_queue": "Fila de mensagens para comunicação assíncrona",
    "storage": "Serviço de armazenamento de arquivos/objetos",
    "cdn": "Rede de distribuição de conteúdo (CDN)",
    "firewall": "Firewall de rede ou WAF filtrando tráfego",
    "auth_service": "Serviço de autenticação e autorização",
    "external_api": "Integração com API ou serviço de terceiros",
    "monitoring": "Serviço de monitoramento, logging e observabilidade",
    "cloud_service": "Serviço gerenciado de nuvem",
}

TYPE_NOUN = {
    "user": "Usuário",
    "web_browser": "Navegador",
    "mobile_app": "App Mobile",
    "api_gateway": "API Gateway",
    "web_server": "Servidor Web",
    "microservice": "Microsserviço",
    "database": "Banco de Dados",
    "cache": "Cache",
    "message_queue": "Fila de Mensagens",
    "storage": "Armazenamento",
    "cdn": "CDN",
    "firewall": "Firewall/WAF",
    "auth_service": "Serviço de Autenticação",
    "external_api": "API Externa",
    "monitoring": "Monitoramento",
    "cloud_service": "Serviço em Nuvem",
}

TEMPLATES = [
    {
        "types": ["user", "web_browser", "cdn", "web_server", "database", "cache"],
        "domains": ["Loja Virtual", "Portal de Notícias", "Site de Ingressos", "Blog Corporativo", "Comparador de Preços"],
    },
    {
        "types": ["user", "mobile_app", "api_gateway", "auth_service", "microservice", "database"],
        "domains": ["Banco Digital", "App de Delivery", "Carteira Digital", "App de Transporte", "Plano de Saúde"],
    },
    {
        "types": ["user", "api_gateway", "microservice", "microservice", "message_queue", "database"],
        "domains": ["Plataforma de Pagamentos", "Marketplace B2B", "Sistema de Pedidos", "Plataforma de Streaming", "Sistema de Reservas"],
    },
    {
        "types": ["user", "web_browser", "api_gateway", "storage", "database", "monitoring"],
        "domains": ["Sistema de Upload de Documentos", "Galeria de Fotos", "Repositório de Arquivos", "Sistema de Backup", "Portal de Contratos"],
    },
    {
        "types": ["microservice", "external_api", "message_queue", "database", "monitoring"],
        "domains": ["Integração com Parceiros de Frete", "Hub de Notificações", "Integração de Pagamentos Externos", "Sincronização com ERP", "Gateway de SMS"],
    },
    {
        "types": ["user", "web_server", "auth_service", "database", "cache", "monitoring"],
        "domains": ["Painel Administrativo", "Portal do Colaborador", "Sistema de RH", "CRM Interno", "Dashboard Financeiro"],
    },
    {
        "types": ["user", "web_browser", "cdn", "api_gateway", "cloud_service", "database", "firewall"],
        "domains": ["Plataforma SaaS Multi-tenant", "ERP em Nuvem", "Plataforma de E-learning", "Sistema de Gestão Hospitalar", "Plataforma de Assinaturas"],
    },
    {
        "types": ["microservice", "message_queue", "external_api", "monitoring"],
        "domains": ["Sistema de Notificações Push", "Motor de Recomendação", "Serviço de Faturamento Automático", "Pipeline de Processamento de Pedidos"],
    },
]


def build_instances() -> list[dict]:
    """Expande os templates em instâncias concretas de arquitetura com listas de componentes."""
    instances = []
    for template in TEMPLATES:
        types = template["types"]
        for domain in template["domains"]:
            components = []
            type_counts: dict[str, int] = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1
                idx = type_counts[t]
                suffix = f" {idx}" if idx > 1 else ""
                name = f"{TYPE_NOUN[t]} do {domain}{suffix}" if t != "user" else f"Usuário do {domain}"
                components.append({
                    "id": f"comp_{len(components) + 1}",
                    "name": name,
                    "type": t,
                    "description": TYPE_DESCRIPTIONS[t],
                })
            instances.append({"domain": domain, "components": components})
    return instances

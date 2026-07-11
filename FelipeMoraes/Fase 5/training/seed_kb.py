"""Base de conhecimento semente com ameaças STRIDE grounded, uma entrada por
(component_type, categoria STRIDE), usando exatamente o vocabulário do
ComponentType de backend/models/schemas.py e as chaves de categoria do StrideReport.

É uma ground truth curada manualmente (traduzida/condensada de utils/knowledge.py
mais alguns tipos de componente novos que não existiam lá) usada para montar os
exemplos de treino sintéticos do fine-tuning. Os campos de texto são mantidos
curtos (<80 chars) para respeitar o contrato do SYSTEM_PROMPT de
backend/services/stride.py.
"""

CATEGORIES = [
    "spoofing", "tampering", "repudiation",
    "information_disclosure", "denial_of_service", "elevation_of_privilege",
]

# component_type -> lista de {category, threat, risk_level, countermeasure, cwe_reference}
SEED_THREATS: dict[str, list[dict]] = {
    "user": [
        {"category": "spoofing", "threat": "Atacante se passa por usuário legítimo para acessar o sistema",
         "risk_level": "high", "countermeasure": "Exigir MFA e políticas de senha forte", "cwe_reference": "CWE-287"},
        {"category": "repudiation", "threat": "Usuário nega ter realizado uma ação sensível no sistema",
         "risk_level": "medium", "countermeasure": "Registrar trilha de auditoria à prova de adulteração", "cwe_reference": "CWE-778"},
        {"category": "information_disclosure", "threat": "Token de sessão do usuário é exposto e reutilizado",
         "risk_level": "high", "countermeasure": "Usar cookies httpOnly seguros e rotação de token", "cwe_reference": "CWE-311"},
    ],
    "web_browser": [
        {"category": "tampering", "threat": "Extensão maliciosa ou XSS altera dados exibidos no navegador",
         "risk_level": "high", "countermeasure": "Aplicar Content Security Policy estrita", "cwe_reference": "CWE-79"},
        {"category": "information_disclosure", "threat": "Dados sensíveis ficam expostos em cache ou storage local",
         "risk_level": "medium", "countermeasure": "Evitar persistir dados sensíveis no cliente", "cwe_reference": "CWE-311"},
        {"category": "spoofing", "threat": "Site falso imita a interface para roubar credenciais (phishing)",
         "risk_level": "high", "countermeasure": "Usar WebAuthn/FIDO2 resistente a phishing", "cwe_reference": "CWE-287"},
    ],
    "mobile_app": [
        {"category": "tampering", "threat": "App decompilado e republicado com código malicioso injetado",
         "risk_level": "high", "countermeasure": "Assinar o binário e validar integridade em runtime", "cwe_reference": "CWE-345"},
        {"category": "information_disclosure", "threat": "Credenciais ou chaves de API hardcoded no binário do app",
         "risk_level": "high", "countermeasure": "Nunca embutir segredos no app, usar backend proxy", "cwe_reference": "CWE-798"},
        {"category": "elevation_of_privilege", "threat": "App explora permissão excessiva do sistema operacional",
         "risk_level": "medium", "countermeasure": "Solicitar apenas permissões mínimas necessárias", "cwe_reference": "CWE-269"},
    ],
    "api_gateway": [
        {"category": "spoofing", "threat": "Atacante forja tokens ou API keys para acessar endpoints protegidos",
         "risk_level": "critical", "countermeasure": "Validar assinatura JWT e usar tokens de curta duração", "cwe_reference": "CWE-347"},
        {"category": "tampering", "threat": "Requisições da API são interceptadas e modificadas em trânsito",
         "risk_level": "high", "countermeasure": "Impor TLS 1.2+ e assinatura de requisições (HMAC)", "cwe_reference": "CWE-319"},
        {"category": "denial_of_service", "threat": "Gateway sobrecarregado por excesso de requisições (flooding)",
         "risk_level": "high", "countermeasure": "Aplicar rate limiting e cotas por chave de API", "cwe_reference": "CWE-770"},
        {"category": "elevation_of_privilege", "threat": "Falha de autorização (IDOR/BOLA) expõe recursos de outros usuários",
         "risk_level": "critical", "countermeasure": "Validar autorização a nível de objeto em cada request", "cwe_reference": "CWE-639"},
    ],
    "web_server": [
        {"category": "tampering", "threat": "Injeção de conteúdo malicioso via XSS nas respostas HTTP",
         "risk_level": "high", "countermeasure": "Codificar saída e aplicar cabeçalhos de segurança", "cwe_reference": "CWE-79"},
        {"category": "denial_of_service", "threat": "Servidor web fica indisponível por ataque DDoS volumétrico",
         "risk_level": "high", "countermeasure": "Usar WAF e proteção anti-DDoS com rate limiting", "cwe_reference": "CWE-400"},
        {"category": "information_disclosure", "threat": "Stack traces e arquivos de configuração expostos em erros",
         "risk_level": "medium", "countermeasure": "Desativar listagem de diretórios e usar páginas de erro genéricas", "cwe_reference": "CWE-200"},
        {"category": "elevation_of_privilege", "threat": "Vulnerabilidade não corrigida permite RCE e privilégios elevados",
         "risk_level": "critical", "countermeasure": "Manter patches em dia e isolar em containers", "cwe_reference": "CWE-269"},
    ],
    "microservice": [
        {"category": "spoofing", "threat": "Atacante se passa por serviço interno confiável na malha",
         "risk_level": "high", "countermeasure": "Usar mTLS entre serviços e identidade via service mesh", "cwe_reference": "CWE-287"},
        {"category": "tampering", "threat": "Serviço comprometido injeta respostas adulteradas na cadeia",
         "risk_level": "high", "countermeasure": "Assinar imagens de container e aplicar políticas de rede", "cwe_reference": "CWE-829"},
        {"category": "denial_of_service", "threat": "Falhas em cascata por ausência de circuit breakers",
         "risk_level": "medium", "countermeasure": "Implementar circuit breaker e timeouts entre chamadas", "cwe_reference": "CWE-400"},
    ],
    "database": [
        {"category": "tampering", "threat": "Injeção SQL permite modificar ou apagar dados diretamente",
         "risk_level": "critical", "countermeasure": "Usar consultas parametrizadas e ORM com binding", "cwe_reference": "CWE-89"},
        {"category": "information_disclosure", "threat": "Vazamento de dados sensíveis (PII, credenciais) do banco",
         "risk_level": "critical", "countermeasure": "Criptografar em repouso e restringir acesso por IAM", "cwe_reference": "CWE-312"},
        {"category": "denial_of_service", "threat": "Banco indisponível por esgotamento de conexões ou ransomware",
         "risk_level": "high", "countermeasure": "Limitar pool de conexões e manter backups testados", "cwe_reference": "CWE-400"},
        {"category": "elevation_of_privilege", "threat": "Usuário do banco escala privilégios via stored procedure",
         "risk_level": "high", "countermeasure": "Aplicar privilégio mínimo e auditar procedures", "cwe_reference": "CWE-269"},
        {"category": "repudiation", "threat": "Alterações no banco ocorrem sem trilha de auditoria",
         "risk_level": "medium", "countermeasure": "Habilitar auditoria e change data capture", "cwe_reference": "CWE-778"},
    ],
    "cache": [
        {"category": "tampering", "threat": "Cache poisoning injeta dados maliciosos servidos a usuários",
         "risk_level": "high", "countermeasure": "Validar chaves de cache e evitar poluição por input", "cwe_reference": "CWE-349"},
        {"category": "information_disclosure", "threat": "Dados sensíveis ficam em cache sem autenticação",
         "risk_level": "high", "countermeasure": "Habilitar autenticação no cache e isolar rede", "cwe_reference": "CWE-312"},
        {"category": "denial_of_service", "threat": "Cache stampede sobrecarrega o backend na expiração simultânea",
         "risk_level": "medium", "countermeasure": "Usar lock de cache e TTL escalonado", "cwe_reference": "CWE-400"},
    ],
    "message_queue": [
        {"category": "tampering", "threat": "Mensagens maliciosas injetadas manipulam processamento downstream",
         "risk_level": "high", "countermeasure": "Assinar mensagens e validar esquema no consumo", "cwe_reference": "CWE-20"},
        {"category": "repudiation", "threat": "Remetente nega ter publicado uma mensagem na fila",
         "risk_level": "medium", "countermeasure": "Assinar mensagens e manter recibos de entrega", "cwe_reference": "CWE-778"},
        {"category": "denial_of_service", "threat": "Fila inundada por mensagens poison-pill derruba consumidores",
         "risk_level": "high", "countermeasure": "Usar dead-letter queue e limites de taxa", "cwe_reference": "CWE-400"},
        {"category": "information_disclosure", "threat": "Payload das mensagens trafega sem criptografia",
         "risk_level": "high", "countermeasure": "Criptografar payload e restringir acesso via IAM", "cwe_reference": "CWE-311"},
    ],
    "storage": [
        {"category": "information_disclosure", "threat": "Bucket de armazenamento público expõe arquivos sensíveis",
         "risk_level": "critical", "countermeasure": "Bloquear acesso público e habilitar criptografia", "cwe_reference": "CWE-312"},
        {"category": "tampering", "threat": "Atacante sobrescreve ou apaga arquivos críticos no storage",
         "risk_level": "high", "countermeasure": "Habilitar versionamento e MFA delete", "cwe_reference": "CWE-732"},
        {"category": "denial_of_service", "threat": "Storage indisponível por exclusão acidental ou ransomware",
         "risk_level": "high", "countermeasure": "Manter versionamento e réplica cross-region", "cwe_reference": "CWE-400"},
    ],
    "cdn": [
        {"category": "tampering", "threat": "Cache poisoning na CDN serve conteúdo malicioso globalmente",
         "risk_level": "high", "countermeasure": "Configurar chaves de cache estritas e cabeçalho Vary", "cwe_reference": "CWE-349"},
        {"category": "denial_of_service", "threat": "Origem fica sobrecarregada quando a CDN é contornada",
         "risk_level": "medium", "countermeasure": "Restringir origem apenas aos IPs da CDN", "cwe_reference": "CWE-400"},
    ],
    "firewall": [
        {"category": "tampering", "threat": "Regras de firewall mal configuradas liberam tráfego indevido",
         "risk_level": "critical", "countermeasure": "Gerenciar regras via IaC e auditar periodicamente", "cwe_reference": "CWE-183"},
        {"category": "elevation_of_privilege", "threat": "Atacante contorna o WAF usando técnicas de encoding",
         "risk_level": "high", "countermeasure": "Usar regras gerenciadas de WAF e normalizar entrada", "cwe_reference": "CWE-20"},
    ],
    "auth_service": [
        {"category": "spoofing", "threat": "Atacante contorna autenticação via falha em OAuth/SAML",
         "risk_level": "critical", "countermeasure": "Usar PKCE e validar todas as assinaturas SAML/JWT", "cwe_reference": "CWE-287"},
        {"category": "elevation_of_privilege", "threat": "Escalonamento de privilégio por manipulação de escopo/role",
         "risk_level": "critical", "countermeasure": "Validar escopos no servidor a cada requisição", "cwe_reference": "CWE-269"},
        {"category": "denial_of_service", "threat": "Serviço de autenticação indisponível por credential stuffing",
         "risk_level": "high", "countermeasure": "Aplicar bloqueio de conta e CAPTCHA", "cwe_reference": "CWE-307"},
        {"category": "information_disclosure", "threat": "Credenciais ou tokens expostos em logs ou mensagens de erro",
         "risk_level": "high", "countermeasure": "Nunca logar credenciais e mascarar dados sensíveis", "cwe_reference": "CWE-532"},
    ],
    "external_api": [
        {"category": "tampering", "threat": "Serviço terceiro comprometido retorna dados maliciosos",
         "risk_level": "high", "countermeasure": "Validar respostas externas com schema", "cwe_reference": "CWE-20"},
        {"category": "information_disclosure", "threat": "Dados sensíveis enviados ao serviço externo ficam expostos",
         "risk_level": "high", "countermeasure": "Minimizar dados enviados e usar tokenização", "cwe_reference": "CWE-200"},
        {"category": "denial_of_service", "threat": "Aplicação fica indisponível por falha da dependência externa",
         "risk_level": "medium", "countermeasure": "Implementar fallback e circuit breaker", "cwe_reference": "CWE-400"},
    ],
    "monitoring": [
        {"category": "repudiation", "threat": "Atacante apaga ou altera logs para encobrir rastros",
         "risk_level": "high", "countermeasure": "Enviar logs a armazenamento imutável (WORM)", "cwe_reference": "CWE-778"},
        {"category": "information_disclosure", "threat": "Dados de monitoramento expõem PII ou segredos",
         "risk_level": "medium", "countermeasure": "Mascarar campos sensíveis e aplicar RBAC", "cwe_reference": "CWE-532"},
    ],
    "cloud_service": [
        {"category": "tampering", "threat": "Configuração incorreta do serviço gerenciado permite alteração indevida",
         "risk_level": "high", "countermeasure": "Gerenciar configuração via IaC com controle de mudança", "cwe_reference": "CWE-183"},
        {"category": "information_disclosure", "threat": "Serviço de nuvem mal configurado expõe dados publicamente",
         "risk_level": "critical", "countermeasure": "Revisar políticas de acesso e habilitar criptografia", "cwe_reference": "CWE-312"},
        {"category": "denial_of_service", "threat": "Cota do serviço gerenciado é excedida, causando indisponibilidade",
         "risk_level": "medium", "countermeasure": "Monitorar cotas e configurar auto-scaling", "cwe_reference": "CWE-400"},
    ],
}

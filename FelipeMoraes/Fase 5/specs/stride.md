# Spec: Metodologia STRIDE

## O que é STRIDE

STRIDE é uma metodologia de modelagem de ameaças criada pela Microsoft para classificar sistematicamente ameaças de segurança em sistemas de software. Cada letra representa uma categoria de ameaça:

## Categorias

### S — Spoofing (Falsificação de Identidade)
**Propriedade violada:** Autenticidade

O atacante se passa por outro usuário, sistema ou componente legítimo.

**Componentes mais afetados:** usuários, APIs, serviços de autenticação, clientes externos

**Exemplos de ameaças:**
- Roubo de credenciais / tokens de sessão
- Falsificação de IP (IP spoofing)
- Phishing para obter credenciais
- Replay attacks com tokens válidos
- Falsificação de certificados

**Contramedidas típicas:**
- Autenticação multifator (MFA)
- Tokens JWT com validade curta
- Certificados TLS mútuos (mTLS)
- Validação de origin/referer
- Rate limiting em endpoints de login

---

### T — Tampering (Adulteração de Dados)
**Propriedade violada:** Integridade

O atacante modifica dados em trânsito ou em repouso sem autorização.

**Componentes mais afetados:** bancos de dados, filas de mensagem, armazenamento, APIs

**Exemplos de ameaças:**
- SQL Injection para alterar registros
- Man-in-the-Middle para modificar requests
- Adulteração de arquivos de configuração
- Injeção de código malicioso em payloads
- Modificação de parâmetros HTTP (tampering de formulário)

**Contramedidas típicas:**
- TLS em toda comunicação
- Assinatura de mensagens com HMAC
- Validação de input (servidor, nunca só cliente)
- Checksums e hashes de integridade
- Controle de acesso granular a banco de dados

---

### R — Repudiation (Repúdio)
**Propriedade violada:** Não-repúdio

O usuário nega ter executado uma ação, e não há evidência para provar o contrário.

**Componentes mais afetados:** sistemas de pagamento, logs, auditoria, serviços críticos

**Exemplos de ameaças:**
- Ausência de logs de auditoria
- Logs manipuláveis pelo próprio usuário
- Falta de assinatura digital em transações
- Ausência de timestamps confiáveis
- Não rastreabilidade de ações administrativas

**Contramedidas típicas:**
- Logs imutáveis (append-only) centralizados
- Assinatura digital de transações críticas
- Timestamps de servidor (não cliente)
- Trilha de auditoria com hash encadeado
- SIEM para correlação de eventos

---

### I — Information Disclosure (Divulgação de Informação)
**Propriedade violada:** Confidencialidade

Dados sensíveis são expostos a partes não autorizadas.

**Componentes mais afetados:** bancos de dados, APIs, storage, logs, CDN

**Exemplos de ameaças:**
- Stack traces expostos em respostas de erro
- Dados sensíveis em logs (senhas, tokens, PII)
- Acessos não autorizados a endpoints privados
- Armazenamento sem criptografia
- Secrets em variáveis de ambiente expostas
- Listagem de diretórios em servidores web

**Contramedidas típicas:**
- Criptografia em repouso (AES-256)
- Sanitização de mensagens de erro (sem stack trace em produção)
- Mascaramento de dados sensíveis em logs
- Controle de acesso baseado em roles (RBAC)
- Secrets management (Vault, AWS Secrets Manager)

---

### D — Denial of Service (Negação de Serviço)
**Propriedade violada:** Disponibilidade

O atacante impede usuários legítimos de acessar o sistema.

**Componentes mais afetados:** APIs, load balancers, servidores, bancos de dados, filas

**Exemplos de ameaças:**
- Flood de requisições (HTTP flood)
- Exaustão de conexões de banco de dados
- Ataques de amplificação (UDP/DNS)
- Slowloris (conexões lentas e longas)
- Consumo de CPU via operações pesadas (zip bombs, regex evil)
- Starvation de recursos em filas de mensagem

**Contramedidas típicas:**
- Rate limiting e throttling por IP/usuário
- WAF (Web Application Firewall)
- Auto-scaling horizontal
- Circuit breaker pattern
- Timeouts em todas as operações externas
- CDN com proteção DDoS

---

### E — Elevation of Privilege (Elevação de Privilégio)
**Propriedade violada:** Autorização

O atacante obtém permissões além do que foi concedido.

**Componentes mais afetados:** serviços de autenticação, APIs, bancos de dados, microserviços

**Exemplos de ameaças:**
- Exploração de vulnerabilidades para acesso root
- IDOR (Insecure Direct Object Reference)
- JWT com role manipulável no payload
- Escalada de privilégio via injeção de comandos
- Bypass de autorização por falta de validação server-side
- Acesso a endpoints administrativos sem autenticação

**Contramedidas típicas:**
- Princípio do menor privilégio (PoLP)
- Autorização server-side em todo endpoint
- Validação de ACL / RBAC / ABAC
- JWT com claims validados no servidor
- Auditoria de acessos administrativos

---

## Aplicação por Tipo de Componente

| Componente | S | T | R | I | D | E |
|-----------|---|---|---|---|---|---|
| user | ● | · | ● | ● | · | · |
| api_gateway | ● | ● | ● | ● | ● | ● |
| web_server | ● | ● | ● | ● | ● | ● |
| database | · | ● | ● | ● | ● | ● |
| auth_service | ● | ● | ● | ● | ● | ● |
| message_queue | · | ● | ● | ● | ● | · |
| storage | · | ● | ● | ● | ● | · |
| external_api | ● | ● | · | ● | ● | · |
| firewall | · | · | · | · | ● | · |
| monitoring | · | ● | ● | ● | ● | · |

● = ameaça frequente · = menos aplicável

---

## Risk Levels

| Nível | Critério |
|-------|---------|
| **critical** | Exploração trivial, impacto total no sistema ou dados |
| **high** | Exploração viável, impacto significativo |
| **medium** | Exploração requer condições específicas, impacto moderado |
| **low** | Exploração improvável ou impacto limitado |

---

## Prompt Engineering para STRIDE

O prompt STRIDE deve:
1. Fornecer o nome, tipo e descrição de cada componente
2. Pedir ameaças específicas (não genéricas) para aquele contexto
3. Solicitar contramedidas acionáveis e concretas
4. Especificar o formato JSON exato esperado
5. Indicar o idioma da resposta (português para o relatório final)

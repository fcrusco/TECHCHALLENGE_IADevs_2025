---
name: analyze
description: Testa a análise STRIDE com uma imagem de diagrama de arquitetura
---

# Skill: Testar Análise de Imagem

Ao executar esta skill, siga os passos abaixo para verificar se o pipeline completo funciona.

## Pré-condição

O backend deve estar rodando em `http://localhost:8000`.
Se não estiver, execute `/dev` primeiro.

## 1. Testar health do backend

```bash
curl http://localhost:8000/api/health
```

Resultado esperado:
```json
{"status": "ok", "provider": "openai", "model": "gpt-4o"}
```

Se falhar, o backend não está rodando. Pare e informe o usuário.

## 2. Verificar providers disponíveis

```bash
curl http://localhost:8000/api/providers
```

Liste os providers retornados e seus status `available`.

## 3. Testar análise com imagem de exemplo

Se o usuário fornecer uma imagem, use-a. Caso contrário, informe que é necessária uma imagem de diagrama de arquitetura para testar.

Com uma imagem disponível (ex: `test_arch.png`):

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@test_arch.png" \
  -F "provider=openai"
```

## 4. Validar a resposta

Verifique na resposta JSON:

- `components`: lista com ao menos 1 componente com campos `id`, `name`, `type`, `description`
- `stride_report`: objeto com as 6 chaves STRIDE, cada uma com lista de ameaças
- `summary`: string não-vazia em português
- `provider_used`: corresponde ao provider enviado
- `model_used`: nome do modelo usado

## 5. Diagnóstico de problemas comuns

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| `422 Unprocessable Entity` | Arquivo não é imagem válida | Usar PNG/JPG/JPEG/WEBP |
| `500 Failed to parse LLM response` | LLM retornou JSON malformado | Verificar logs do backend |
| `503 Provider not available` | Ollama/LM Studio offline | Iniciar o provider local |
| `401 Unauthorized` | API key OpenAI inválida/ausente | Verificar `.env` |
| `components: []` | Imagem sem texto/ícones reconhecíveis | Usar diagrama mais claro |
| STRIDE categories vazias | Componentes muito genéricos | Componentes foram detectados? Verificar step anterior |

## 6. Resultado esperado (exemplo simplificado)

```json
{
  "components": [
    {
      "id": "comp_1",
      "name": "API Gateway",
      "type": "api_gateway",
      "description": "Ponto de entrada para todas as requisições"
    }
  ],
  "stride_report": {
    "spoofing": [
      {
        "component_id": "comp_1",
        "component_name": "API Gateway",
        "threat": "Falsificação de identidade do cliente via token roubado",
        "risk_level": "high",
        "countermeasures": ["Implementar OAuth 2.0 com refresh tokens de curta duração", "Validar JWT signature em cada requisição"]
      }
    ],
    "tampering": [...],
    "repudiation": [...],
    "information_disclosure": [...],
    "denial_of_service": [...],
    "elevation_of_privilege": [...]
  },
  "summary": "A análise identificou N componentes na arquitetura...",
  "provider_used": "openai",
  "model_used": "gpt-4o"
}
```

Se tudo estiver correto, o pipeline está funcionando. Informe o usuário que pode usar o frontend em http://localhost:3000.

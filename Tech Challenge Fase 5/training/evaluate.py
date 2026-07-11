"""Verificação qualitativa rápida do adapter STRIDE treinado.

Carrega o modelo base + adapter LoRA e roda sobre exemplos de arquitetura
que NÃO estavam no conjunto de treino, usando exatamente o mesmo formato
de system prompt/entrada de backend/services/stride.py. Imprime a saída
bruta e valida contra o schema JSON esperado.

Uso:
    python evaluate.py
"""

import json
import os

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_DIR = "output/stride-qwen2.5-3b-lora"

SYSTEM_PROMPT = """Você é um especialista em cibersegurança. Realize a análise de ameaças STRIDE sobre os componentes fornecidos.

Retorne APENAS um objeto JSON válido com estas chaves exatas:
spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege

Cada valor é um array de:
{"component_id":"comp_1","component_name":"Name","threat":"descrição curta em português do Brasil","risk_level":"low|medium|high|critical","countermeasures":["uma contramedida em português do Brasil"]}

Regras:
- No máximo 1 ameaça por componente por categoria STRIDE
- No máximo 30 ameaças no total, somando todas as categorias
- Apenas 1 contramedida por ameaça
- Mantenha os textos de ameaça e contramedida curtos (menos de 80 caracteres cada)
- Retorne APENAS o objeto JSON, sem markdown, sem explicação"""

CATEGORIES = [
    "spoofing", "tampering", "repudiation",
    "information_disclosure", "denial_of_service", "elevation_of_privilege",
]

# Arquiteturas de teste separadas — tipos/combinações NÃO vistos juntos durante o treino
TEST_CASES = [
    "Componentes da arquitetura para analisar:\n"
    "- id:comp_1 name:App de Investimentos type:mobile_app desc:Aplicativo móvel usado pelo cliente\n"
    "- id:comp_2 name:Gateway de Ordens type:api_gateway desc:Gateway de API que roteia e gerencia as requisições\n"
    "- id:comp_3 name:Serviço de Cotações type:microservice desc:Microsserviço da arquitetura distribuída\n"
    "- id:comp_4 name:Banco de Posições type:database desc:Banco de dados relacional ou NoSQL\n"
    "- id:comp_5 name:Autenticador Corporativo type:auth_service desc:Serviço de autenticação e autorização",

    "Componentes da arquitetura para analisar:\n"
    "- id:comp_1 name:Totem de Autoatendimento type:web_browser desc:Navegador web usado pelo cliente para acessar a aplicação\n"
    "- id:comp_2 name:CDN de Cardápio type:cdn desc:Rede de distribuição de conteúdo (CDN)\n"
    "- id:comp_3 name:Firewall de Loja type:firewall desc:Firewall de rede ou WAF filtrando tráfego\n"
    "- id:comp_4 name:Integração com Delivery type:external_api desc:Integração com API ou serviço de terceiros\n"
    "- id:comp_5 name:Fila de Pedidos type:message_queue desc:Fila de mensagens para comunicação assíncrona",
]


def main() -> None:
    print(f"Carregando base {BASE_MODEL} + adapter {ADAPTER_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, dtype=torch.bfloat16, device_map="cuda")
    model = PeftModel.from_pretrained(base, ADAPTER_DIR)
    model.eval()

    for i, user_msg in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 70}\nCASO {i}\n{'=' * 70}")
        print(user_msg)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_msg}]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=1500, do_sample=False, temperature=None, top_p=None,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        print("\n--- SAÍDA DO MODELO ---")
        print(text)

        print("\n--- VALIDAÇÃO ---")
        try:
            data = json.loads(text.strip())
            missing = [c for c in CATEGORIES if c not in data]
            total = sum(len(v) for v in data.values() if isinstance(v, list))
            print(f"JSON válido | categorias ausentes: {missing or 'nenhuma'} | total de ameaças: {total}")
        except json.JSONDecodeError as e:
            print(f"JSON INVÁLIDO: {e}")


if __name__ == "__main__":
    main()

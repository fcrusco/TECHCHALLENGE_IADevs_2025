"""
Pipeline principal do Assistente Medico.

Este modulo e o coracao do projeto. Ele orquestra todas as pecas:
  1. Carregamento do LLM (modelo fine-tunado ou Ollama como fallback)
  2. Busca semantica RAG via FAISS (retriever)
  3. Geracao de resposta com contexto medico (LangChain LCEL)
  4. Guardrails de seguranca na entrada e na saida
  5. Explainability: associa fontes MedQuAD a cada resposta
  6. Auditoria: registra toda interacao em JSONL

Ordem de prioridade para o LLM:
  1. Modelo fine-tunado localmente (LLaMA 3.2 + adaptadores LoRA, gerado no Kaggle)
     Localizado em: outputs/llama-medical/
  2. Fallback: Ollama rodando localmente (llama3.2:1b)
     Usado quando USE_OLLAMA_FALLBACK=true no .env ou quando o modelo nao e encontrado

O pipeline usa o padrao LCEL (LangChain Expression Language), que e a forma
atual recomendada pelo LangChain para construir chains. Substituiu o
ConversationalRetrievalChain que foi descontinuado nas versoes recentes.

A chain LCEL funciona assim:
  pergunta do usuario
    -> retriever busca documentos relevantes no FAISS
    -> documentos + pergunta sao inseridos no prompt
    -> LLM gera a resposta
    -> StrOutputParser extrai o texto da resposta
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.assistant.retriever import MedicalRetriever
from src.assistant.memory import build_memory
from src.security.guardrails import Guardrails
from src.security.logger import AuditLogger
from src.security.explainability import ExplainabilityModule
from src.utils.config import Config


# Prompt que instrui o LLM a responder em portugues com base no contexto recuperado.
# O contexto e preenchido automaticamente pelo retriever RAG.
# A instrucao de responder em portugues e importante porque o MedQuAD e em ingles,
# mas queremos que as respostas sejam em portugues para o uso clinico.
PROMPT_TEMPLATE = PromptTemplate.from_template(
    "Voce e um assistente medico especializado. Use o contexto abaixo para responder a pergunta em portugues.\n"
    "Sempre cite as fontes utilizadas e recomende validacao humana para decisoes criticas.\n"
    "Nunca emita prescricoes diretas sem revisao medica.\n\n"
    "Contexto:\n{context}\n\n"
    "Pergunta: {question}\n\n"
    "Resposta em portugues:"
)


def _format_docs(docs) -> str:
    """
    Concatena o conteudo dos documentos recuperados pelo RAG em uma unica string.
    Essa string e inserida no campo {context} do prompt.
    """
    return "\n\n".join(d.page_content for d in docs)


def _load_finetuned_llm():
    """
    Carrega o modelo fine-tunado salvo localmente.

    O modelo foi treinado no Kaggle usando QLoRA (Quantized LoRA):
    - Modelo base: meta-llama/Llama-3.2-3B-Instruct
    - Dataset: MedQuAD (11.657 amostras de treino)
    - Tecnica: QLoRA 4-bit com adaptadores LoRA (r=16, alpha=32)
    - Plataforma: Kaggle, GPU T4

    Os adaptadores LoRA ficam salvos em outputs/llama-medical/.
    O modelo base e carregado sem conexao com o HuggingFace (local_files_only=True).
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline
    from langchain_community.llms import HuggingFacePipeline

    model_path = Config.FINETUNED_MODEL_PATH
    print(f"[pipeline] Carregando modelo fine-tunado: {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        low_cpu_mem_usage=True,
        local_files_only=True,
    )
    pipe = hf_pipeline(
        "text-generation", model=model, tokenizer=tokenizer,
        max_new_tokens=Config.pipeline["pipeline"]["max_new_tokens"],
        temperature=Config.pipeline["pipeline"]["temperature"],
        top_p=Config.pipeline["pipeline"]["top_p"],
        repetition_penalty=Config.pipeline["pipeline"]["repetition_penalty"],
        do_sample=True,
    )
    print("[pipeline] Modelo fine-tunado carregado com sucesso.")
    return HuggingFacePipeline(pipeline=pipe)


def _load_ollama_llm():
    """
    Carrega o Ollama como fallback.

    O Ollama roda o modelo llama3.2:1b localmente via API REST em localhost:11434.
    E usado quando:
    - O modelo fine-tunado nao esta disponivel
    - USE_OLLAMA_FALLBACK=true no .env
    - Para desenvolvimento e testes antes do fine-tuning

    Para usar: ollama serve + ollama pull llama3.2:1b
    """
    from langchain_ollama import OllamaLLM
    print(f"[pipeline] Usando Ollama ({Config.OLLAMA_MODEL}) como fallback.")
    return OllamaLLM(
        base_url=Config.OLLAMA_BASE_URL,
        model=Config.OLLAMA_MODEL,
        temperature=Config.pipeline["pipeline"]["temperature"],
    )


def _build_llm():
    """
    Decide qual LLM carregar baseado nas configuracoes do .env e na existencia
    do modelo fine-tunado em disco.

    Logica:
    1. Verifica se existe a pasta outputs/llama-medical/ com arquivos .safetensors
    2. Se sim, tenta carregar o modelo fine-tunado
    3. Se falhar ou nao existir, verifica USE_OLLAMA_FALLBACK
    4. Se fallback habilitado, carrega Ollama
    5. Se fallback desabilitado, lanca erro com instrucoes
    """
    model_path = Path(Config.FINETUNED_MODEL_PATH)
    model_exists = model_path.exists() and any(model_path.glob("*.safetensors"))

    if model_exists:
        try:
            return _load_finetuned_llm()
        except Exception as e:
            print(f"[pipeline] Erro ao carregar modelo fine-tunado: {e}")

    if Config.USE_OLLAMA_FALLBACK:
        return _load_ollama_llm()

    raise RuntimeError(
        "Modelo fine-tunado nao encontrado e USE_OLLAMA_FALLBACK=false.\n"
        "Execute o notebook 04_colab_finetuning.ipynb no Kaggle e baixe o modelo para outputs/llama-medical/."
    )


class MedicalAssistantPipeline:
    """
    Pipeline completo do assistente medico.

    Integra todas as camadas do sistema:
    - LLM: modelo de linguagem (fine-tunado ou Ollama)
    - RAG: recuperacao de documentos relevantes do MedQuAD via FAISS
    - Guardrails: verificacao de seguranca na entrada e saida
    - Explainability: rastreamento das fontes usadas na resposta
    - Auditoria: log de todas as interacoes em JSONL (conformidade LGPD)

    Uso:
        pipeline = MedicalAssistantPipeline(user_id="dr_silva")
        resposta = pipeline.run("Quais os tratamentos para diabetes tipo 2?")
    """

    def __init__(self, user_id: str = "system"):
        self.user_id        = user_id
        self.guardrails     = Guardrails()
        self.audit_logger   = AuditLogger()
        self.explainability = ExplainabilityModule()
        self.memory         = build_memory()
        self.retriever      = MedicalRetriever()
        self._chain         = None
        self._retriever     = None

        self._llm = _build_llm()

        try:
            self.retriever.load_or_build()
            lc_retriever = self.retriever._store.as_retriever(
                search_kwargs={"k": Config.pipeline["retriever"]["top_k"]}
            )
            # Monta a chain LCEL:
            # O dicionario com "context" e "question" alimenta o prompt template.
            # O retriever busca documentos e _format_docs os concatena em texto.
            # RunnablePassthrough passa a pergunta original sem modificacao.
            self._chain = (
                {
                    "context":  lc_retriever | _format_docs,
                    "question": RunnablePassthrough(),
                }
                | PROMPT_TEMPLATE
                | self._llm
                | StrOutputParser()
            )
            self._retriever = lc_retriever
            print("[pipeline] Pipeline pronto.")
        except FileNotFoundError:
            print("[pipeline] Vector store nao encontrado.")
            print("[pipeline] Execute: python -m src.assistant.retriever")

    def run(self, query: str, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Processa uma pergunta clinica e retorna a resposta com metadados.

        Fluxo completo:
        1. Guardrail na entrada: bloqueia perguntas fora do escopo
        2. RAG: busca documentos relevantes no MedQuAD
        3. LLM: gera resposta com base nos documentos
        4. Guardrail na saida: adiciona avisos para temas criticos
        5. Explainability: associa fontes a resposta
        6. Auditoria: registra a interacao no log

        Retorna um dicionario com:
        - answer: resposta formatada com fontes
        - sources: lista de fontes MedQuAD utilizadas
        - warnings: alertas de guardrail
        - confidence: estimativa de confianca (0 a 1)
        - interaction_id: UUID para rastreamento no log de auditoria
        """
        uid = user_id or self.user_id

        # Passo 1: guardrail na entrada
        guard = self.guardrails.check(query)
        if not guard.allowed:
            self.audit_logger.log_interaction(
                uid, query, "", [], [guard.blocked_reason], blocked=True
            )
            return {
                "answer":         f"Consulta bloqueada: {guard.blocked_reason}",
                "sources":        [],
                "warnings":       guard.warnings,
                "interaction_id": None,
                "confidence":     0.0,
            }

        if self._chain is None:
            return {
                "answer":         "Pipeline nao inicializado. Execute python -m src.assistant.retriever primeiro.",
                "sources":        [],
                "warnings":       [],
                "interaction_id": None,
                "confidence":     0.0,
            }

        # Passo 2 e 3: RAG + LLM via chain LCEL
        try:
            raw_answer  = self._chain.invoke(query)
            source_docs = self._retriever.invoke(query)
        except Exception as exc:
            self.audit_logger.log_error(uid, str(exc), {"query": query[:100]})
            return {
                "answer":         "Erro interno. Verifique se o modelo esta carregado corretamente.",
                "sources":        [],
                "warnings":       ["Erro interno"],
                "interaction_id": None,
                "confidence":     0.0,
            }

        # Passo 4: guardrail na saida
        guard_out = self.guardrails.check(query, raw_answer)
        warnings  = guard.warnings + guard_out.warnings
        final     = raw_answer + self.guardrails.safety_note(guard_out)

        # Passo 5: explainability - associa fontes a resposta
        retrieved = [
            {"page_content": d.page_content, "metadata": d.metadata, "score": 0.8}
            for d in source_docs
        ]
        explained = self.explainability.build_attribution(retrieved, raw_answer)
        sources   = [{"title": a.title, "score": a.relevance_score} for a in explained.attributions]

        # Passo 6: auditoria
        iid = self.audit_logger.log_interaction(
            uid, query, final,
            sources=[a.source_id for a in explained.attributions],
            guardrail_flags=warnings,
        )

        return {
            "answer":         explained.format_with_sources(),
            "sources":        sources,
            "warnings":       warnings,
            "interaction_id": iid,
            "confidence":     explained.confidence,
        }

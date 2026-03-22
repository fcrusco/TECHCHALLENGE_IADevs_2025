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

from langgraph.graph import StateGraph
from typing import TypedDict, List, Dict


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

class AgentState(TypedDict):
    input: str
    user_id: str

    blocked: bool
    warnings: List[str]

    raw_answer: str
    final_answer: str

    source_docs: List
    sources: List[Dict]

    confidence: float
    interaction_id: str


class MedicalAssistantPipeline:
    """ Pipeline completo do assistente medico. Integra todas as camadas do sistema: 
    - LLM: modelo de linguagem (fine-tunado ou Ollama)
    - RAG: recuperacao de documentos relevantes do MedQuAD via FAISS 
    - Guardrails: verificacao de seguranca na entrada e saida 
    - Explainability: rastreamento das fontes usadas na resposta 
    - Auditoria: log de todas as interacoes em JSONL (conformidade LGPD) 
    Uso: pipeline = MedicalAssistantPipeline(user_id="dr_silva") resposta = pipeline.run("Quais os tratamentos para diabetes tipo 2?") """

    def __init__(self, user_id: str = "system"):
        self.user_id        = user_id
        self.guardrails     = Guardrails()
        self.audit_logger   = AuditLogger()
        self.explainability = ExplainabilityModule()
        self.memory         = build_memory()
        self.retriever      = MedicalRetriever()

        self._llm = _build_llm()

        try:
            self.retriever.load_or_build()
            lc_retriever = self.retriever._store.as_retriever(
                search_kwargs={"k": Config.pipeline["retriever"]["top_k"]}
            )

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
            self.graph = self._build_graph()

            print("[pipeline] Pipeline com LangGraph pronto.")

        except FileNotFoundError:
            print("[pipeline] Vector store nao encontrado.")
            print("[pipeline] Execute: python -m src.assistant.retriever")

    # =========================
    # NODES DO LANGGRAPH
    # =========================

    def _guardrail_node(self, state: AgentState):
        guard = self.guardrails.check(state["input"])

        state["blocked"] = not guard.allowed
        state["warnings"] = guard.warnings.copy()

        if not guard.allowed:
            state["final_answer"] = f"Consulta bloqueada: {guard.blocked_reason}"
            state["confidence"] = 0.0

        return state

    def _retrieval_node(self, state: AgentState):
        if state["blocked"]:
            return state

        docs = self._retriever.invoke(state["input"])
        state["source_docs"] = docs

        return state

    def _generation_node(self, state: AgentState):
        if state["blocked"]:
            return state

        try:
            raw_answer = self._chain.invoke(state["input"])
            state["raw_answer"] = raw_answer
        except Exception as exc:
            self.audit_logger.log_error(state["user_id"], str(exc), {"query": state["input"][:100]})

            state["final_answer"] = "Erro interno. Verifique o modelo."
            state["confidence"] = 0.0
            state["blocked"] = True

        return state

    def _postprocess_node(self, state: AgentState):
        if state["blocked"]:
            return state

        # Guardrail saída
        guard_out = self.guardrails.check(state["input"], state["raw_answer"])
        state["warnings"] += guard_out.warnings

        final = state["raw_answer"] + self.guardrails.safety_note(guard_out)

        # Explainability
        retrieved = [
            {"page_content": d.page_content, "metadata": d.metadata, "score": 0.8}
            for d in state["source_docs"]
        ]

        explained = self.explainability.build_attribution(retrieved, state["raw_answer"])

        state["final_answer"] = explained.format_with_sources()
        state["sources"] = [
            {"title": a.title, "score": a.relevance_score}
            for a in explained.attributions
        ]
        state["confidence"] = explained.confidence

        return state

    def _logging_node(self, state: AgentState):
        iid = self.audit_logger.log_interaction(
            state["user_id"],
            state["input"],
            state.get("final_answer", ""),
            sources=[s["title"] for s in state.get("sources", [])],
            guardrail_flags=state.get("warnings", []),
            blocked=state.get("blocked", False)
        )

        state["interaction_id"] = iid
        return state

    # =========================
    # BUILD GRAPH
    # =========================

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("guardrail", self._guardrail_node)
        graph.add_node("retrieve", self._retrieval_node)
        graph.add_node("generate", self._generation_node)
        graph.add_node("postprocess", self._postprocess_node)
        graph.add_node("log", self._logging_node)

        graph.set_entry_point("guardrail")

        graph.add_edge("guardrail", "retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "postprocess")
        graph.add_edge("postprocess", "log")

        return graph.compile()

    # =========================
    # RUN (AGORA USA LANGGRAPH)
    # =========================

    def run(self, query: str, user_id: Optional[str] = None) -> dict[str, Any]:
        uid = user_id or self.user_id

        result = self.graph.invoke({
            "input": query,
            "user_id": uid,
            "blocked": False,
            "warnings": [],
            "context": "",
            "source_docs": [],
            "sources": [],
            "raw_answer": "",
            "final_answer": "",
            "confidence": 0.0,
            "interaction_id": "",

            "chain": self._chain,
            "retriever": self._retriever,
            "guardrails": self.guardrails,
            "logger": self.audit_logger,
            "explainability": self.explainability,
        })

        return {
            "answer": result.get("final_answer", ""),
            "sources": result.get("sources", []),
            "warnings": result.get("warnings", []),
            "interaction_id": result.get("interaction_id"),
            "confidence": result.get("confidence", 0.0),
        }
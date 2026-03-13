"""
Historico de mensagens da conversa.

Mantem o contexto das interacoes anteriores do medico com o assistente
durante a sessao atual. O historico e perdido ao encerrar o programa,
o que e intencional por questoes de privacidade (LGPD).

Para persistencia entre sessoes, seria necessario integrar com
um banco de dados (ex: Redis, PostgreSQL), o que esta fora do escopo
deste projeto academico.
"""
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


def build_memory() -> ChatMessageHistory:
    """
    Cria um novo historico de mensagens vazio para a sessao.
    
    Retorna uma instancia de ChatMessageHistory que armazena as mensagens
    em memoria RAM. Compativel com a versao atual do LangChain (LCEL).
    """
    return ChatMessageHistory()

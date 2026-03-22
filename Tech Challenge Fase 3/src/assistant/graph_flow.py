from langgraph.graph import StateGraph

class AgentState(dict):
    pass

def validate_input(state):
    question = state["input"]

    if "prescreva" in question.lower():
        state["error"] = "Solicitação não permitida -> sem validação médica."
    return state


def retrieve_context(state):
    state["context"] = "Protocolo clínico institucional relevante."
    return state


def generate_response(state):
    if "error" in state:
        state["response"] = state["error"]
        return state

    context = state.get("context", "")
    question = state["input"]

    state["response"] = f"Baseado em: {context}\nResposta: Conduta recomendada para: {question}"
    return state


def explain(state):
    state["explainability"] = "Resposta baseada em protocolo interno simulado."
    return state


def log_step(state):
    print("LOG:", state)
    return state

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("validate", validate_input)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("generate", generate_response)
    graph.add_node("explain", explain)
    graph.add_node("log", log_step)

    graph.set_entry_point("validate")

    graph.add_edge("validate", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "explain")
    graph.add_edge("explain", "log")

    return graph.compile()
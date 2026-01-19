# Roteiro do Vídeo - Sistema de Predição de Diabetes com IA

**Duração Total: 10 minutos**

---

## 🎬 INTRODUÇÃO (1 min)

**O que falar:**
- "Olá! Vou apresentar um sistema de predição de risco de diabetes que combina Machine Learning com algoritmos genéticos e LLMs para explicação."
- "O sistema usa Random Forest otimizado via algoritmo genético e integra GPT-4 para gerar explicações clínicas."

**O que mostrar:**
- Estrutura de pastas do projeto
- Arquivos principais

---

## 🔧 COMPONENTES DA SOLUÇÃO (3 min)

### 2.1 Estrutura do Projeto (30s)
- Mostrar: `data/`, `src/`, `outputs/`
- Explicar: Dataset, código fonte, modelos salvos

### 2.2 Pipeline de Treinamento (1.5 min)
**Abrir `src/treinamento.py` e explicar:**
- Carregamento e pré-processamento (substituição de zeros, normalização)
- Processamento em lotes (simulação de carga variável)
- Balanceamento com SMOTE
- Treinamento de modelos base (LR e RF)

### 2.3 Algoritmo Genético (1 min)
**Mostrar código do GA:**
- População inicial (5 indivíduos)
- Função fitness (F1-score via validação cruzada)
- Operadores: crossover e mutação
- Seleção dos melhores

---

## 🧬 RESULTADOS DO ALGORITMO GENÉTICO (2.5 min)

### 3.1 Executar Visualização (1 min)
**Executar:** `python apresentacao/visualizar_ga.py`
- Mostrar evolução das gerações
- Comparar fitness dos indivíduos
- Destacar o melhor indivíduo encontrado

### 3.2 Comparação de Modelos (1.5 min)
**Mostrar métricas:**
- Modelo base (LR): Accuracy, Recall, F1
- Modelo base (RF): Accuracy, Recall, F1
- Modelo otimizado (RF): Melhoria obtida
- Explicar ganho de performance

---

## 🤖 DEMONSTRAÇÃO DO SISTEMA (2.5 min)

### 4.1 Executar Avaliação (1.5 min)
**Executar:** `python apresentacao/demo_completa.py`
- Mostrar entrada de dados do paciente
- Exibir predições de ambos os modelos
- Mostrar probabilidades

### 4.2 Integração com LLM (1 min)
- Mostrar explicação gerada pelo GPT-4o-mini
- Destacar linguagem técnica e clínica
- Explicar como o LLM interpreta os resultados

---

## 📊 RESUMO E CONCLUSÕES (1 min)

**Pontos principais:**
- ✅ Sistema funcional end-to-end
- ✅ Otimização automática via algoritmo genético
- ✅ Explicabilidade através de LLM
- ✅ Métricas de performance melhoradas

**Próximos passos (opcional):**
- Deploy em produção
- Interface web
- Integração com sistemas hospitalares

---

## 🎯 DICAS PARA GRAVAÇÃO

1. **Prepare o ambiente:**
   - Certifique-se que os modelos estão treinados (`python src/treinamento.py`)
   - Tenha dados de exemplo prontos
   - Teste a conexão com OpenAI API (variável OPENAI_API_KEY no .env)

2. **Durante a gravação:**
   - Fale pausadamente
   - Destaque os pontos principais
   - Use zoom no terminal/código quando necessário

3. **Edição:**
   - Adicione legendas para métricas
   - Destaque trechos de código importantes
   - Use transições suaves

---

## 📁 COMANDOS ÚTEIS

```bash
# Na raiz do projeto (Fase 2)
python src/treinamento.py              # Treinar modelos (se necessário)
python apresentacao/visualizar_ga.py   # Ver resultados do GA
python apresentacao/demo_completa.py   # Demonstração com LLM
```

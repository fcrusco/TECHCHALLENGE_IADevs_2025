// Configuração da API base URL
// A URL da API é injetada pelo servidor Python via window.API_BASE_URL
// Fallback para desenvolvimento local
function getApiBaseUrl() {
    // Prioridade 1: URL injetada pelo servidor via window.API_BASE_URL
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    
    // Prioridade 2: Meta tag
    const metaApiUrl = document.querySelector('meta[name="api-base-url"]');
    if (metaApiUrl && metaApiUrl.content && metaApiUrl.content !== '{{ API_BASE_URL }}') {
        return metaApiUrl.getAttribute('content');
    }
    
    // Prioridade 3: Detecção automática para desenvolvimento local
    const currentUrl = window.location.origin;
    if (currentUrl.includes('localhost') || currentUrl.includes('127.0.0.1')) {
        return currentUrl.replace(':5000', ':8000').replace(':3000', ':8000');
    }
    
    // Fallback padrão
    return 'http://localhost:8000';
}

const API_BASE_URL = getApiBaseUrl();

// Log para debug (remover em produção se necessário)
console.log('API Base URL:', API_BASE_URL);

// Casos de teste (mesmos dados dos scripts 1–5 em script_teste/)
const CASOS_TESTE = {
    t1: {
        label: 'Teste 1 — Sem diabetes',
        paciente: {
            Pregnancies: 1,
            Glucose: 85,
            BloodPressure: 66,
            SkinThickness: 29,
            Insulin: 0,
            BMI: 26.6,
            DiabetesPedigreeFunction: 0.351,
            Age: 31
        }
    },
    t2: {
        label: 'Teste 2 — Com diabetes',
        paciente: {
            Pregnancies: 6,
            Glucose: 148,
            BloodPressure: 72,
            SkinThickness: 35,
            Insulin: 0,
            BMI: 33.6,
            DiabetesPedigreeFunction: 0.627,
            Age: 50
        }
    },
    t3: {
        label: 'Teste 3 — Limítrofe',
        paciente: {
            Pregnancies: 3,
            Glucose: 120,
            BloodPressure: 80,
            SkinThickness: 25,
            Insulin: 100,
            BMI: 28.5,
            DiabetesPedigreeFunction: 0.450,
            Age: 40
        }
    },
    t4: {
        label: 'Teste 4 — Idoso sem diabetes',
        paciente: {
            Pregnancies: 2,
            Glucose: 95,
            BloodPressure: 70,
            SkinThickness: 30,
            Insulin: 80,
            BMI: 24.5,
            DiabetesPedigreeFunction: 0.300,
            Age: 65
        }
    },
    t5: {
        label: 'Teste 5 — Jovem com diabetes',
        paciente: {
            Pregnancies: 0,
            Glucose: 180,
            BloodPressure: 90,
            SkinThickness: 40,
            Insulin: 200,
            BMI: 35.0,
            DiabetesPedigreeFunction: 0.850,
            Age: 25
        }
    }
};

function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    // dispara eventos para qualquer validação/listener
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
}

// Preenche o formulário com base em um caso de teste
function preencherFormularioPaciente(paciente) {
    setInputValue('Pregnancies', paciente.Pregnancies);
    setInputValue('Glucose', paciente.Glucose);
    setInputValue('BloodPressure', paciente.BloodPressure);
    setInputValue('SkinThickness', paciente.SkinThickness);
    setInputValue('Insulin', paciente.Insulin);
    setInputValue('BMI', paciente.BMI);
    setInputValue('DiabetesPedigreeFunction', paciente.DiabetesPedigreeFunction);
    setInputValue('Age', paciente.Age);

    // Esconde resultados/erros anteriores ao trocar os dados
    document.getElementById('avaliacao-resultado').classList.add('hidden');
    document.getElementById('avaliacao-erro').classList.add('hidden');
}

// Handler chamado pelos botões do HTML
function preencherCasoTeste(casoId) {
    const caso = CASOS_TESTE[casoId];
    if (!caso) return;
    preencherFormularioPaciente(caso.paciente);
}

// Função para mostrar tabs
function showTab(tabName) {
    // Esconde todos os tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active de todos os botões
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Mostra o tab selecionado
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Ativa o botão correspondente
    event.target.classList.add('active');
}

// Função para formatar dados do paciente
function formatarDadosPaciente(paciente) {
    const campos = {
        'Pregnancies': 'Número de gestações',
        'Glucose': 'Glicose (mg/dL)',
        'BloodPressure': 'Pressão arterial (mmHg)',
        'SkinThickness': 'Espessura da pele (mm)',
        'Insulin': 'Insulina (µU/mL)',
        'BMI': 'IMC (Body Mass Index)',
        'DiabetesPedigreeFunction': 'Função de pedigree diabético',
        'Age': 'Idade'
    };
    
    let html = '';
    for (const [key, label] of Object.entries(campos)) {
        if (paciente[key] !== undefined) {
            html += `${label}: ${paciente[key]}\n`;
        }
    }
    return html;
}

// Função para exibir resultados da avaliação
function exibirResultadosAvaliacao(data) {
    // Esconde erros e mostra resultados
    document.getElementById('avaliacao-erro').classList.add('hidden');
    document.getElementById('avaliacao-resultado').classList.remove('hidden');
    
    // Dados do paciente
    const pacienteInfo = document.getElementById('paciente-info');
    pacienteInfo.textContent = formatarDadosPaciente(data.paciente);
    
    // Resultados dos modelos
    const modelosDiv = document.getElementById('modelos-resultado');
    modelosDiv.innerHTML = '';
    
    data.resultados.forEach(resultado => {
        const modeloDiv = document.createElement('div');
        modeloDiv.className = 'modelo-resultado';
        
        const predicaoClass = resultado.predicao_binaria === 1 ? 'predicao-positiva' : 'predicao-negativa';
        
        modeloDiv.innerHTML = `
            <h4>${resultado.modelo}</h4>
            <p class="${predicaoClass}">Predição: ${resultado.predicao}</p>
            <div class="probabilidade">
                <span>Probabilidade de Não Diabetes:</span>
                <span>${(resultado.probabilidade_nao_diabetes * 100).toFixed(2)}%</span>
            </div>
            <div class="probabilidade-bar" style="width: ${resultado.probabilidade_nao_diabetes * 100}%"></div>
            <div class="probabilidade">
                <span>Probabilidade de Diabetes:</span>
                <span>${(resultado.probabilidade_diabetes * 100).toFixed(2)}%</span>
            </div>
            <div class="probabilidade-bar diabetes" style="width: ${resultado.probabilidade_diabetes * 100}%"></div>
        `;
        
        modelosDiv.appendChild(modeloDiv);
    });
    
    // Explicação da IA
    if (data.explicacao_ia) {
        const explicacaoDiv = document.getElementById('explicacao-ia');
        explicacaoDiv.classList.remove('hidden');
        document.getElementById('explicacao-texto').textContent = data.explicacao_ia;
    } else {
        document.getElementById('explicacao-ia').classList.add('hidden');
    }
}

// Função para exibir erro na avaliação
function exibirErroAvaliacao(mensagem) {
    document.getElementById('avaliacao-resultado').classList.add('hidden');
    document.getElementById('avaliacao-erro').classList.remove('hidden');
    document.getElementById('erro-mensagem').textContent = mensagem;
}

// Função para submeter avaliação
document.getElementById('avaliacao-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Coleta dados do formulário
    const formData = new FormData(e.target);
    const paciente = {};
    
    for (const [key, value] of formData.entries()) {
        if (key === 'incluir_explicacao') continue;
        paciente[key] = key === 'Pregnancies' || key === 'Age' ? parseInt(value) : parseFloat(value);
    }
    
    const incluirExplicacao = document.getElementById('incluir_explicacao').checked;
    
    try {
        // Faz requisição para API
        const response = await fetch(`${API_BASE_URL}/avaliacao?incluir_explicacao=${incluirExplicacao}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(paciente)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Erro ao avaliar paciente');
        }
        
        const data = await response.json();
        exibirResultadosAvaliacao(data);
        
    } catch (error) {
        exibirErroAvaliacao(error.message);
    }
});

// Função para formatar métricas
function formatarMetricas(metricas) {
    if (!metricas) return 'N/A';
    return `Acurácia: ${(metricas.accuracy * 100).toFixed(2)}%\n` +
           `Recall: ${(metricas.recall * 100).toFixed(2)}%\n` +
           `F1-Score: ${(metricas.f1 * 100).toFixed(2)}%`;
}

// Função para formatar parâmetros
function formatarParametros(params) {
    if (!params) return 'N/A';
    let html = '';
    for (const [key, value] of Object.entries(params)) {
        html += `${key}: ${value}\n`;
    }
    return html;
}

// Função para exibir resultados do treinamento
function exibirResultadosTreinamento(data) {
    // Esconde loading e erros, mostra resultados
    document.getElementById('treinamento-loading').classList.add('hidden');
    document.getElementById('treinamento-erro').classList.add('hidden');
    document.getElementById('treinamento-resultado').classList.remove('hidden');
    
    // Status
    document.getElementById('status-info').textContent = `Status: ${data.status}\n${data.mensagem}`;
    
    // Métricas Base LR
    if (data.metricas_base_lr) {
        document.getElementById('metricas-base-lr').classList.remove('hidden');
        document.getElementById('metricas-lr').textContent = formatarMetricas(data.metricas_base_lr);
    }
    
    // Métricas Base RF
    if (data.metricas_base_rf) {
        document.getElementById('metricas-base-rf').classList.remove('hidden');
        document.getElementById('metricas-rf').textContent = formatarMetricas(data.metricas_base_rf);
    }
    
    // Métricas Otimizado RF
    if (data.metricas_otimizado_rf) {
        document.getElementById('metricas-otimizado-rf').classList.remove('hidden');
        document.getElementById('metricas-rf-opt').textContent = formatarMetricas(data.metricas_otimizado_rf);
    }
    
    // Parâmetros de otimização
    if (data.melhores_parametros) {
        document.getElementById('parametros-otimizacao').classList.remove('hidden');
        document.getElementById('parametros-info').textContent = formatarParametros(data.melhores_parametros);
    }
    
    // Tempo de execução
    if (data.tempo_execucao !== undefined) {
        document.getElementById('tempo-execucao').classList.remove('hidden');
        const minutos = Math.floor(data.tempo_execucao / 60);
        const segundos = (data.tempo_execucao % 60).toFixed(2);
        document.getElementById('tempo-info').textContent = 
            `Tempo total: ${minutos > 0 ? minutos + ' minutos e ' : ''}${segundos} segundos`;
    }
}

// Função para exibir erro no treinamento
function exibirErroTreinamento(mensagem) {
    document.getElementById('treinamento-loading').classList.add('hidden');
    document.getElementById('treinamento-resultado').classList.add('hidden');
    document.getElementById('treinamento-erro').classList.remove('hidden');
    document.getElementById('treinamento-erro-mensagem').textContent = mensagem;
}

// Função para treinar modelos
async function treinarModelos() {
    // Mostra loading e esconde outros elementos
    document.getElementById('treinamento-loading').classList.remove('hidden');
    document.getElementById('treinamento-resultado').classList.add('hidden');
    document.getElementById('treinamento-erro').classList.add('hidden');
    
    try {
        // Faz requisição para API
        const response = await fetch(`${API_BASE_URL}/treinamento`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Erro ao treinar modelos');
        }
        
        const data = await response.json();
        exibirResultadosTreinamento(data);
        
    } catch (error) {
        exibirErroTreinamento(error.message);
    }
}

// Função para baixar log de execução
async function baixarLog() {
    // Esconde mensagens de erro anteriores
    document.getElementById('log-download-erro').classList.add('hidden');
    
    try {
        console.log('Baixando log de:', `${API_BASE_URL}/download-log`);
        
        // Faz requisição para API
        const response = await fetch(`${API_BASE_URL}/download-log`, {
            method: 'GET',
        });
        
        if (!response.ok) {
            // Tenta obter mensagem de erro em JSON
            let errorMessage = 'Erro ao baixar log';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch {
                // Se não for JSON, usa o texto da resposta
                errorMessage = await response.text() || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        // Obtém o blob do arquivo
        const blob = await response.blob();
        
        // Cria URL temporária para download
        const url = window.URL.createObjectURL(blob);
        
        // Cria elemento <a> temporário para download
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pipeline_execution.log';
        document.body.appendChild(a);
        a.click();
        
        // Limpa
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        console.log('Log baixado com sucesso!');
        
    } catch (error) {
        console.error('Erro ao baixar log:', error);
        // Exibe erro na interface
        document.getElementById('log-download-erro').classList.remove('hidden');
        document.getElementById('log-download-erro-mensagem').textContent = error.message;
        
        // Scroll para o erro
        document.getElementById('log-download-erro').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

"""
Script de teste 03: Paciente limítrofe (valores intermediários)
Este teste verifica a avaliação de um paciente com valores clínicos
intermediários, onde a predição pode variar entre os modelos.
"""
import requests
import json

# URL da API
#API_URL = "http://localhost:8000"
API_URL = "https://fiap-techchallengefiap-fase2.azurewebsites.net/avaliacao?incluir_explicacao=true"


def testar_paciente_limitrofe():
    """Testa avaliação de paciente limítrofe."""
    
    print("=" * 60)
    print("TESTE 03: Paciente LIMÍTROFE (Valores Intermediários)")
    print("=" * 60)
    
    # Dados do paciente - valores intermediários (caso limítrofe)
    paciente = {
        "Pregnancies": 3,
        "Glucose": 120,
        "BloodPressure": 80,
        "SkinThickness": 25,
        "Insulin": 100,
        "BMI": 28.5,
        "DiabetesPedigreeFunction": 0.450,
        "Age": 40
    }
    
    print("\n📋 Dados do Paciente:")
    print(json.dumps(paciente, indent=2, ensure_ascii=False))
    print("\n⚠️  Valores intermediários:")
    print("   - Glicose: 120 mg/dL (pré-diabetes)")
    print("   - IMC: 28.5 (sobrepeso)")
    print("   - Idade: 40 anos")
    
    try:
        # Faz a requisição
        print("\n🔄 Enviando requisição para /avaliacao...")
        response = requests.post(
            f"{API_URL}/avaliacao",
            json=paciente,
            params={"incluir_explicacao": True}
        )
        
        # Verifica status
        if response.status_code == 200:
            resultado = response.json()
            
            print("\n✅ Requisição bem-sucedida!")
            print("\n📊 Resultados da Predição:")
            print("-" * 60)
            
            for resultado_modelo in resultado["resultados"]:
                print(f"\n🔹 Modelo: {resultado_modelo['modelo']}")
                print(f"   Predição: {resultado_modelo['predicao']}")
                print(f"   Probabilidade (Não Diabetes): {resultado_modelo['probabilidade_nao_diabetes']:.2%}")
                print(f"   Probabilidade (Diabetes): {resultado_modelo['probabilidade_diabetes']:.2%}")
            
            if resultado.get("explicacao_ia"):
                print("\n🤖 Explicação IA:")
                print("-" * 60)
                print(resultado["explicacao_ia"])
            
            # Verifica consistência entre modelos
            pred_lr = resultado["resultados"][0]["predicao_binaria"]
            pred_rf = resultado["resultados"][1]["predicao_binaria"]
            
            if pred_lr == pred_rf:
                print(f"\n✅ Modelos concordam: {resultado['resultados'][0]['predicao']}")
            else:
                print("\n⚠️  Modelos discordam (caso limítrofe):")
                print(f"   - Regressão Logística: {resultado['resultados'][0]['predicao']}")
                print(f"   - Random Forest: {resultado['resultados'][1]['predicao']}")
            
        else:
            print(f"\n❌ Erro na requisição: {response.status_code}")
            print(f"Detalhes: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar à API.")
        print("Certifique-se de que a API está rodando em http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")


if __name__ == "__main__":
    testar_paciente_limitrofe()

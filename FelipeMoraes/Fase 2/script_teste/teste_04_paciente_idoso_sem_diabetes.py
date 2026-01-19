"""
Script de teste 04: Paciente idoso sem diabetes
Este teste verifica a avaliação de um paciente idoso com valores
clínicos normais, demonstrando que idade avançada não necessariamente
indica diabetes se outros fatores estão controlados.
"""
import requests
import json

# URL da API
#API_URL = "http://localhost:8000"
API_URL = "https://fiap-techchallengefiap-fase2.azurewebsites.net/avaliacao?incluir_explicacao=true"

def testar_paciente_idoso_sem_diabetes():
    """Testa avaliação de paciente idoso sem diabetes."""
    
    print("=" * 60)
    print("TESTE 04: Paciente IDOSO SEM Diabetes")
    print("=" * 60)
    
    # Dados do paciente - idoso com valores normais
    paciente = {
        "Pregnancies": 2,
        "Glucose": 95,
        "BloodPressure": 70,
        "SkinThickness": 30,
        "Insulin": 80,
        "BMI": 24.5,
        "DiabetesPedigreeFunction": 0.300,
        "Age": 65
    }
    
    print("\n📋 Dados do Paciente:")
    print(json.dumps(paciente, indent=2, ensure_ascii=False))
    print("\nℹ️  Características:")
    print("   - Idade: 65 anos (idoso)")
    print("   - Glicose normal: 95 mg/dL")
    print("   - IMC normal: 24.5")
    print("   - Pressão arterial normal: 70 mmHg")
    
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
            
            # Verifica se a predição está correta (esperado: negativo)
            predicao_rf = resultado["resultados"][1]["predicao_binaria"]
            if predicao_rf == 0:
                print("\n✅ TESTE PASSOU: Predição correta (Negativo para diabetes)")
                print("   Mesmo sendo idoso, valores normais indicam baixo risco")
            else:
                print("\n⚠️  ATENÇÃO: Predição positiva para diabetes")
                print("   Pode ser devido à idade avançada sendo um fator de risco")
            
        else:
            print(f"\n❌ Erro na requisição: {response.status_code}")
            print(f"Detalhes: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar à API.")
        print("Certifique-se de que a API está rodando em http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")


if __name__ == "__main__":
    testar_paciente_idoso_sem_diabetes()

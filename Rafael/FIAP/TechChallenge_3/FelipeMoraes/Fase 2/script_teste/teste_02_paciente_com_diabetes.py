"""
Script de teste 02: Paciente com diabetes (valores indicativos)
Este teste verifica a avaliação de um paciente com valores clínicos
que indicam risco de diabetes, esperando predição positiva.
"""
import requests
import json

# URL da API
#API_URL = "http://localhost:8000"
API_URL = "https://fiap-techchallengefiap-fase2.azurewebsites.net/avaliacao?incluir_explicacao=true"

def testar_paciente_com_diabetes():
    """Testa avaliação de paciente com diabetes."""
    
    print("=" * 60)
    print("TESTE 02: Paciente COM Diabetes (Valores Indicativos)")
    print("=" * 60)
    
    # Dados do paciente - valores indicativos de diabetes
    paciente = {
        "Pregnancies": 6,
        "Glucose": 148,
        "BloodPressure": 72,
        "SkinThickness": 35,
        "Insulin": 0,
        "BMI": 33.6,
        "DiabetesPedigreeFunction": 0.627,
        "Age": 50
    }
    
    print("\n📋 Dados do Paciente:")
    print(json.dumps(paciente, indent=2, ensure_ascii=False))
    print("\n⚠️  Valores indicativos de diabetes:")
    print("   - Glicose elevada: 148 mg/dL")
    print("   - IMC elevado: 33.6")
    print("   - Idade: 50 anos")
    
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
            
            # Verifica se a predição está correta (esperado: positivo)
            predicao_rf = resultado["resultados"][1]["predicao_binaria"]
            if predicao_rf == 1:
                print("\n✅ TESTE PASSOU: Predição correta (Positivo para diabetes)")
            else:
                print("\n⚠️  ATENÇÃO: Predição negativa para diabetes (pode ser um falso negativo)")
            
        else:
            print(f"\n❌ Erro na requisição: {response.status_code}")
            print(f"Detalhes: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar à API.")
        print("Certifique-se de que a API está rodando em http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")


if __name__ == "__main__":
    testar_paciente_com_diabetes()

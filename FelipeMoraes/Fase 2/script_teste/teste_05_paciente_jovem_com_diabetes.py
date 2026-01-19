"""
Script de teste 05: Paciente jovem com diabetes
Este teste verifica a avaliação de um paciente jovem com valores
clínicos que indicam diabetes, demonstrando que idade jovem não
impede o diagnóstico quando há fatores de risco presentes.
"""
import requests
import json

# URL da API
#API_URL = "http://localhost:8000"
API_URL = "https://fiap-techchallengefiap-fase2.azurewebsites.net/avaliacao?incluir_explicacao=true"

def testar_paciente_jovem_com_diabetes():
    """Testa avaliação de paciente jovem com diabetes."""
    
    print("=" * 60)
    print("TESTE 05: Paciente JOVEM COM Diabetes")
    print("=" * 60)
    
    # Dados do paciente - jovem com valores indicativos de diabetes
    paciente = {
        "Pregnancies": 0,
        "Glucose": 180,
        "BloodPressure": 90,
        "SkinThickness": 40,
        "Insulin": 200,
        "BMI": 35.0,
        "DiabetesPedigreeFunction": 0.850,
        "Age": 25
    }
    
    print("\n📋 Dados do Paciente:")
    print(json.dumps(paciente, indent=2, ensure_ascii=False))
    print("\n⚠️  Características:")
    print("   - Idade: 25 anos (jovem)")
    print("   - Glicose muito elevada: 180 mg/dL")
    print("   - IMC elevado: 35.0 (obesidade)")
    print("   - Função de pedigree alta: 0.850")
    print("   - Pressão arterial elevada: 90 mmHg")
    
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
                print("   Mesmo sendo jovem, fatores de risco elevados indicam diabetes")
            else:
                print("\n⚠️  ATENÇÃO: Predição negativa para diabetes")
                print("   Pode ser um falso negativo devido à idade jovem")
            
        else:
            print(f"\n❌ Erro na requisição: {response.status_code}")
            print(f"Detalhes: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO: Não foi possível conectar à API.")
        print("Certifique-se de que a API está rodando em http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")


if __name__ == "__main__":
    testar_paciente_jovem_com_diabetes()

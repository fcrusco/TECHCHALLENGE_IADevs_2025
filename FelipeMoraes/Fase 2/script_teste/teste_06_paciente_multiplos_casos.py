"""
Script de teste 06: Múltiplos pacientes em lote
Este teste executa avaliações para vários pacientes de uma vez,
incluindo casos com e sem diabetes, para testar a robustez da API.
"""
import requests
import json
import time

# URL da API
#API_URL = "http://localhost:8000"
API_URL = "https://fiap-techchallengefiap-fase2.azurewebsites.net/avaliacao?incluir_explicacao=true"

def testar_multiplos_pacientes():
    """Testa avaliação de múltiplos pacientes."""
    
    print("=" * 60)
    print("TESTE 06: Múltiplos Pacientes em Lote")
    print("=" * 60)
    
    # Lista de pacientes variados
    pacientes = [
        {
            "nome": "Paciente 1 - Sem Diabetes",
            "dados": {
                "Pregnancies": 0,
                "Glucose": 80,
                "BloodPressure": 65,
                "SkinThickness": 20,
                "Insulin": 0,
                "BMI": 22.0,
                "DiabetesPedigreeFunction": 0.200,
                "Age": 28
            },
            "esperado": "Negativo"
        },
        {
            "nome": "Paciente 2 - Com Diabetes",
            "dados": {
                "Pregnancies": 8,
                "Glucose": 183,
                "BloodPressure": 64,
                "SkinThickness": 0,
                "Insulin": 0,
                "BMI": 23.3,
                "DiabetesPedigreeFunction": 0.672,
                "Age": 32
            },
            "esperado": "Positivo"
        },
        {
            "nome": "Paciente 3 - Sem Diabetes",
            "dados": {
                "Pregnancies": 1,
                "Glucose": 89,
                "BloodPressure": 66,
                "SkinThickness": 23,
                "Insulin": 94,
                "BMI": 28.1,
                "DiabetesPedigreeFunction": 0.167,
                "Age": 21
            },
            "esperado": "Negativo"
        },
        {
            "nome": "Paciente 4 - Com Diabetes",
            "dados": {
                "Pregnancies": 0,
                "Glucose": 137,
                "BloodPressure": 40,
                "SkinThickness": 35,
                "Insulin": 168,
                "BMI": 43.1,
                "DiabetesPedigreeFunction": 2.288,
                "Age": 33
            },
            "esperado": "Positivo"
        },
        {
            "nome": "Paciente 5 - Limítrofe",
            "dados": {
                "Pregnancies": 5,
                "Glucose": 116,
                "BloodPressure": 74,
                "SkinThickness": 0,
                "Insulin": 0,
                "BMI": 25.6,
                "DiabetesPedigreeFunction": 0.201,
                "Age": 30
            },
            "esperado": "Negativo"
        }
    ]
    
    resultados_teste = []
    
    for i, paciente_info in enumerate(pacientes, 1):
        print(f"\n{'='*60}")
        print(f"Testando {paciente_info['nome']}")
        print(f"{'='*60}")
        
        try:
            # Faz a requisição
            print(f"\n🔄 Enviando requisição {i}/{len(pacientes)}...")
            response = requests.post(
                f"{API_URL}/avaliacao",
                json=paciente_info["dados"],
                params={"incluir_explicacao": False}  # Sem explicação para ser mais rápido
            )
            
            if response.status_code == 200:
                resultado = response.json()
                
                # Obtém predição do Random Forest
                pred_rf = resultado["resultados"][1]
                predicao_binaria = pred_rf["predicao_binaria"]
                predicao_texto = "Positivo" if predicao_binaria == 1 else "Negativo"
                
                print(f"✅ Predição: {pred_rf['predicao']}")
                print(f"   Probabilidade Diabetes: {pred_rf['probabilidade_diabetes']:.2%}")
                
                # Verifica se corresponde ao esperado
                esperado_binario = 1 if paciente_info["esperado"] == "Positivo" else 0
                acerto = predicao_binaria == esperado_binario
                
                resultados_teste.append({
                    "paciente": paciente_info["nome"],
                    "esperado": paciente_info["esperado"],
                    "obtido": predicao_texto,
                    "acerto": acerto,
                    "probabilidade": pred_rf["probabilidade_diabetes"]
                })
                
                if acerto:
                    print(f"✅ Resultado esperado: {paciente_info['esperado']} - CORRETO")
                else:
                    print(f"⚠️  Resultado esperado: {paciente_info['esperado']} - DIFERENTE")
                
            else:
                print(f"❌ Erro na requisição: {response.status_code}")
                resultados_teste.append({
                    "paciente": paciente_info["nome"],
                    "erro": f"Status {response.status_code}"
                })
            
            # Pequeno delay entre requisições
            if i < len(pacientes):
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            resultados_teste.append({
                "paciente": paciente_info["nome"],
                "erro": str(e)
            })
    
    # Resumo final
    print(f"\n{'='*60}")
    print("RESUMO DOS TESTES")
    print(f"{'='*60}")
    
    acertos = sum(1 for r in resultados_teste if r.get("acerto", False))
    total = len([r for r in resultados_teste if "acerto" in r])
    
    print(f"\n📊 Estatísticas:")
    print(f"   Total de testes: {len(pacientes)}")
    print(f"   Testes bem-sucedidos: {total}")
    print(f"   Acertos: {acertos}/{total}")
    print(f"   Taxa de acerto: {(acertos/total*100) if total > 0 else 0:.1f}%")
    
    print(f"\n📋 Detalhes:")
    for resultado in resultados_teste:
        if "erro" in resultado:
            print(f"   ❌ {resultado['paciente']}: ERRO - {resultado['erro']}")
        else:
            status = "✅" if resultado["acerto"] else "⚠️"
            print(f"   {status} {resultado['paciente']}: "
                  f"Esperado={resultado['esperado']}, "
                  f"Obtido={resultado['obtido']}, "
                  f"Prob={resultado['probabilidade']:.2%}")


if __name__ == "__main__":
    testar_multiplos_pacientes()

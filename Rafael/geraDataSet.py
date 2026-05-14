"""
Gerador de Dataset Sintético de Áudio — VozSaúde
Gera 12 áudios MP3 simulando consultas médicas em saúde da mulher
usando a API TTS da OpenAI (voz: nova — feminina, em português)
"""

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
 
load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Diretório de saída
OUTPUT_DIR = Path("C:/Users/rafael.silva/Desktop/Alura/FIAPHandsOn/Projeto4/teste") #INSERIR O CAMINHO AONDE QUER QUE OS AUDIOS SEJAM SALVOS
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# FALAS DO DATASET
# 3 casos por tipo de consulta (alto, médio, baixo risco)
# ─────────────────────────────────────────────

DATASET = [

    # ── GINECOLÓGICA ──────────────────────────────────────────────────────────
    {
        "id": "gineco_01_alto",
        "tipo": "ginecologica",
        "risco_esperado": "ALTO",
        "descricao": "Paciente hesitante, sinais de violência sexual velada",
        "fala": (
            "Doutora... eu tô com muita dor há uns três meses. "
            "É uma dor assim... difícil de explicar. "
            "Fica na parte de baixo do abdômen. "
            "Eu... eu não sei ao certo como aconteceu. "
            "Meu marido às vezes é... é meio bruto, sabe? "
            "Mas não precisa anotar isso não, doutora. "
            "Não é nada demais. Eu acho que é stress mesmo. "
            "Será que pode ser só stress?"
        )
    },
    {
        "id": "gineco_02_medio",
        "tipo": "ginecologica",
        "risco_esperado": "MÉDIO",
        "descricao": "Paciente ansiosa ao relatar irregularidade menstrual",
        "fala": (
            "Então, doutora, minha menstruação tá muito irregular já faz uns quatro meses. "
            "Às vezes atrasa quinze dias, às vezes vem duas vezes no mês. "
            "Eu fico muito preocupada, fico pesquisando na internet e acho que pode ser muita coisa. "
            "Tô dormindo mal por causa disso. "
            "Não tenho parceiro fixo no momento, mas faço exame regularmente. "
            "Ah, e tô tomando anticoncepcional há dois anos, nunca tive problema antes."
        )
    },
    {
        "id": "gineco_03_baixo",
        "tipo": "ginecologica",
        "risco_esperado": "BAIXO",
        "descricao": "Consulta de rotina, paciente tranquila",
        "fala": (
            "Oi doutora, vim fazer minha consulta anual de rotina. "
            "Tô me sentindo bem, sem queixas específicas. "
            "Minha menstruação tá regular, vem certinho a cada vinte e oito dias. "
            "Faço papanicolau todo ano, o último foi normal. "
            "Tô no mesmo anticoncepcional há três anos, sem problemas. "
            "Só queria checar se tá tudo certo mesmo, por prevenção."
        )
    },

    # ── PRÉ-NATAL ────────────────────────────────────────────────────────────
    {
        "id": "prenatal_01_alto",
        "tipo": "pre_natal",
        "risco_esperado": "ALTO",
        "descricao": "Ansiedade severa, isolamento, possível violência doméstica",
        "fala": (
            "Doutora, eu... eu tô com muito medo. "
            "Toda noite eu fico pensando que alguma coisa vai dar errado com o bebê. "
            "Não consigo dormir direito. Choro muito. "
            "Meu marido fala que eu tô exagerando, que essa neura minha vai prejudicar a criança. "
            "Às vezes ele perde a paciência e grita muito comigo. "
            "Já saí de casa duas vezes esse mês por causa de briga. "
            "Não tenho família aqui perto, vim de longe. "
            "Tô me sentindo muito sozinha. Muito mesmo."
        )
    },
    {
        "id": "prenatal_02_medio",
        "tipo": "pre_natal",
        "risco_esperado": "MÉDIO",
        "descricao": "Ansiedade moderada, preocupação com trabalho e financeiro",
        "fala": (
            "Tô com vinte e duas semanas, doutora. "
            "Fisicamente tô bem, as enjoas passaram. "
            "Mas tô muito preocupada com o emprego. "
            "Não sei se vou conseguir manter a licença, minha chefe tá me pressionando bastante. "
            "Fico ansiosa pensando em como vai ser financeiramente com o bebê. "
            "Meu companheiro tá trabalhando, mas o salário dele é pouco. "
            "Consigo dormir, mas acordo bastante preocupada."
        )
    },
    {
        "id": "prenatal_03_baixo",
        "tipo": "pre_natal",
        "risco_esperado": "BAIXO",
        "descricao": "Gestante saudável, bem assistida, sem sinais de alerta",
        "fala": (
            "Oi doutora, tô com trinta semanas. Tô me sentindo muito bem. "
            "O bebê tá mexendo bastante, é muito emocionante. "
            "Meu marido tá super presente, foi comigo em todas as consultas. "
            "Fizemos o cursinho de preparação pro parto, foi ótimo. "
            "Tô dormindo bem, comendo direito. "
            "Minha família tá animadíssima, minha mãe vai ficar comigo no primeiro mês. "
            "Só tenho mesmo aquela ansiedade normal de primeira viagem."
        )
    },

    # ── PÓS-PARTO ────────────────────────────────────────────────────────────
    {
        "id": "posparto_01_alto",
        "tipo": "pos_parto",
        "risco_esperado": "ALTO",
        "descricao": "Forte indicativo de depressão pós-parto, pensamentos intrusivos",
        "fala": (
            "Meu filho tem seis semanas. "
            "Eu... eu não tô conseguindo. "
            "Eu choro o dia inteiro. Não sinto vontade de nada. "
            "Às vezes olho pra ele e me pergunto se eu realmente amo ele, e isso me apavora. "
            "Tenho um medo enorme de ficar sozinha com ele. "
            "Esses dias tive um pensamento de me machucar... não fiz nada, mas assustei. "
            "Meu marido fala que é frescura, que minha mãe criou seis filhos e não ficou assim. "
            "Não tô conseguindo amamentar direito. Me sinto um fracasso total."
        )
    },
    {
        "id": "posparto_02_medio",
        "tipo": "pos_parto",
        "risco_esperado": "MÉDIO",
        "descricao": "Baby blues prolongado, cansaço extremo, falta de apoio",
        "fala": (
            "Minha bebê tem três semanas. "
            "Tô muito cansada, doutora. Não durmo mais que duas horas seguidas. "
            "Choro às vezes, mas acho que é cansaço mesmo. "
            "Amo muito minha filha, mas tô me sentindo sobrecarregada. "
            "Meu marido trabalha muito, então fico sozinha com ela a maior parte do tempo. "
            "Minha mãe veio ajudar na primeira semana, mas foi embora. "
            "Não sei se isso que tô sentindo é normal ou não."
        )
    },
    {
        "id": "posparto_03_baixo",
        "tipo": "pos_parto",
        "risco_esperado": "BAIXO",
        "descricao": "Puérpera bem adaptada, boa rede de apoio",
        "fala": (
            "Meu bebê tem dois meses, doutora. Tô me sentindo bem. "
            "Claro que o cansaço é real, acordo várias vezes à noite. "
            "Mas tô feliz, amamentando bem, o vínculo com ele é muito bonito. "
            "Meu marido divide bastante as tarefas, ele acorda junto comigo à noite. "
            "Minha sogra mora perto e ajuda bastante. "
            "Retomei minhas caminhadas essa semana, tô me sentindo mais disposta. "
            "Tô ansiosa com as vacinas dele, mas nada fora do normal."
        )
    },

    # ── VIOLÊNCIA ─────────────────────────────────────────────────────────────
    {
        "id": "violencia_01_alto",
        "tipo": "violencia",
        "risco_esperado": "ALTO",
        "descricao": "Violência física e psicológica ativa, risco imediato",
        "fala": (
            "Eu caí da escada, doutora. Por isso esse roxo no braço. "
            "Não foi nada não. Sou muito desajeitada mesmo. "
            "Pode deixar, não precisa chamar ninguém. "
            "Meu marido tá lá fora esperando, ele gosta de me acompanhar nas consultas. "
            "Ele sempre vem junto. "
            "Eu... eu tô bem. Tô ótima. "
            "Ah, essa marca no pescoço foi minha corrente que arranhou. "
            "Por favor, doutora, não faz escândalo não. "
            "Se ele souber que eu falei alguma coisa vai ser pior."
        )
    },
    {
        "id": "violencia_02_medio",
        "tipo": "violencia",
        "risco_esperado": "MÉDIO",
        "descricao": "Violência psicológica, controle financeiro, isolamento",
        "fala": (
            "Tô com dor de cabeça constante há uns dois meses. "
            "Meu marido fala que é frescura, que eu invento doença pra não trabalhar. "
            "Ele controla o dinheiro todo, eu tenho que pedir quando preciso comprar alguma coisa. "
            "Saí do meu emprego porque ele não queria que eu trabalhasse fora. "
            "Não vejo minha família quase nunca, ele acha que minha mãe me influencia mal. "
            "Às vezes me sinto muito sozinha e inútil. "
            "Mas ele é bom pai pras crianças, então... sei lá."
        )
    },
    {
        "id": "violencia_03_baixo",
        "tipo": "violencia",
        "risco_esperado": "BAIXO",
        "descricao": "Paciente em processo de recuperação, já fora da situação de risco",
        "fala": (
            "Vim fazer acompanhamento, doutora. "
            "Faz seis meses que me separei. Foi muito difícil, mas tô bem melhor. "
            "Fiz um boletim de ocorrência, tô com medida protetiva. "
            "Tô fazendo terapia toda semana, tem me ajudado muito. "
            "Voltei a trabalhar, tô morando com minha irmã. "
            "Ainda tenho pesadelos às vezes, mas tô conseguindo lidar. "
            "Quero fazer os exames de rotina que deixei pra trás durante esse período."
        )
    },
]


def gerar_audio(item: dict) -> Path:
    """Gera um arquivo MP3 para um item do dataset usando OpenAI TTS."""
    output_path = OUTPUT_DIR / f"{item['id']}.mp3"

    if output_path.exists():
        print(f"  ⏭  Já existe, pulando: {output_path.name}")
        return output_path

    print(f"  🎙  Gerando: {output_path.name} ({item['descricao']})")

    response = client.audio.speech.create(
        model="tts-1",
        voice="nova",       # Voz feminina, natural em português
        input=item["fala"],
        response_format="mp3",
        speed=0.92          # Levemente mais lento para simular fala hesitante/emocional
    )
    with open(output_path, "wb") as f:
        f.write(response.content)


def gerar_metadata():
    """Gera arquivo JSON com metadados do dataset."""
    metadata = []
    for item in DATASET:
        metadata.append({
            "arquivo": f"{item['id']}.mp3",
            "tipo_consulta": item["tipo"],
            "risco_esperado": item["risco_esperado"],
            "descricao": item["descricao"],
            "fala_original": item["fala"]
        })

    meta_path = OUTPUT_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n   Metadados salvos em: {meta_path}")


def main():
    print("=" * 55)
    print("  VozSaúde — Gerador de Dataset Sintético de Áudio")
    print("=" * 55)
    print(f"\n  Total de áudios a gerar: {len(DATASET)}")
    print(f"  Diretório de saída: {OUTPUT_DIR.resolve()}\n")

    sucessos = 0
    erros = []

    for item in DATASET:
        try:
            gerar_audio(item)
            sucessos += 1
        except Exception as e:
            print(f"   Erro em {item['id']}: {e}")
            erros.append(item["id"])

    gerar_metadata()

    print("\n" + "=" * 55)
    print(f"   Áudios gerados com sucesso: {sucessos}/{len(DATASET)}")
    if erros:
        print(f"   Erros: {', '.join(erros)}")
    print("\n  Dataset pronto! Estrutura gerada:")
    print("  dataset/")
    for item in DATASET:
        print(f"    ├── {item['id']}.mp3")
    print("    └── metadata.json")
    print("=" * 55)


if __name__ == "__main__":
    main()
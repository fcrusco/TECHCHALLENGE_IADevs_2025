# Tech Challenge - FIAP
# Curso Pós IA para DEVS

## Resumo do Tech Challenge

Este projeto utiliza os aprendizados do curso até o momento, priorizando técnicas de **machine learning** e o uso de **modelos CNN** para realizar o treinamento de um modelo em cima de um dataset contendo dados sobre lesões de pele e possíveis casos de câncer de pele. A partir do modelo treinado, utilizaremos um segundo dataset só de imagens para prever a lesão e se possui câncer ou não.  

Neste modelo inicialmente utilizamos um modelo CNN básico, mas devido a limitação de tempo, performance e acurácia obtida após diversos testes optamos por utilizar um backbone já treinado: o **MobileNetV2** para o treinamento do modelo CNN.

---

## Estrutura do Projeto

```
📁 ExtraVisao_TechChallenge_Final/
│
├── ExtraVisao_TechChallenge_Final.ipynb   # Notebook principal
├── README.md                              # Este arquivo
├── requirements.txt                       # Dependências do projeto
└── ExtraVisao_TechChallenge_Final.pdf     # Resultado em pdf
```

O notebook também pode ser acessado por meio do collab: [https://colab.research.google.com/drive/1JC5UU0dCoGAlvcwNdsAP6DCG16FluyKW](https://colab.research.google.com/drive/1JC5UU0dCoGAlvcwNdsAP6DCG16FluyKW)
---

## Datasets Utilizados

Foram utilizados dois conjuntos de dados complementares, ambos públicos e provenientes do Kaggle:

1. **Skin Cancer Dataset**  
   🔗 [https://www.kaggle.com/datasets/farjanakabirsamanta/skin-cancer-dataset/data](https://www.kaggle.com/datasets/farjanakabirsamanta/skin-cancer-dataset/data)  
   - Contém imagens de diferentes tipos de lesões de pele.  
   - Usado para treinar o modelo CNN.  

2. **Skin Cancer 9 Classes (ISIC)**  
   🔗 [https://www.kaggle.com/datasets/nodoubttome/skin-cancer9-classesisic](https://www.kaggle.com/datasets/nodoubttome/skin-cancer9-classesisic)  
   - Conjunto de imagens do repositório ISIC (International Skin Imaging Collaboration).  
   - Classifica nove tipos de lesões, incluindo malignas e benignas.  
   - Possui apenas imagens, não existe metadata com a rotulação das lesões.

---

## Modelos e Técnicas Utilizadas

O trabalho realiza experimentos com diferentes **redes neurais convolucionais (CNNs)** pré-treinadas em ImageNet, ajustadas (fine-tuning) para o problema de classificação de lesões de pele.

Modelos testados:
- **MobileNetV2**  
- Também foi utilizado um modelo CNN básico descartado devido a performance. O código do modelo criado está comentado na parte de preparo do treinamento, na seção **Executando o CNN: MobileNetV2**.

Técnicas empregadas:
- **Data Augmentation**
- **Limpeza de dados**
- **Normalização de imagens**  
- **Fine-tuning de camadas convolucionais**  
- **Treinamento com Early Stopping e ReduceLROnPlateau**  
- **Divisão estratificada dos dados**
- **Métricas de desempenho:**

---

## Instruções de Execução

### 1. Requisitos

Certifique-se de ter o **Python 3.10+** e o **Jupyter Notebook** instalados.
Após testes realizados, recomendá-se que não se utilize versões do Python superiores a 3.12.8.  
Recomenda-se criar um ambiente virtual:

```bash
python -m venv env
source env/bin/activate        # Linux/Mac
env\Scripts\activate         # Windows
```

Instale as dependências principais:

```bash
pip install -r requirements.txt
```

---

### 2. Execução do Notebook

1. Abra o Jupyter Notebook:
   ```bash
   jupyter notebook
   ```
2. Carregue o arquivo:  
   `ExtraVisao_TechChallenge_Final.ipynb`
3. Execute todas as células em sequência (`Kernel > Restart & Run All`).

O notebook faz:
- Download e extração dos datasets
- Pré-processamento das imagens
- Treinamento do modelo CNN
- Avaliação e visualização dos resultados

---

## Resultados Esperados

- Acurácia de classificação superior a **80%** em testes realizados na execuções.  
- Diferenciação entre **lesões benignas e malignas**.  
- Visualizações gráficas de desempenho e matriz de confusão.  

---

**Projeto desenvolvido como parte do Tech Challenge – Visão Computacional**  
- Felipe Lessa de Moraes
- Fábio Crusco da Silva
- Fábio Alves de Lima
- Rafael Iornandes
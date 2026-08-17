# Datasets de benchmark

Os 30 datasets mais conhecidos do Kaggle, usados para validar a inferência de tipos e as análises do maat em dados reais. **Os arquivos de dados não são versionados** (ver `.gitignore`) — apenas este manifesto. Para baixá-los:

```bash
kaggle auth login          # uma vez, abre o navegador
python scripts/download_datasets.py
```

| Pasta | Ref no Kaggle | O que testa no maat |
|---|---|---|
| titanic | `yasserh/titanic-dataset` | binárias, nominais, discretas, ausentes |
| iris | `uciml/iris` | contínuas puras, nominal de 3 níveis |
| wine-quality | `uciml/red-wine-quality-cortez-et-al-2009` | contínuas, ordinal disfarçada de inteiro (quality) |
| diabetes | `uciml/pima-indians-diabetes-database` | contínuas com zeros-que-são-ausentes |
| breast-cancer | `uciml/breast-cancer-wisconsin-data` | contínuas correlacionadas, coluna id |
| adult-census | `uciml/adult-census-income` | nominais de várias cardinalidades, renda categórica |
| mushrooms | `uciml/mushroom-classification` | só qualitativas (22 nominais) |
| sms-spam | `uciml/sms-spam-collection-dataset` | regime textual (mensagens livres) |
| heart-disease | `johnsmith88/heart-disease-dataset` | discretas vs binárias codificadas como número |
| california-housing | `camnugent/california-housing-prices` | contínuas, nominal geográfica |
| house-sales-kc | `harlfoxem/housesalesprediction` | **datas**, contínuas, cep/zipcode suspeito |
| insurance | `mirichoi0218/insurance` | mistura clássica quali + quanti |
| telco-churn | `blastchar/telco-customer-churn` | binárias em texto (Yes/No), TotalCharges numérico-em-string |
| mall-customers | `vjchoudhary7/customer-segmentation-tutorial-in-python` | id, discretas, poucas linhas |
| students | `spscientist/students-performance-in-exams` | ordinais reais (nível educação dos pais) |
| wine-reviews | `zynicide/wine-reviews` | regime textual longo (descrições), cauda longa (vinícolas) |
| world-happiness | `unsdsn/world-happiness` | contínuas por país, múltiplos csvs por ano |
| videogame-sales | `gregorut/videogamesales` | cauda longa (títulos), ano como número |
| fifa19 | `karangadiya/fifa19` | dezenas de colunas mistas, moedas em string ("€110.5M") |
| google-play | `lava18/google-play-store-apps` | sujeira real: "3.0M", "Varies with device", datas em texto |
| netflix | `shivamb/netflix-shows` | **datas**, duração em texto ("90 min", "2 Seasons") |
| movies | `rounakbanik/the-movies-dataset` | json embutido em coluna, cauda longa (grande, ~230 MB) |
| youtube-trending | `datasnaek/youtube-new` | **datas**, tags, múltiplos países (~200 MB) |
| nyc-airbnb | `dgomonov/new-york-city-airbnb-open-data` | regime textual (nomes), geo, cauda longa |
| hotel-bookings | `jessemostipak/hotel-booking-demand` | **datas** decompostas em 3 colunas, muitas categóricas |
| avocado | `neuromusic/avocado-prices` | **série temporal** semanal, regiões |
| creditcard-fraud | `mlg-ulb/creditcardfraud` | contínuas anônimas, desbalanceamento extremo (~66 MB) |
| ecommerce | `carrie1/ecommerce-data` | **timestamps**, invoice id, quantidades negativas (devoluções) |
| suicide-rates | `russellyates88/suicide-rates-overview-1985-to-2016` | ordinal de faixa etária, ano, país |
| stroke | `fedesoriano/stroke-prediction-dataset` | binárias, "N/A" em string, bmi numérico-em-string |

Critério de escolha: além da fama, cada dataset exercita um canto diferente do fluxo de classificação — datas, ordinais disfarçadas, números-em-string, texto livre, ids, sujeira real de coleta.

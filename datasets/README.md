# Datasets de benchmark

Os 30 datasets mais conhecidos do Kaggle, usados para validar a inferência de tipos e as análises do maat em dados reais. **Os arquivos de dados não são versionados** (ver `.gitignore`) — apenas este manifesto. Para baixá-los:

```bash
kaggle auth login          # uma vez, abre o navegador
python scripts/download_datasets.py
```

| Pasta | Ref no Kaggle | O que testa no maat |
|---|---|---|
| titanic | [`yasserh/titanic-dataset`](https://www.kaggle.com/datasets/yasserh/titanic-dataset) | binárias, nominais, discretas, ausentes |
| iris | [`uciml/iris`](https://www.kaggle.com/datasets/uciml/iris) | contínuas puras, nominal de 3 níveis |
| wine-quality | [`uciml/red-wine-quality-cortez-et-al-2009`](https://www.kaggle.com/datasets/uciml/red-wine-quality-cortez-et-al-2009) | contínuas, ordinal disfarçada de inteiro (quality) |
| diabetes | [`kumargh/pimaindiansdiabetescsv`](https://www.kaggle.com/datasets/kumargh/pimaindiansdiabetescsv) | contínuas com zeros-que-são-ausentes |
| breast-cancer | [`uciml/breast-cancer-wisconsin-data`](https://www.kaggle.com/datasets/uciml/breast-cancer-wisconsin-data) | contínuas correlacionadas, coluna id |
| adult-census | [`uciml/adult-census-income`](https://www.kaggle.com/datasets/uciml/adult-census-income) | nominais de várias cardinalidades, renda categórica |
| mushrooms | [`uciml/mushroom-classification`](https://www.kaggle.com/datasets/uciml/mushroom-classification) | só qualitativas (22 nominais) |
| sms-spam | [`uciml/sms-spam-collection-dataset`](https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset) | regime textual (mensagens livres) |
| heart-disease | [`johnsmith88/heart-disease-dataset`](https://www.kaggle.com/datasets/johnsmith88/heart-disease-dataset) | discretas vs binárias codificadas como número |
| california-housing | [`camnugent/california-housing-prices`](https://www.kaggle.com/datasets/camnugent/california-housing-prices) | contínuas, nominal geográfica |
| house-sales-kc | [`harlfoxem/housesalesprediction`](https://www.kaggle.com/datasets/harlfoxem/housesalesprediction) | **datas**, contínuas, cep/zipcode suspeito |
| insurance | [`mirichoi0218/insurance`](https://www.kaggle.com/datasets/mirichoi0218/insurance) | mistura clássica quali + quanti |
| telco-churn | [`blastchar/telco-customer-churn`](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) | binárias em texto (Yes/No), TotalCharges numérico-em-string |
| mall-customers | [`vjchoudhary7/customer-segmentation-tutorial-in-python`](https://www.kaggle.com/datasets/vjchoudhary7/customer-segmentation-tutorial-in-python) | id, discretas, poucas linhas |
| students | [`spscientist/students-performance-in-exams`](https://www.kaggle.com/datasets/spscientist/students-performance-in-exams) | ordinais reais (nível educação dos pais) |
| wine-reviews | [`zynicide/wine-reviews`](https://www.kaggle.com/datasets/zynicide/wine-reviews) | regime textual longo (descrições), cauda longa (vinícolas) |
| world-happiness | [`unsdsn/world-happiness`](https://www.kaggle.com/datasets/unsdsn/world-happiness) | contínuas por país, múltiplos csvs por ano |
| videogame-sales | [`gregorut/videogamesales`](https://www.kaggle.com/datasets/gregorut/videogamesales) | cauda longa (títulos), ano como número |
| fifa19 | [`javagarm/fifa-19-complete-player-dataset`](https://www.kaggle.com/datasets/javagarm/fifa-19-complete-player-dataset) | dezenas de colunas mistas, moedas em string ("€110.5M") |
| google-play | [`lava18/google-play-store-apps`](https://www.kaggle.com/datasets/lava18/google-play-store-apps) | sujeira real: "3.0M", "Varies with device", datas em texto |
| netflix | [`shivamb/netflix-shows`](https://www.kaggle.com/datasets/shivamb/netflix-shows) | **datas**, duração em texto ("90 min", "2 Seasons") |
| movies | [`rounakbanik/the-movies-dataset`](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) | json embutido em coluna, cauda longa (grande, ~230 MB) |
| youtube-trending | [`datasnaek/youtube-new`](https://www.kaggle.com/datasets/datasnaek/youtube-new) | **datas**, tags, múltiplos países (~200 MB) |
| nyc-airbnb | [`dgomonov/new-york-city-airbnb-open-data`](https://www.kaggle.com/datasets/dgomonov/new-york-city-airbnb-open-data) | regime textual (nomes), geo, cauda longa |
| hotel-bookings | [`jessemostipak/hotel-booking-demand`](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand) | **datas** decompostas em 3 colunas, muitas categóricas |
| avocado | [`neuromusic/avocado-prices`](https://www.kaggle.com/datasets/neuromusic/avocado-prices) | **série temporal** semanal, regiões |
| creditcard-fraud | [`mlg-ulb/creditcardfraud`](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) | contínuas anônimas, desbalanceamento extremo (~66 MB) |
| ecommerce | [`carrie1/ecommerce-data`](https://www.kaggle.com/datasets/carrie1/ecommerce-data) | **timestamps**, invoice id, quantidades negativas (devoluções) |
| suicide-rates | [`russellyates88/suicide-rates-overview-1985-to-2016`](https://www.kaggle.com/datasets/russellyates88/suicide-rates-overview-1985-to-2016) | ordinal de faixa etária, ano, país |
| stroke | [`fedesoriano/stroke-prediction-dataset`](https://www.kaggle.com/datasets/fedesoriano/stroke-prediction-dataset) | binárias, "N/A" em string, bmi numérico-em-string |

Critério de escolha: além da fama, cada dataset exercita um canto diferente do fluxo de classificação — datas, ordinais disfarçadas, números-em-string, texto livre, ids, sujeira real de coleta.

## Dados abertos do governo brasileiro

10 fontes oficiais com download direto verificado (`python scripts/download_gov_datasets.py`). Além da fama, trazem as pegadinhas reais do dado público brasileiro: encoding latin-1, separador `;`, vírgula decimal e códigos que parecem números:

| Pasta | Fonte | O que testa no maat |
|---|---|---|
| [gov-bcb-ipca](https://www3.bcb.gov.br/sgspub/consultarvalores/telaCvsSelecionarSeries.paint) | Banco Central (SGS 433) | série temporal mensal desde 1980, vírgula decimal |
| [gov-bcb-selic](https://www3.bcb.gov.br/sgspub/consultarvalores/telaCvsSelecionarSeries.paint) | Banco Central (SGS 4390) | Selic acumulada mensal desde 1986 — série longa |
| [gov-bcb-dolar](https://www3.bcb.gov.br/sgspub/consultarvalores/telaCvsSelecionarSeries.paint) | Banco Central (SGS 1) | série diária com gaps de fim de semana |
| [gov-ibge-municipios](https://servicodados.ibge.gov.br/api/docs/localidades) | IBGE (API localidades) | JSON aninhado, 5.570 municípios, hierarquia região/UF |
| [gov-tesouro-direto](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) | Tesouro Transparente | preços/taxas por título e vencimento — datas múltiplas por linha |
| [gov-tse-candidatos](https://dadosabertos.tse.jus.br/dataset/candidatos-2024) | TSE (eleições 2024) | dezenas de categóricas em pt-BR, latin-1, separador `;` |
| [gov-camara-cota](https://www.camara.leg.br/transparencia/gastos-parlamentares) | Câmara dos Deputados | despesas: fornecedores em cauda longa, CNPJ como código |
| [gov-cvm-fundos](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario) | CVM (informes diários) | CNPJ-id, valores por cota, temporal denso |
| [gov-transparencia-viagens](https://portaldatransparencia.gov.br/download-de-dados/viagens) | Portal da Transparência | órgãos, cargos, valores e datas de viagens a serviço |
| [gov-comex-exp-mun](https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta) | Comex Stat (MDIC) | exportações por município: códigos NCM/SH4, país, kg/FOB |

(INMET e PRF ficaram de fora: os servidores recusaram download direto no teste de 2026-08-16.)

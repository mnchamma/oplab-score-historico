from matplotlib import style
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
from pandas.core.common import SettingWithCopyWarning


warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

style.use('dark_background')

### FUNÇÃO PARA RETORNAR A SÉRIE HISTÓRICA
def getFechamentosPorData(token,symbol,data_inicio,data_fim,resolution="1d"):     
    ## HEADER DE AUTENTICAÇÃO
    header = {"Access-Token": token}
    
    ## CHAMADA NA API 
    dados = requests.get('https://api.oplab.com.br/v3/market/historical/{}/{}?from={}&to={}?smooth=true'.format(
    symbol, resolution, data_inicio.strftime("%Y%m%d%H%M"), data_fim.strftime("%Y%m%d%H%M")),
                        headers=header).json()['data']
    ## CONSTRUÇÃO DO DATAFRAME NO PANDAS
    fechamentos = []
    datas_list = []
    for i in dados:
        fechamentos.append(i['close'])
        datas_list.append(datetime.fromtimestamp(int(str(i['time'])[:10])))
    df = pd.DataFrame({'Adj Close': fechamentos}, index = datas_list)
    return df

### FUNÇÃO PARA PEGAR TOKEN DE AUTENTICAÇÃO NA API
def get_token(email,senha):
    ## BODY PARA REQUISIÇÃO NA API
    body = {"email": email,"password": senha}
    
    ## CHAMADA NA API
    r = requests.post('https://api.oplab.com.br/v3/domain/users/authenticate',json=body).json()['access-token']
    return r

### FUNÇÃO PARA RETORNAR OS FUNDAMENTOS DO ATIVO
def get_fund_inf(token,symbol):
    r = requests.get('https://api.oplab.com.br/v3/market/stocks/{}?with_financials=dre,bpa,dfc,stocks,bpp,sector,fundamentals'.format(symbol), headers={"Access-Token": token})
    return r.json()

### INSERIR EMAIL E SENHA --> get_token('seu@email.com','sua_senha')
try:
    token = get_token()
except:
    print('TOKEN ERRADO')
    exit()


ativo = 'PETR4'

symbol = ativo
menor_data = datetime(2012,1,1)

### COLETAR E SEPARAR OS RELATÓRIOS FINANCEIROS
df = get_fund_inf(token,symbol)['financial']
dre = df['dre']
dfc = df['dfc']
bpp = df['bpp']
dt = list(dre.keys())

### ITERAR SOBRE OS RELATÓRIOS E GERAR DATAFRAME ORGANIZADO EM ORDEM DE TRIMESTRES
rev = 0
ebit = 0
ger_caixa = 0
passivo_circ = 0
relatorios_df = pd.DataFrame()
for d in dt:
    mes = datetime.strptime(d,'%Y-%m-%d').month
    rev = dre[d]['3_01']['value']
    ebit = dre[d]['3_05']['value']
    ger_caixa = dfc[d]['6_05']['value']
    passivo_circ = bpp[d]['2_01']['value']
    relatorios_df[datetime.strptime(d,'%Y-%m-%d')] = [rev,ebit,ger_caixa,passivo_circ,mes]
        
relatorios_df = relatorios_df.transpose().sort_index().reset_index()

### GERAR SCORE SOBRE A VARIAÇÃO DO INDICADOR DE UM TRIMESTRE PARA OUTRO
score = []
r = relatorios_df
for i in relatorios_df.index:
    if i < 4 :
        score.append(None)
    else:
        rev_change = int(r.iloc[i-4,:][0] < r.iloc[i,:][0]) ### SE AUMENTOU
        ebit_change = int(r.iloc[i-4,:][1] < r.iloc[i,:][1]) ### SE AUMENTOU
        ger_caixa_change = int(r.iloc[i-4,:][2] < r.iloc[i,:][2]) ### SE AUMENTOU
        passivo_circ_change = int(r.iloc[i-4,:][3] > r.iloc[i,:][3]) ### SE DIMINUIU
        score.append(rev_change + ebit_change + ger_caixa_change + passivo_circ_change) ### SOMA-SE AS NOTAS

relatorios_df['score'] = score

### PLOTAR O GRÁFICO COM SCORE X PREÇO
fig, ax = plt.subplots(1,1, figsize = (15,8))

ax.plot(relatorios_df['index'],relatorios_df['score'], color = 'blue',linewidth = 3)
ax.set_ylabel('Score'.format(symbol), fontsize=30)
closes = getFechamentosPorData(token, symbol, menor_data, datetime.today(),resolution="1M")
ax2 = ax.twinx()
data_string = [x.date() for x in list(closes.index)]
ax2.plot(data_string, list(closes['Adj Close']), color='grey')
ax2.set_ylabel('Preço'.format(symbol), fontsize=30)
fig.suptitle('Score X Preço {}'.format(symbol), fontsize=35)
plt.show()
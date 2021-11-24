# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 04:23:23 2020

@author: Vinicius
"""
#%% IMPORTAR PACOTES
import requests as rq 
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import codecs
import smtplib
from datetime import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
#%% EXTRAIR DADOS
url = 'https://www.fundsexplorer.com.br/ranking'
page = rq.get(url)
soup = BeautifulSoup(page.text, 'html.parser')
html_table = soup.find_all('table', id='table-ranking')
#CRIAR O DATAFRAME BRUTO
df = pd.read_html(str(html_table))[0]
#%% FORMATAR DADOS
pd.set_option('max_columns', None)
#RENOMEAR COLUNAS PARA MELHOR MANIPULAÇÃO
df.columns = ['codigo','setor','preco_rs','liquidez_diaria','dividendo','dy','dy_3m_acum','dy_6m_acum',
'dy_12m_acum','dy_3m_media','dy_6m_media','dy_12m_media','dy_ano','var_preco','rentab_per','rentab_acum',
'pl','vpa','p_vpa','dy_patrim','var_patrim','rentab_patrim_per','rentab_patrim_acum','vacancia_fisica',
'vacancia_financeira','qtde_ativos']

#FUNÇÃO PARA CONVERTER AS COLUNAS QUE CONTÊM STRINGS DE PERCENTUAIS EM VALORES DECIMAIS
def convert_perc(dataframe, *args):
    for col in args:
        try:
            dataframe[str(col)+'_nf'] = dataframe[col].str.rstrip('%').str.replace('.','').str.replace(',','.').astype(float)/100
        except:
            continue

#A FUNÇÃO FAZ ISSO:
#df['vacancia_financeira'] = df['vacancia_financeira'].str.rstrip('%').str.replace(',','.').astype(float)/100
#df['vacancia_fisica'] = df['vacancia_fisica'].str.rstrip('%').str.replace(',','.').astype(float)/100
# ETC

#FUNÇÃO PARA FORMATAR PARA R$
def formata_rs(x):
    return 'R$ {:,.2f}'.format(x).replace(',','X').replace('.',',').replace('X','.')

convert_perc(df,'dy','dy_3m_acum','dy_6m_acum', 'dy_12m_acum','dy_3m_media','dy_6m_media','dy_12m_media','dy_ano','var_preco',
             'rentab_per','rentab_acum','dy_patrim','var_patrim','rentab_patrim_per','rentab_patrim_acum','vacancia_fisica',
             'vacancia_financeira')

# P/VPA FOI CONVERTIDO PARA NÚMERO INTEIRO NA IMPORTAÇÃO. NECESSÁRIO TRANSFORMAR EM PERCENTUAL
df['p_vpa'] = df['p_vpa']/100
# CRIAÇÃO DA COLUNA VACÂNCIA, A SER CONSIDERADA NA BUSCA, DANDO PREFERÊNCIA PARA A VACÂNCIA FINANCEIRA, QUANDO HOUVER
df['vacancia'] = np.where(df['vacancia_financeira_nf'].notna(), df['vacancia_financeira_nf'], df['vacancia_fisica_nf'])
# CRIAÇÃO DA COLUNA VOLUME, COM A LIQUIDEZ x PREÇO
df['preco'] = df['preco_rs'].str.replace('R\$ ','').str.replace('\.','').str.replace('\,','.').astype(float)
df['volume'] = df['liquidez_diaria']*df['preco']
    
#%% BUSCAR CONFORME CRITÉRIO E FORMATAR O RESULTADO
oport_compra = df.query('vacancia < 0.1 & qtde_ativos > 5 & p_vpa > 0.9 & p_vpa < 1.15 & dy_nf > 0.9*dy_12m_media_nf & volume > volume.quantile(0.4)')
result = oport_compra[['codigo','setor','preco_rs','liquidez_diaria','volume','dy','dy_12m_media','pl','vpa','p_vpa','vacancia_fisica','vacancia_financeira','qtde_ativos']].sort_values(by=['dy_12m_media'], ascending=False)
result['volume'] = result['volume'].apply(formata_rs)
result[['vacancia_fisica','vacancia_financeira']] = result[['vacancia_fisica','vacancia_financeira']].replace(np.nan, 'N/D')
result['liquidez_diaria'] = result['liquidez_diaria'].apply(lambda x: '{:,.0f}'.format(x)).str.replace(',','.')
result.columns = ['Código', 'Setor', 'Preço', 'Liquidez Diária', 'Volume Diário', 'Div. Yield (DY)','DY 12m (Média)','Patr. Líquido','VPA','P/VPA','Vacância Física','Vacância Financeira','Qtde. Ativos']
print(result)
#%% ABRIR ARQUIVO EXTERNO E MONTAR O HTML
f = codecs.open('C:/path/email_template.html','r',encoding='utf-8')
template = f.read()
f.close()
hoje = dt.now()
data_hoje = str(hoje.day) + '/' + str(hoje.month) + '/' + str(hoje.year)
html_final = template.replace('$tab_html$',result.to_html(index=False)).replace('$XX/XX/XXXX$', data_hoje)
#%% ENVIO DE EMAIL COM OS ALERTAS
fromaddr = "sender@isp.com"
toaddr = ["dest1@isp.com", 'dest2@isp.com']
msg = MIMEMultipart()
msg['From'] = "Recomenda FII"
msg['To'] = ", ".join(toaddr)
msg['Subject'] = "Recomenda FII - " + data_hoje

body = html_final
msg.attach(MIMEText(body, 'html'))
# 
server = smtplib.SMTP('smtp.isp.com', 587)
server.starttls()
server.login(fromaddr, "password")
text = msg.as_string()
server.sendmail(fromaddr, toaddr, text)
server.quit()
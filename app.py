import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import norm
from datetime import datetime

st.set_page_config(page_title="Scanner Opções Semanais", layout="wide")
st.title("Scanner de Opções Semanais - Operações Cobertas")
st.write("O app analisa ativos confiáveis do Yahoo Finance e mostra as 5 melhores operações da semana.")

# Ativos confiáveis para opções brasileiras
ativos = [
    "BBAS3.SA", "ITUB4.SA", "BBDC4.SA",
    "PETR4.SA",
    "SUZB3.SA"
]

# Funções para probabilidade aproximada
def prob_otm_call(S, K, T, sigma):
    if sigma == 0:
        return 0
    d2 = (np.log(S/K) - 0.5*sigma**2*T) / (sigma*np.sqrt(T))
    return norm.cdf(-d2)

def prob_otm_put(S, K, T, sigma):
    if sigma == 0:
        return 0
    d2 = (np.log(S/K) - 0.5*sigma**2*T) / (sigma*np.sqrt(T))
    return norm.cdf(d2)

def analisar():
    resultados = []

    for ativo in ativos:
        try:
            ticker = yf.Ticker(ativo)
            hist = ticker.history(period="3mo")
            if len(hist) < 30:
                continue
            preco = hist["Close"].iloc[-1]
            retornos = hist["Close"].pct_change().dropna()
            vol = retornos.std() * np.sqrt(252)
            expiracoes = ticker.options

            for exp in expiracoes:
                data_exp = datetime.strptime(exp, "%Y-%m-%d")
                dias = (data_exp - datetime.today()).days
                if dias <= 0 or dias > 30:
                    continue

                cadeia = ticker.option_chain(exp)
                calls = cadeia.calls
                puts = cadeia.puts
                T = dias / 365

                for _, row in calls.iterrows():
                    if row["bid"] <= 0:
                        continue
                    strike = row["strike"]
                    prob = prob_otm_call(preco, strike, T, vol)
                    retorno = row["bid"] / preco
                    score = prob * retorno
                    resultados.append({
                        "Ativo": ativo.replace(".SA", ""),
                        "Opção": row["contractSymbol"],
                        "Tipo": "CALL",
                        "Strike": round(strike, 2),
                        "Probabilidade (%)": round(prob*100, 1),
                        "Bid": row["bid"],
                        "Ask": row["ask"],
                        "Retorno (%)": round(retorno*100, 2),
                        "Ordem": "VENDER NO BID",
                        "Score": score
                    })

                for _, row in puts.iterrows():
                    if row["bid"] <= 0:
                        continue
                    strike = row["strike"]
                    prob = prob_otm_put(preco, strike, T, vol)
                    retorno = row["bid"] / strike
                    score = prob * retorno
                    resultados.append({
                        "Ativo": ativo.replace(".SA", ""),
                        "Opção": row["contractSymbol"],
                        "Tipo": "PUT",
                        "Strike": round(strike, 2),
                        "Probabilidade (%)": round(prob*100, 1),
                        "Bid": row["bid"],
                        "Ask": row["ask"],
                        "Retorno (%)": round(retorno*100, 2),
                        "Ordem": "VENDER NO BID",
                        "Score": score
                    })
        except:
            pass

    if len(resultados) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(resultados)
    df = df.sort_values("Score", ascending=False)
    df = df.head(5)
    return df[["Ativo", "Opção", "Tipo", "Strike", "Probabilidade (%)", "Bid", "Ask", "Retorno (%)", "Ordem"]]

# Botão de análise
if st.button("ANALISAR MELHORES OPÇÕES DA SEMANA"):
    with st.spinner("Analisando mercado..."):
        tabela = analisar()
    if len(tabela) == 0:
        st.warning("Nenhuma opção encontrada. Isso acontece se o Yahoo Finance não listar opções semanais desse ativo.")
    else:
        st.subheader("TOP 5 OPERAÇÕES DA SEMANA")
        st.dataframe(tabela, use_container_width=True)
        melhor = tabela.iloc[0]
        st.success(f"Operação sugerida: VENDER {melhor['Tipo']} {melhor['Opção']} NO BID")

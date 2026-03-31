import streamlit as st
import pandas as pd
import re
import numpy as np
import json
import os
from difflib import SequenceMatcher

# 1. Configuração inicial
st.set_page_config(page_title="Andrey Delivery Pro - Sequence Notes", layout="wide")

# --- BANCO DE DADOS DE NOTAS ---
OBS_FILE = "observacoes.json"

def carregar_obs():
    if os.path.exists(OBS_FILE):
        try:
            with open(OBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def salvar_obs(dic_obs):
    with open(OBS_FILE, "w", encoding="utf-8") as f:
        json.dump(dic_obs, f, indent=4, ensure_ascii=False)

# --- FUNÇÕES DE PADRONIZAÇÃO ---
def padronizar_complemento(texto):
    if not texto: return ""
    t = str(texto).upper().strip()
    # Padroniza termos comuns para evitar duplicidade no banco
    t = re.sub(r'\b(APARTAMENTO|APTO|APT|AP)\b', 'AP', t)
    t = re.sub(r'\b(BLOCO|BL)\b', 'BL', t)
    t = t.replace('.', '').replace('  ', ' ')
    return t

def extrair_numero(texto):
    if pd.isna(texto): return ""
    match = re.search(r',\s*(\d+)', str(texto))
    return match.group(1) if match else ""

def extrair_complemento_puro(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper()
    match = re.search(r'(APT|APTO|AP|APARTAMENTO|BLOCO|BL|SL|SALA|FUNDOS|CASA\s\d+|AP\s\d+).*', t)
    return match.group(0).strip() if match else ""

def normalizar_rua(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper().strip()
    substituicoes = {
        r'\bR\b': 'RUA', r'\bAV\b': 'AVENIDA', r'\bM\b': 'MARTIM',
        r'\bPROF\b': 'PROFESSOR', r'\bDR\b': 'DOUTOR', r'\.': ''
    }
    for padrao, sub in substituicoes.items():
        t = re.sub(padrao, sub, t)
    return t.split(',')[0].strip()

def formatar_sequencia_visual(lista_seq):
    numeros = []
    adicionais = 0
    for s in lista_seq:
        s_str = str(s).strip()
        if s_str in ['-', 'nan', '', 'None']: adicionais += 1
        else:
            num = "".join(filter(str.isdigit, s_str.split('.')[0]))
            if num: numeros.append(int(num))
    if not numeros: return "📦 Sem Ordem" if adicionais == 0 else f"📦 {adicionais} Adds"
    numeros = sorted(list(set(numeros)))
    ranges = []
    if not numeros: return f"📦 {adicionais} Adds"
    start, last = numeros[0], numeros[0]
    for n in numeros[1:]:
        if n == last + 1: last = n
        else:
            ranges.append(f"{start} ao {last}" if start != last else str(start))
            start = last = n
    ranges.append(f"{start} ao {last}" if start != last else str(start))
    resumo = "Pacote " + ", ".join(ranges)
    if adicionais > 0: resumo += f" + {adicionais} Add"
    return f"📦 {resumo}"

# --- INICIALIZAÇÃO DE MEMÓRIA ---
if 'enderecos_planilha' not in st.session_state:
    st.session_state.enderecos_planilha = []

# --- INTERFACE ---
st.title("🚚 Andrey Delivery Pro")

tab1, tab2 = st.tabs(["📋 Processar Planilha", "📝 Gerenciar Notas"])

with tab1:
    arquivo = st.file_uploader("1. Carregar Planilha", type=['xlsx', 'csv'], key="up_v5")
    
    if arquivo:
        df_temp = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
        if 'Destination Address' in df_temp.columns:
            novos = sorted(df_temp['Destination Address'].unique().tolist())
            if novos != st.session_state.enderecos_planilha:
                st.session_state.enderecos_planilha = novos
                st.rerun()

            if st.button("🚀 Processar e Agrupar AGORA"):
                notas_vivas = carregar_obs()
                df = df_temp.copy()
                
                df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)
                df['Rua_Base'] = df['Destination Address'].apply(normalizar_rua)
                df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
                
                # Identifica quais linhas possuem notas salvas no sistema
                def verificar_minha_nota(row):
                    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
                    for chave_s in notas_vivas.keys():
                        try:
                            partes_s = chave_s.split('|')
                            if len(partes_s) == 3:
                                r_s, n_s, c_s = partes_s
                                if n_p == n_s and c_p == c_s and SequenceMatcher(None, r_p, r_s).ratio() > 0.8:
                                    return True
                        except: continue
                    return False
                
                df['Tem_Minha_Nota'] = df.apply(verificar_minha_nota, axis=1)

                # --- LÓGICA DE AGRUPAMENTO ---
                group_ids = np.zeros(len(df))
                curr = 1
                for i in range(len(df)):
                    if group_ids[i] == 0:
                        group_ids[i] = curr
                        for j in range(i + 1, len(df)):
                            m_num = (df.iloc[i]['Num_Casa'] == df.iloc[j]['Num_Casa']) and (df.iloc[i]['Num_Casa'] != "")
                            sim_rua = SequenceMatcher(None, df.iloc[i]['Rua_Base'], df.iloc[j]['Rua_Base']).ratio()
                            if m_num and sim_rua > 0.8:
                                # Agrupa se ambos não têm nota OU se for o mesmo AP com nota
                                if df.iloc[i]['Tem_Minha_Nota'] == df.iloc[j]['Tem_Minha_Nota']:
                                    if df.iloc[i]['Tem_Minha_Nota']:
                                        if df.iloc[i]['Comp_Padrao'] == df.iloc[j]['Comp_Padrao']:
                                            group_ids[j] = curr
                                    else:
                                        group_ids[j] = curr
                        curr += 1
                
                df['GroupID'] = group_ids
                
                # Agrupamento para consolidar os pacotes
                df_f = df.groupby('GroupID').agg({
                    'Sequence': lambda x: list(x),
                    'Destination Address': 'first', 'Bairro': 'first', 'City': 'first',
                    'Zipcode/Postal code': 'first', 'Latitude': 'first', 'Longitude': 'first',
                    'Rua_Base': 'first', 'Num_Casa': 'first', 'Comp_Padrao': 'first'
                }).reset_index(drop=True)

                # Insere a nota no início do campo Sequence
                def aplicar_formatacao_final(row):
                    texto_seq = formatar_sequencia_visual(row['Sequence'])
                    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
                    nota_encontrada = ""
                    for chave_s, nota_s in notas_vivas.items():
                        try:
                            partes_s = chave_s.split('|')
                            if len(partes_s) == 3:
                                r_s, n_s, c_s = partes_s
                                if n_p == n_s and c_p == c_s and SequenceMatcher(None, r_p, r_s).ratio() > 0.8:
                                    nota_encontrada = nota_s
                                    break
                        except: continue
                    
                    if nota_encontrada:
                        return f"⚠️ {nota_encontrada} | {texto_seq}"
                    return texto_seq

                df_f['Sequence'] = df_f.apply(aplicar_formatacao_final, axis=1)
                
                cols_final = ['Sequence', 'Destination Address', 'Bairro', 'City', 'Zipcode/Postal code', 'Latitude', 'Longitude']
                
                st.success(f"✅ Agrupamento concluído. Notas inseridas no campo Sequence.")
                st.dataframe(df_f[cols_final])
                csv = df_f[cols_final].to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha", csv, f"Rota_Notas_Sequence_{arquivo.name}")

with tab2:
    st.session_state.banco_notas = carregar_obs()
    st.subheader("📝 Gerenciar Notas")
    
    lista_opcoes = ["-- Selecione um endereço --"] + st.session_state.enderecos_planilha if st.session_state.enderecos_planilha else ["-- Planilha não carregada --"]
    endereco_selecionado = st.selectbox("📍 Buscar da Planilha:", lista_opcoes)
    
    if endereco_selecionado and endereco_selecionado not in ["-- Selecione um endereço --", "-- Planilha não carregada --"]:
        rua_sug, num_sug, comp_sug = normalizar_rua(endereco_selecionado), extrair_numero(endereco_selecionado), extrair_complemento_puro(endereco_selecionado)
    else:
        rua_sug, num_sug, comp_sug = "", "", ""

    with st.form("form_notas", clear_on_submit=True):
        col_r, col_n, col_c = st.columns([2, 1, 1])
        with col_r: rua_in = st.text_input("Rua", value=rua_sug).upper().strip()
        with col_n: num_in = st.text_input("Número", value=num_sug).strip()
        with col_c: comp_in = st.text_input("Complemento (AP)", value=comp_sug).upper().strip()
        obs_in = st.text_input("Nota / Observação")
        
        if st.form_submit_button("➕ Salvar Nota"):
            if rua_in and num_in and obs_in:
                banco = carregar_obs()
                chave = f"{rua_in}|{num_in}|{padronizar_complemento(comp_in)}"
                banco[chave] = obs_in
                salvar_obs(banco)
                st.success("Nota salva!")
                st.rerun()

    st.divider()
    
    if st.session_state.banco_notas:
        st.subheader("📋 Notas Ativas")
        for chave, nota in list(st.session_state.banco_notas.items()):
            try:
                partes = chave.split('|')
                end_label = f"{partes[0]}, {partes[1]} {partes[2]}" if len(partes) == 3 else chave.replace('|', ', ')
                col_obs, col_end, col_del = st.columns([2, 2, 1])
                col_obs.write(f"⚠️ **{nota}**")
                col_end.write(f"{end_label}")
                if col_del.button("🗑️ Apagar", key=f"del_v5_{chave}"):
                    banco_atual = carregar_obs()
                    if chave in banco_atual:
                        del banco_atual[chave]
                        salvar_obs(banco_atual)
                    st.rerun()
            except: continue
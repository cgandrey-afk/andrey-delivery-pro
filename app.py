import streamlit as st
import pandas as pd
import re
import numpy as np
import json
import os
from datetime import datetime
from difflib import SequenceMatcher

# 1. Configuração inicial do Dashboard
st.set_page_config(page_title="Gerenciador de Rotas", layout="wide", page_icon="🚚")

# --- BANCO DE DADOS (JSON) ---
OBS_FILE = "observacoes.json"
COND_FILE = "condominios.json"

def carregar_dados(arquivo):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def salvar_dados(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# --- FUNÇÕES DE PADRONIZAÇÃO E LIMPEZA ---
def limpar_para_condominio(texto):
    if not texto: return ""
    t = str(texto).upper().strip()
    t = re.sub(r'(\d+),\s*\1', r'\1', t)
    # Corta em complementos comuns para ter a base Rua + Número
    t = re.split(r'\b(APT|APTO|AP|APARTAMENTO|BLOCO|BL|SL|SALA|FUNDOS|CASA|A\d+|B\d+|C\d+|D\d+)\b', t)[0]
    return t.replace(',', ' ').replace('  ', ' ').strip()

def padronizar_complemento(texto):
    if not texto: return ""
    t = str(texto).upper().strip()
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
if 'temp_condo_list' not in st.session_state:
    st.session_state.temp_condo_list = []

# --- INTERFACE ---
st.title("🚚 Gerenciador de Rotas")

tab1, tab2, tab3 = st.tabs(["📋 Processar Planilha", "📝 Gerenciar Notas", "🏢 Condomínios"])

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
                notas_vivas = carregar_dados(OBS_FILE)
                condos_db = carregar_dados(COND_FILE)
                df = df_temp.copy()
                
                # 1. Identificação de Bases e Notas
                df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)
                df['Rua_Base'] = df['Destination Address'].apply(normalizar_rua)
                df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
                
                def verificar_minha_nota(row):
                    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
                    for chave_s in notas_vivas.keys():
                        partes_s = chave_s.split('|')
                        if len(partes_s) == 3:
                            if n_p == partes_s[1] and c_p == partes_s[2] and SequenceMatcher(None, r_p, partes_s[0]).ratio() > 0.8:
                                return True
                    return False
                
                df['Tem_Minha_Nota'] = df.apply(verificar_minha_nota, axis=1)

                # 2. Lógica de Endereço Final (Respeitando a Barreira de Notas)
                def definir_destino_final(row):
                    addr_original = row['Destination Address']
                    # BARREIRA: Se tem nota, mantém o endereço original (não vai para a portaria principal)
                    if row['Tem_Minha_Nota']:
                        return addr_original
                    
                    # Se não tem nota, verifica se pertence a algum condomínio
                    addr_limpo = limpar_para_condominio(addr_original)
                    for principal, lista_membros in condos_db.items():
                        p_limpo = limpar_para_condominio(principal)
                        m_limpos = [limpar_para_condominio(m) for m in lista_membros]
                        if addr_limpo == p_limpo or addr_limpo in m_limpos:
                            return principal
                    return addr_original

                df['Addr_Final'] = df.apply(definir_destino_final, axis=1)

                # 3. Agrupamento Consolidado
                group_ids = np.zeros(len(df))
                curr = 1
                for i in range(len(df)):
                    if group_ids[i] == 0:
                        group_ids[i] = curr
                        for j in range(i + 1, len(df)):
                            # Agrupa se o endereço final (já processado) for idêntico
                            if df.iloc[i]['Addr_Final'] == df.iloc[j]['Addr_Final']:
                                # Se um tem nota e o outro não, eles não agrupam (separação de pacotes especiais)
                                if df.iloc[i]['Tem_Minha_Nota'] == df.iloc[j]['Tem_Minha_Nota']:
                                    group_ids[j] = curr
                        curr += 1
                
                df['GroupID'] = group_ids
                df_f = df.groupby('GroupID').agg({
                    'Sequence': lambda x: list(x), 'Addr_Final': 'first', 'Bairro': 'first', 'City': 'first',
                    'Zipcode/Postal code': 'first', 'Latitude': 'first', 'Longitude': 'first',
                    'Rua_Base': 'first', 'Num_Casa': 'first', 'Comp_Padrao': 'first'
                }).reset_index(drop=True)

                df_f = df_f.rename(columns={'Addr_Final': 'Destination Address'})
                df_f['Destination Address'] = df_f['Destination Address'].apply(lambda x: f"📍 {x}")

                def aplicar_formatacao_final(row):
                    texto_seq = formatar_sequencia_visual(row['Sequence'])
                    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
                    nota_encontrada = ""
                    for chave_s, nota_s in notas_vivas.items():
                        partes_s = chave_s.split('|')
                        if len(partes_s) == 3 and n_p == partes_s[1] and c_p == partes_s[2] and SequenceMatcher(None, r_p, partes_s[0]).ratio() > 0.8:
                            nota_encontrada = nota_s
                            break
                    return f"⚠️ {nota_encontrada} | {texto_seq}" if nota_encontrada else texto_seq

                df_f['Sequence'] = df_f.apply(aplicar_formatacao_final, axis=1)
                cols_f = ['Sequence', 'Destination Address', 'Bairro', 'City', 'Zipcode/Postal code', 'Latitude', 'Longitude']
                
                st.success("✅ Agrupamento concluído!")
                st.dataframe(df_f[cols_f])
                st.download_button("📥 Baixar Planilha", df_f[cols_f].to_csv(index=False).encode('utf-8-sig'), 
                                   f"Roteiro_{datetime.now().strftime('%d-%m-%Y')}.csv", "text/csv")

# --- AS ABAS 2 E 3 PERMANECEM COM A MESMA LÓGICA DE CADASTRO ---
with tab2:
    st.session_state.banco_notas = carregar_dados(OBS_FILE)
    st.subheader("📝 Gerenciar Notas")
    end_sel = st.selectbox("📍 Buscar da Planilha:", ["-- Selecione --"] + st.session_state.enderecos_planilha, key="sel_notas")
    rua_sug = normalizar_rua(end_sel) if end_sel != "-- Selecione --" else ""
    num_sug = extrair_numero(end_sel) if end_sel != "-- Selecione --" else ""
    comp_sug = extrair_complemento_puro(end_sel) if end_sel != "-- Selecione --" else ""

    with st.form("form_notas", clear_on_submit=True):
        c1, n1, cp1 = st.columns([2, 1, 1])
        rua_in = c1.text_input("Rua", value=rua_sug).upper().strip()
        num_in = n1.text_input("Número", value=num_sug).strip()
        comp_in = cp1.text_input("Comp (AP)", value=comp_sug).upper().strip()
        obs_in = st.text_input("Nota / Observação")
        if st.form_submit_button("➕ Salvar Nota"):
            if rua_in and num_in and obs_in:
                b = carregar_dados(OBS_FILE)
                b[f"{rua_in}|{num_in}|{padronizar_complemento(comp_in)}"] = obs_in
                salvar_dados(OBS_FILE, b)
                st.rerun()

    if st.session_state.banco_notas:
        for ch, nt in list(st.session_state.banco_notas.items()):
            p = ch.split('|')
            c_o, c_e, c_d = st.columns([2, 2, 1])
            c_o.markdown(f"⚠️ **{nt}**")
            c_e.write(f"📍 {p[0]}, {p[1]} {p[2]}")
            if c_d.button("🗑️", key=f"del_{ch}"):
                b = carregar_dados(OBS_FILE)
                if ch in b: del b[ch]
                salvar_dados(OBS_FILE, b)
                st.rerun()

with tab3:
    st.subheader("🏢 Agrupar Condomínios")
    condos_db = carregar_dados(COND_FILE)
    col_add, col_list = st.columns([1, 1])
    
    with col_add:
        st.markdown("### 1. Adicionar ao Grupo")
        e_plan = st.selectbox("Escolher da Planilha:", ["-- Selecione --"] + st.session_state.enderecos_planilha, key="c_plan")
        e_manu = st.text_input("OU Digitar Manualmente (Rua, Número):", key="c_manu").upper().strip()
        
        if st.button("➕ Incluir na Lista"):
            alvo = e_plan if e_plan != "-- Selecione --" else e_manu
            if alvo:
                limpo = limpar_para_condominio(alvo)
                if limpo not in st.session_state.temp_condo_list:
                    st.session_state.temp_condo_list.append(limpo)
                    st.rerun()

        if st.session_state.temp_condo_list:
            voto_principal = ""
            for i, addr in enumerate(st.session_state.temp_condo_list):
                c1, c2 = st.columns([4, 1])
                if c1.checkbox(f"{addr}", key=f"check_c_{i}"): voto_principal = addr
                if c2.button("❌", key=f"del_tmp_{i}"):
                    st.session_state.temp_condo_list.remove(addr)
                    st.rerun()
            
            if st.button("💾 Salvar Grupo de Condomínio"):
                if voto_principal and len(st.session_state.temp_condo_list) >= 2:
                    condos_db[voto_principal] = [a for a in st.session_state.temp_condo_list if a != voto_principal]
                    salvar_dados(COND_FILE, condos_db)
                    st.session_state.temp_condo_list = []
                    st.rerun()

    with col_list:
        st.markdown("### 2. Grupos Cadastrados")
        for princ, outros in list(condos_db.items()):
            with st.expander(f"🏢 Portaria: {princ}"):
                for o in outros: st.write(f"🏠 {o}")
                if st.button("Remover Grupo", key=f"del_g_{princ}"):
                    del condos_db[princ]
                    salvar_dados(COND_FILE, condos_db)
                    st.rerun()

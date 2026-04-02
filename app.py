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
    """Normaliza o endereço para comparação de grupos de condomínio."""
    if not texto: return ""
    t = str(texto).upper().strip()
    # 1. Remove números repetidos (ex: 150, 150 -> 150)
    t = re.sub(r'(\d+),\s*\1', r'\1', t)
    # 2. Padroniza separadores e remove excesso de espaços
    t = t.replace(',', ' ').replace('  ', ' ')
    # 3. Remove complementos comuns para focar na base (Rua + Número)
    t = re.split(r'\b(APT|APTO|AP|APARTAMENTO|BLOCO|BL|SL|SALA|FUNDOS|CASA|A\d+|B\d+|C\d+|D\d+|E\d+)\b', t)[0]
    return t.strip()

def padronizar_complemento(texto):
    if not texto: return ""
    t = str(texto).upper().strip()
    t = re.sub(r'\b(APARTAMENTO|APTO|APT|AP)\b', 'AP', t)
    t = re.sub(r'\b(BLOCO|BL)\b', 'BL', t)
    t = t.replace('.', '').replace('  ', ' ')
    return t

def extrair_numero(texto):
    if pd.isna(texto): return ""
    # Tenta pegar o primeiro número que aparece após um espaço ou vírgula
    match = re.search(r'(?:,|\s)(\d+)', str(texto))
    return match.group(1) if match else ""

def extrair_complemento_puro(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper()
    match = re.search(r'(APT|APTO|AP|APARTAMENTO|BLOCO|BL|SL|SALA|FUNDOS|CASA\s\d+|AP\s\d+|[A-Z]\d+).*', t)
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
                
                def converter_para_principal(addr):
                    addr_limpo = limpar_para_condominio(addr)
                    for principal, lista_membros in condos_db.items():
                        p_limpo = limpar_para_condominio(principal)
                        # Se a base do condomínio está contida no endereço da planilha
                        if p_limpo in addr_limpo:
                            return principal
                        for m in lista_membros:
                            if limpar_para_condominio(m) in addr_limpo:
                                return principal
                    return addr
                
                df['Addr_Final'] = df['Destination Address'].apply(converter_para_principal)
                df['Num_Casa'] = df['Addr_Final'].apply(extrair_numero)
                df['Rua_Base'] = df['Addr_Final'].apply(normalizar_rua)
                df['Comp_Padrao'] = df['Addr_Final'].apply(extrair_complemento_puro).apply(padronizar_complemento)
                
                # Agrupamento
                group_ids = np.zeros(len(df))
                curr = 1
                for i in range(len(df)):
                    if group_ids[i] == 0:
                        group_ids[i] = curr
                        for j in range(i + 1, len(df)):
                            if df.iloc[i]['Addr_Final'] == df.iloc[j]['Addr_Final']:
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

                def aplicar_formatacao(row):
                    texto_seq = formatar_sequencia_visual(row['Sequence'])
                    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
                    for ch, nt in notas_vivas.items():
                        pts = ch.split('|')
                        if len(pts) == 3 and n_p == pts[1] and c_p == pts[2] and SequenceMatcher(None, r_p, pts[0]).ratio() > 0.8:
                            return f"⚠️ {nt} | {texto_seq}"
                    return texto_seq

                df_f['Sequence'] = df_f.apply(aplicar_formatacao, axis=1)
                cols_f = ['Sequence', 'Destination Address', 'Bairro', 'City', 'Zipcode/Postal code', 'Latitude', 'Longitude']
                
                st.success("✅ Concluído!")
                st.dataframe(df_f[cols_f])
                
                nome_f = f"Entrega {arquivo.name.split('.')[0]} {datetime.now().strftime('%d-%m-%Y')}.csv"
                st.download_button("📥 Baixar Planilha", df_f[cols_f].to_csv(index=False).encode('utf-8-sig'), nome_f, "text/csv")

with tab2:
    st.session_state.banco_notas = carregar_dados(OBS_FILE)
    st.subheader("📝 Gerenciar Notas")
    end_sel = st.selectbox("📍 Buscar da Planilha:", ["-- Selecione --"] + st.session_state.enderecos_planilha, key="s_notas")
    rua_s = normalizar_rua(end_sel) if end_sel != "-- Selecione --" else ""
    num_s = extrair_numero(end_sel) if end_sel != "-- Selecione --" else ""
    comp_s = extrair_complemento_puro(end_sel) if end_sel != "-- Selecione --" else ""

    with st.form("f_notas", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        r_in = c1.text_input("Rua", value=rua_s).upper().strip()
        n_in = c2.text_input("Número", value=num_s).strip()
        cp_in = c3.text_input("Comp (AP)", value=comp_s).upper().strip()
        obs_in = st.text_input("Nota / Observação")
        if st.form_submit_button("➕ Salvar Nota"):
            if r_in and n_in and obs_in:
                b = carregar_dados(OBS_FILE)
                b[f"{r_in}|{n_in}|{padronizar_complemento(cp_in)}"] = obs_in
                salvar_dados(OBS_FILE, b)
                st.rerun()

    if st.session_state.banco_notas:
        st.divider()
        for ch, nt in list(st.session_state.banco_notas.items()):
            p = ch.split('|')
            col_obs, col_end, col_del = st.columns([2, 2, 1])
            col_obs.markdown(f"⚠️ **{nt}**")
            col_end.write(f"📍 {p[0]}, {p[1]} {p[2] if len(p)>2 else ''}")
            if col_del.button("🗑️", key=f"d_obs_{ch}"):
                b = carregar_dados(OBS_FILE)
                if ch in b: del b[ch]
                salvar_dados(OBS_FILE, b)
                st.rerun()

with tab3:
    st.subheader("🏢 Agrupar Condomínios")
    st.info("Digite ou selecione endereços para agrupá-los na mesma portaria. Complementos são ignorados aqui.")
    condos_db = carregar_dados(COND_FILE)
    
    c_add, c_list = st.columns([1, 1])
    with c_add:
        st.markdown("### 1. Criar Grupo")
        e_plan = st.selectbox("Da Planilha:", ["-- Selecione --"] + st.session_state.enderecos_planilha, key="c_plan")
        e_manu = st.text_input("Manual (Rua, Número):", key="c_manu").upper().strip()
        
        if st.button("➕ Adicionar à Lista"):
            alvo = e_plan if e_plan != "-- Selecione --" else e_manu
            if alvo:
                limpo = limpar_para_condominio(alvo)
                if limpo not in st.session_state.temp_condo_list:
                    st.session_state.temp_condo_list.append(limpo)
                    st.rerun()
        
        if st.session_state.temp_condo_list:
            st.write("---")
            principal_voto = ""
            for i, addr in enumerate(st.session_state.temp_condo_list):
                col1, col2 = st.columns([4, 1])
                if col1.checkbox(f"{addr}", key=f"ck_c_{i}"): principal_voto = addr
                if col2.button("❌", key=f"dt_c_{i}"):
                    st.session_state.temp_condo_list.remove(addr)
                    st.rerun()
            
            if st.button("💾 Salvar Grupo"):
                if principal_voto and len(st.session_state.temp_condo_list) >= 2:
                    condos_db[principal_voto] = [a for a in st.session_state.temp_condo_list if a != principal_voto]
                    salvar_dados(COND_FILE, condos_db)
                    st.session_state.temp_condo_list = []
                    st.success("Grupo Salvo!")
                    st.rerun()
                else: st.warning("Selecione a portaria principal e tenha pelo menos 2 endereços.")

    with c_list:
        st.markdown("### 2. Grupos Ativos")
        for princ, outros in list(condos_db.items()):
            with st.expander(f"🏢 Portaria: {princ}"):
                for o in outros: st.write(f"🏠 {o}")
                if st.button("Excluir Grupo", key=f"dg_c_{princ}"):
                    del condos_db[princ]
                    salvar_dados(COND_FILE, condos_db)
                    st.rerun()

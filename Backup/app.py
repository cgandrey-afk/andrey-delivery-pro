import streamlit as st
import pandas as pd
from datetime import datetime
from funcoes import (
    carregar_obs,
    carregar_json,
    processar_agrupamento,
    aplicar_formatacao_final,
    CONDO_FILE
)

# Configuração inicial
st.set_page_config(page_title="Gerenciador de Rotas", layout="wide", page_icon="🚚")

if 'enderecos_planilha' not in st.session_state:
    st.session_state.enderecos_planilha = []

st.title("🚚 Gerenciador de Rotas")

tab1, tab2, tab3 = st.tabs([
    "📋 Processar Planilha",
    "📝 Gerenciar Notas",
    "🏢 Condomínios Agrupados"
])

with tab1:
    arquivo = st.file_uploader(
        "1. Carregar Planilha",
        type=['xlsx', 'csv'],
        key="up_v5"
    )

    if arquivo:
        # Leitura da planilha
        if arquivo.name.endswith('.csv'):
            df_temp = pd.read_csv(arquivo, sep=None, engine='python')
        else:
            df_temp = pd.read_excel(arquivo)

        # Atualiza endereços da sessão para a aba de notas
        if 'Destination Address' in df_temp.columns:
            novos = sorted(df_temp['Destination Address'].unique().tolist())
            if novos != st.session_state.enderecos_planilha:
                st.session_state.enderecos_planilha = novos
                st.rerun()

        # 🔥 Botão de Processamento - AGORA MAIS SIMPLES
        if st.button("🚀 Processar e Agrupar AGORA"):
            with st.spinner("Processando rotas e agrupando condomínios..."):
                notas_vivas = carregar_obs()
                db_condos = carregar_json(CONDO_FILE)

                # Todas as regras de Bloco, Condomínio e Formatação de Endereço 
                # acontecem dentro desta função no funcoes.py
                df_f = processar_agrupamento(df_temp, notas_vivas, db_condos)

                # Define as colunas que você quer ver no CSV final e na tela
                cols_final = [
                    'Sequence',
                    'Destination Address',
                    'Bairro',
                    'City',
                    'Zipcode/Postal code',
                    'Latitude',
                    'Longitude'
                ]

                st.success("✅ Processamento concluído!")
                
                # Exibe o resultado na tela
                st.dataframe(df_f[cols_final], use_container_width=True)

                # Preparação do Download
                data_str = datetime.now().strftime("%d-%m-%Y")
                nome_base = arquivo.name.split('.')[0]
                nome_final = f"Entregas {data_str} {nome_base}.csv"
                
                # utf-8-sig para o Excel abrir com acentos e ícones corretamente
                csv = df_f[cols_final].to_csv(index=False).encode('utf-8-sig')

                st.download_button(
                    label="📥 Baixar Planilha para Roteirizador",
                    data=csv,
                    file_name=nome_final,
                    mime="text/csv"
                )

with tab2:
    import interface_notas
    interface_notas.mostrar_aba_notas()

with tab3:
    import interface_condos
    interface_condos.mostrar_aba_condos()
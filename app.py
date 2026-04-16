import streamlit as st
import pandas as pd
from datetime import datetime
from funcoes import carregar_dados_fluxoderotas, processar_agrupamento
from interface_sidebar import mostrar_sidebar
from interface_condos import mostrar_aba_condos
from interface_notas import mostrar_aba_notas

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Fluxo de Rotas - Campinas",
    initial_sidebar_state="collapsed", 
    layout="wide",
    page_icon="🚚"
)



# --- 3. GERADOR DE ID DE SESSÃO ---
if 'id_sessao' not in st.session_state:
    st.session_state.id_sessao = datetime.now().timestamp()
    st.session_state.mostrar_form = False  
    if 'logado' not in st.session_state:
        st.session_state.logado = False

# --- 4. INTERFACE LATERAL ---
aba_selecionada = mostrar_sidebar()

# --- 5. BANNERS INFORMATIVOS ---
if not st.session_state.get('logado'):
    st.markdown("""
        <div style="background: linear-gradient(90deg, #ff4b4b 0%, #ff8585 100%); padding: 10px 20px; border-radius: 12px; color: white; display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 4px solid #fff;">
            <div style="flex: 1; text-align: left;">
                <h2 style='margin: 0; font-size: 17px;'>🚀 Desbloqueie o Poder Total!</h2>
                <p style='margin: 0; font-size: 13px; opacity: 0.9;'>Sincronize <b>Notas</b> e <b>Condomínios</b> na nuvem via menu lateral.</p>
            </div>
            <div style="margin-left: 15px;">
                <span style='background: rgba(255, 255, 255, 0.2); color: white; padding: 5px 12px; border-radius: 10px; border: 1px solid white; font-weight: bold; font-size: 11px; text-transform: uppercase; white-space: nowrap;'>⬅️ ACESSE O MENU LATERAL</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="text-align: right; margin-bottom: 5px;">
            <span style="color: #28a745; font-size: 11px; font-weight: bold;">✅ Sincronização Ativa</span>
        </div>
    """, unsafe_allow_html=True)

# --- 6. NAVEGAÇÃO ---
if st.session_state.get("pagina_atual") == "cadastro":
    #Esse mostra a tela de cadastro
    #from criacao_conta import mostrar_tela_cadastro 
    #mostrar_tela_cadastro()
    # Esse mostra a tela de manuençao ao inves de cadastro
    from manutencao import mostrar_tela_manutencao 
    mostrar_tela_manutencao()
else:
    # ABA 1: INÍCIO
    if aba_selecionada == "🏠 Início" or aba_selecionada is None:
        st.title("🚀 Processamento de Rotas")
        arquivo = st.file_uploader("1. Carregar Planilha da Shopee", type=['xlsx', 'csv'], key="up_v5")

        if arquivo:
            df_temp = pd.read_csv(arquivo, sep=None, engine='python') if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)

            if st.button("🚀 Processar e Agrupar AGORA", type="primary", use_container_width=True):
                with st.spinner("Otimizando rotas..."):
                    notas_vivas = carregar_dados_fluxoderotas("observacoes")
                    db_condos = carregar_dados_fluxoderotas("condominios")
                    df_f = processar_agrupamento(df_temp, notas_vivas, db_condos)

                    cols_final = ['Sequence', 'Destination Address', 'Bairro', 'City', 'Zipcode/Postal code', 'Latitude', 'Longitude']
                    st.success("✅ Processamento concluído!")
                    st.dataframe(df_f[cols_final], use_container_width=True)

                    csv = df_f[cols_final].to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Baixar Planilha para Roteirizador",
                        data=csv,
                        file_name=f"Entregas_{datetime.now().strftime('%d-%m-%Y')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

    # ABA 2: NOTAS
    elif aba_selecionada == "📝 Gerenciar Notas":
        if st.session_state.get('logado'):
            mostrar_aba_notas()
        else:
            st.error("### 🔒 Acesso Negado")
            st.info("O banco de notas é um recurso restrito. Faça login na barra lateral.")

    # ABA 3: CONDOMÍNIOS
    elif aba_selecionada == "🏢 Condomínios":
        if st.session_state.get('logado'):
            mostrar_aba_condos()
        else:
            st.error("### 🔒 Acesso Negado")
            st.info("O cadastro de portarias é restrito. Faça login na barra lateral.")
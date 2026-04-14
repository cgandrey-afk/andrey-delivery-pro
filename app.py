import streamlit as st
import pandas as pd
from datetime import datetime
from funcoes import (
    carregar_dados_fluxoderotas,  # Chamada da nuvem
    processar_agrupamento,
    aplicar_formatacao_final
)

# --- CONFIGURAÇÃO DA PÁGINA (Inicia minimizado com 'collapsed') ---
st.set_page_config(
    page_title="Fluxo de Rotas", 
    layout="wide", 
    initial_sidebar_state="collapsed" # <-- ISSO FAZ ELE INICIAR FECHADO
)

# --- CSS PARA O PERFIL E BOTÃO VERMELHO ---
st.markdown("""
    <style>
    /* Estilo do Perfil no Menu Lateral */
    .user-profile {
        display: flex;
        align-items: center;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
    }
    .user-photo {
        width: 55px;
        height: 55px;
        border-radius: 50%; /* Faz o círculo */
        object-fit: cover;
        margin-right: 15px;
        border: 2px solid #ff4b4b;
    }
    .user-info {
        display: flex;
        flex-direction: column;
    }
    .user-name {
        font-weight: bold;
        color: #31333F;
        font-size: 16px;
    }
    .user-status {
        font-size: 12px;
        color: #28a745;
    }

    /* Forçar Botão de Processamento em Vermelho */
    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DO MENU LATERAL (DRAWER) ---
with st.sidebar:
    st.title("⚙️ Configurações")
    
    if 'logado' not in st.session_state:
        st.session_state.logado = False
    if 'mostrar_form' not in st.session_state:
        st.session_state.mostrar_form = False

    if st.session_state.logado:
        # --- PERFIL LOGADO ---
        foto_url = "https://www.w3schools.com/howto/img_avatar.png" 
        st.markdown(f"""
            <div class="user-profile">
                <img src="{foto_url}" class="user-photo">
                <div class="user-info">
                    <span class="user-name">Andrey Junior</span>
                    <span class="user-status">● Online</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Sair da Conta", use_container_width=True):
            st.session_state.logado = False
            st.session_state.mostrar_form = False
            st.rerun()

    elif st.session_state.mostrar_form:
        # --- FORMULÁRIO DE LOGIN ---
        st.markdown("### 🔐 Entrar na Conta")
        
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("ENTRAR", use_container_width=True)
            
            if submit:
                # Aqui você valida a senha (exemplo simples)
                if user == "admin" and password == "123":
                    st.session_state.logado = True
                    st.session_state.mostrar_form = False
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")

        st.markdown("<p style='text-align: center;'>ou</p>", unsafe_allow_html=True)
        
        # Botão Google (Visualmente diferente)
        if st.button("🔵 Fazer login com Google", use_container_width=True):
            st.info("Conectando ao Google API...")
            # Lógica de integração Google iria aqui
            
        if st.button("⬅️ Voltar"):
            st.session_state.mostrar_form = False
            st.rerun()

    else:
        # --- TELA INICIAL DO MENU (DESLOGADO) ---
        st.info("Acesse sua conta para sincronizar dados.")
        if st.button("🔑 Fazer Login", type="primary", use_container_width=True):
            st.session_state.mostrar_form = True
            st.rerun()

    st.divider()
    st.write("🔧 **Preferências do App**")
    st.toggle("Modo de Alta Precisão (GPS)")
    st.caption("Versão 5.3.0 - Campinas/SP")

# --- O RESTO DO SEU APP CONTINUA ABAIXO ---
# tab1, tab2 = st.tabs(["🚀 Processamento", "🏢 Condomínios"])
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
    # Mantemos o CSS para o botão vermelho, mas ajustamos para não forçar largura total 
    # a menos que você queira. Removi o 'width: 100%' para ele respeitar o alinhamento natural.
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #ff4b4b;
            color: white;
            border: none;
            font-weight: bold;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #ff1a1a;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)

    arquivo = st.file_uploader("1. Carregar Planilha", type=['xlsx', 'csv'], key="up_v5")

    if arquivo:
        if arquivo.name.endswith('.csv'):
            df_temp = pd.read_csv(arquivo, sep=None, engine='python')
        else:
            df_temp = pd.read_excel(arquivo)

        if 'Destination Address' in df_temp.columns:
            novos = sorted(df_temp['Destination Address'].unique().tolist())
            if novos != st.session_state.enderecos_planilha:
                st.session_state.enderecos_planilha = novos
                st.rerun()

        # Botão alinhado à esquerda (padrão)
        if st.button("🚀 Processar e Agrupar AGORA", type="primary"):
            with st.spinner("Buscando dados na nuvem e processando rotas..."):
                notas_vivas = carregar_dados_fluxoderotas("observacoes")
                db_condos = carregar_dados_fluxoderotas("condominios")

                df_f = processar_agrupamento(df_temp, notas_vivas, db_condos)

                cols_final = [
                    'Sequence', 'Destination Address', 'Bairro', 
                    'City', 'Zipcode/Postal code', 'Latitude', 'Longitude'
                ]

                st.success("✅ Processamento concluído!")
                
                # Tabela pegando a tela toda (use_container_width=True)
                st.dataframe(df_f[cols_final], use_container_width=True)

                data_str = datetime.now().strftime("%d-%m-%Y")
                nome_base = arquivo.name.split('.')[0]
                nome_final = f"Entregas {data_str} {nome_base}.csv"
                
                csv = df_f[cols_final].to_csv(index=False).encode('utf-8-sig')

                st.download_button(
                    label="📥 Baixar Planilha para Roteirizador",
                    data=csv,
                    file_name=nome_final,
                    mime="text/csv",
                    use_container_width=True # Botão de download também largo para facilitar
                )
                
                
with tab2:
    import interface_notas
    interface_notas.mostrar_aba_notas()

with tab3:
    import interface_condos
    interface_condos.mostrar_aba_condos()

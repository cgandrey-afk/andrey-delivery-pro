import streamlit as st
import pandas as pd
from datetime import datetime
from funcoes import (
    carregar_dados_fluxoderotas,
    processar_agrupamento,
    aplicar_formatacao_final

)
from interface_condos import mostrar_aba_condos
from interface_notas import mostrar_aba_notas

# --- 1. CONFIGURAÇÃO DA PÁGINA (Sempre o primeiro comando) ---
st.set_page_config(
    page_title="Gerenciador de Rotas", 
    layout="wide", 
    page_icon="🚚",
    initial_sidebar_state="collapsed"
)

# --- 2. INICIALIZAÇÃO DO SESSION STATE ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'mostrar_form' not in st.session_state:
    st.session_state.mostrar_form = False
if 'enderecos_planilha' not in st.session_state:
    st.session_state.enderecos_planilha = []

# --- 3. CSS CUSTOMIZADO (Perfil, Botão Vermelho e Layout) ---
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
        border-radius: 50%;
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

    /* Botão Primário Vermelho */
    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        border: none;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #ff1a1a;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR (MENU LATERAL / DRAWER) ---
with st.sidebar:
    st.title("⚙️ Configurações")
    
    if st.session_state.logado:
        # Perfil do Usuário Logado
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
        # Formulário de Login
        st.markdown("### 🔐 Entrar na Conta")
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("ENTRAR", use_container_width=True)
            
            if submit:
                # Validação simples (Substituir por sua lógica real se necessário)
                if user == "admin" and password == "123":
                    st.session_state.logado = True
                    st.session_state.mostrar_form = False
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")

        st.markdown("<p style='text-align: center; margin:0;'>ou</p>", unsafe_allow_html=True)
        
        if st.button("🔵 Fazer login com Google", use_container_width=True):
            st.info("Conectando ao Google API...")
            
        if st.button("⬅️ Voltar"):
            st.session_state.mostrar_form = False
            st.rerun()

    else:
        # Tela Deslogada
        st.info("Acesse sua conta para sincronizar dados.")
        if st.button("🔑 Fazer Login", type="primary", use_container_width=True):
            st.session_state.mostrar_form = True
            st.rerun()

    st.divider()
    st.write("🔧 **Preferências do App**")
    st.toggle("Modo de Alta Precisão (GPS)")
    st.caption("Versão 5.3.0 - Campinas/SP")

# --- 5. CONTEÚDO PRINCIPAL ---
st.title("🚚 Gerenciador de Rotas")

tab1, tab2, tab3 = st.tabs(["🚀 Processamento", "🏢 Condomínios", "📝 Notas"])

# --- ABA 1: PROCESSAMENTO ---
with tab1:
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

        if st.button("🚀 Processar e Agrupar AGORA", type="primary"):
            with st.spinner("Buscando dados na nuvem e processando rotas..."):
                # Busca dados no Firestore através das funções importadas
                notas_vivas = carregar_dados_fluxoderotas("observacoes")
                db_condos = carregar_dados_fluxoderotas("condominios")

                df_f = processar_agrupamento(df_temp, notas_vivas, db_condos)

                cols_final = [
                    'Sequence', 'Destination Address', 'Bairro', 
                    'City', 'Zipcode/Postal code', 'Latitude', 'Longitude'
                ]

                st.success("✅ Processamento concluído!")
                st.dataframe(df_f[cols_final], use_container_width=True)

                # Preparação do arquivo para Download
                data_str = datetime.now().strftime("%d-%m-%Y")
                nome_base = arquivo.name.split('.')[0]
                nome_final = f"Entregas {data_str} {nome_base}.csv"
                
                csv = df_f[cols_final].to_csv(index=False).encode('utf-8-sig')

                st.download_button(
                    label="📥 Baixar Planilha para Roteirizador",
                    data=csv,
                    file_name=nome_final,
                    mime="text/csv",
                    use_container_width=True
                )

# --- ABA 2: CONDOMÍNIOS (PROTEGIDA) ---
with tab2:
    if st.session_state.logado:
        mostrar_aba_condos()
    else:
        st.warning("### 🔒 Acesso Restrito")
        st.info("Para gerenciar o cadastro de condomínios na nuvem, você precisa estar logado.")
        if st.button("Ir para Login", key="btn_login_condo"):
            st.info("Clique no ícone de 3 linhas no canto superior esquerdo para entrar.")

# --- ABA 3: NOTAS/OBSERVAÇÕES ---
with tab3:
    if st.session_state.logado:
        # Chama a interface completa com checkboxes e campo de endereço único
        mostrar_aba_notas()
    else:
        st.warning("### 🔒 Acesso Restrito")
        st.info("O banco de observações só pode ser editado por usuários autenticados.")
        if st.button("Ir para Login", key="btn_login_notas"):
            st.info("Clique no ícone de 3 linhas no canto superior esquerdo para entrar.")

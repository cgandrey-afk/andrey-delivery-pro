import streamlit as st
import extra_streamlit_components as stx
import time

def mostrar_sidebar():
    # 1. Inicializa o gerenciador de cookies
    cookie_manager = stx.CookieManager(key="cookie_manager_andrey")

    # --- LÓGICA DE RESET NO F5 ---
    if "carregamento_limpo" not in st.session_state:
        st.session_state.mostrar_form = False
        st.session_state.logout_feito = False
        st.session_state.carregamento_limpo = True

    # --- 2. RECUPERAÇÃO AUTOMÁTICA (COOKIE) ---
    logado = st.session_state.get('logado', False)
    logout_feito = st.session_state.get('logout_feito', False)

    if not logado and not logout_feito:
        token = cookie_manager.get(cookie="auth_fluxo")
        if token is None:
            time.sleep(0.5)  # Aumente de 0.1 para 0.5 para dar tempo no celular
            token = cookie_manager.get(cookie="auth_fluxo")
            
        if token == "admin_validado":
            st.session_state.logado = True
            st.rerun()

    with st.sidebar:
        st.title("🚚 Fluxo de Rotas")

        if st.session_state.get('logado'):
            # --- INTERFACE LOGADO ---
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
                    <img src="https://www.w3schools.com/howto/img_avatar.png" style="width: 50px; border-radius: 50%;">
                    <div>
                        <p style="margin: 0; font-weight: bold; color: black; font-size: 15px;">Andrey Junior</p>
                        <p style="margin: 0; font-size: 12px; color: green;">● Online</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            menu = st.radio("Navegação", ["🏠 Início", "📝 Gerenciar Notas", "🏢 Condomínios"])
            
            st.divider()
            
            if st.button("Sair da Conta", use_container_width=True):
                st.session_state.logout_feito = True
                st.session_state.logado = False
                cookie_manager.delete("auth_fluxo", key="sair_definitivo")
                st.info("Desconectando...")
                time.sleep(0.5)
                st.rerun()

        elif st.session_state.get('mostrar_form'):
            # --- INTERFACE FORMULÁRIO DE LOGIN ---
            st.markdown("### 🔐 Entrar na Conta")
            id_f = st.session_state.get('id_sessao', 'fixo')
            
            with st.form(key=f"form_login_{id_f}"):
                user = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                submit = st.form_submit_button("ENTRAR", use_container_width=True)
                
                if submit:
                    if user == "admin" and password == "123":
                        cookie_manager.set("auth_fluxo", "admin_validado", key="save_v1")
                        st.session_state.logado = True
                        st.session_state.mostrar_form = False
                        st.session_state.logout_feito = False
                        st.success("Login realizado!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos")

            if st.button("⬅️ Voltar"):
                st.session_state.mostrar_form = False
                st.rerun()
            menu = "🏠 Início"

        else:
            # --- INTERFACE DESLOGADO (LOGIN E CADASTRO) ---
            st.info("Acesse sua conta para sincronizar dados.")
            id_btn = st.session_state.get('id_sessao', 'fixo')
            
            if st.button("🔑 Fazer Login", type="primary", use_container_width=True, key=f"btn_login_{id_btn}"):
                st.session_state.mostrar_form = True
                st.rerun()

            if st.button("📝 Criar Conta", use_container_width=True, key=f"btn_criar_{id_btn}"):
                st.session_state.pagina_atual = "cadastro"
                st.rerun()
                
            menu = "🏠 Início"

        st.divider()
        st.write("🔧 **Preferências**")
        st.toggle("Modo Alta Precisão", key="toggle_precisao")
        st.caption("Versão 5.3.0 - Campinas/SP")
        
    return menu

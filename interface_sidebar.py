import streamlit as st
import extra_streamlit_components as stx
import time
import datetime 
from datetime import timedelta

def mostrar_sidebar():
    cookie_manager = stx.CookieManager(key="cookie_manager_andrey")

    # --- NOVO SPLASH RESISTENTE AO F5 ---
    if not st.session_state.get('logado'):
        placeholder_loading = st.empty()
        
        # O HTML abaixo garante que a tela não fique "preta" ou vazia
        with placeholder_loading.container():
            st.markdown("""
                <div style='height: 80vh; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                    <h2 style='color: #ff4b4b; margin-bottom: 10px;'>🚚 Fluxo de Rotas</h2>
                    <div style='border: 4px solid #f3f3f3; border-top: 4px solid #ff4b4b; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite;'></div>
                    <p style='margin-top: 15px; color: #666;'>Sincronizando com a nuvem...</p>
                    <style>
                        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                </div>
            """, unsafe_allow_html=True)

        # Loop de verificação
        for tentativa in range(4): # Aumentei para 4 para dar mais margem no F5
            token = cookie_manager.get(cookie="auth_fluxo")
            if token:
                from funcoes import db
                try:
                    doc = db.collection("usuarios").document(token).get()
                    if doc.exists:
                        dados = doc.to_dict()
                        st.session_state.logado = True
                        st.session_state.usuario_nome = dados.get('nome')
                        st.session_state.nivel_acesso = dados.get('nivel', 'usuario')
                        st.session_state.pagina_atual = "home"
                        placeholder_loading.empty()
                        st.rerun()
                        break 
                except:
                    pass
            time.sleep(0.5) 

        # Se após as tentativas não logar, limpa o splash para mostrar os botões de login
        placeholder_loading.empty()

    # --- LÓGICA DE RESET NO F5 ---
    if "carregamento_limpo" not in st.session_state:
        st.session_state.mostrar_form = False
        st.session_state.logout_feito = False
        st.session_state.carregamento_limpo = True

    with st.sidebar:
        st.title("🚚 Fluxo de Rotas")

        if st.session_state.get('logado'):
            # --- INTERFACE LOGADO ---
            nome_user = st.session_state.get('usuario_nome', 'Motorista')
            nivel = st.session_state.get('nivel_acesso', 'usuario')
            cor_status = "blue" if nivel == "admin" else "green"
            label_status = "● Administrador" if nivel == "admin" else "● Online"

            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
                    <img src="https://www.w3schools.com/howto/img_avatar.png" style="width: 50px; border-radius: 50%;">
                    <div>
                        <p style="margin: 0; font-weight: bold; color: black; font-size: 15px;">{nome_user}</p>
                        <p style="margin: 0; font-size: 12px; color: {cor_status};">{label_status}</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            menu = st.radio("Navegação", ["🏠 Início", "📝 Gerenciar Notas", "🏢 Condomínios"])
            st.divider()
            
            # Criamos um espaço vazio para mensagens de status da sidebar
            status_logout = st.empty()

            if st.button("Sair da Conta", use_container_width=True):
                # 1. FEEDBACK VISUAL IMEDIATO (Para o celular não parecer travado)
                status_logout.markdown("""
                    <div style='text-align: center; padding: 10px; background-color: #ffebee; border-radius: 5px;'>
                        <p style='color: #c62828; margin: 0; font-weight: bold;'>Encerrando sessão...</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # 2. Limpa a memória interna
                st.session_state.logado = False
                st.session_state.usuario_nome = None
                st.session_state.logout_feito = True
                st.session_state.pagina_atual = "home"
                
                # 3. Deleta o cookie
                cookie_manager.delete("auth_fluxo")
                
                # 4. Espera o tempo necessário para o Chrome processar
                time.sleep(1.2)
                
                # 5. Força a atualização final
                st.rerun()

        elif st.session_state.get('mostrar_form'):
            # --- FORMULÁRIO DE LOGIN ---
            st.markdown("### 🔐 Entrar na Conta")
            with st.form(key="form_login_final"):
                user_email = st.text_input("E-mail").lower().strip()
                password = st.text_input("Senha", type="password")
                submit = st.form_submit_button("ENTRAR", use_container_width=True)
                
                if submit:
                    from funcoes import db, criptografar_senha
                    email_limpo = user_email.lower().strip()
                    senha_limpa = password.strip()
                    try:
                        user_ref = db.collection("usuarios").document(email_limpo)
                        doc = user_ref.get()
                        if doc.exists:
                            dados = doc.to_dict()
                            if criptografar_senha(senha_limpa) == dados.get('senha'):
                                # Grava Cookie e Sessão
                                validade = datetime.datetime.now() + datetime.timedelta(days=30)
                                cookie_manager.set("auth_fluxo", email_limpo, expires_at=validade)
                                
                                st.session_state.logado = True
                                st.session_state.usuario_nome = dados.get('nome')
                                st.session_state.nivel_acesso = dados.get('nivel', 'usuario')
                                st.session_state.mostrar_form = False
                                st.session_state.pagina_atual = "home"
                                
                                st.success("✅ Autenticado!")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                        else:
                            st.error("Usuário não encontrado.")
                    except Exception as e:
                        st.error(f"Erro técnico: {e}")

            if st.button("⬅️ Voltar"):
                st.session_state.mostrar_form = False
                st.rerun()
            menu = "🏠 Início"

        else:
            # --- INTERFACE DESLOGADO ---
            st.info("Acesse sua conta para sincronizar dados.")
            if st.button("🔑 Fazer Login", type="primary", use_container_width=True):
                st.session_state.mostrar_form = True
                st.rerun()

            if st.button("📝 Criar Conta", use_container_width=True):
                st.session_state.pagina_atual = "cadastro"
                st.rerun()
            menu = "🏠 Início"

        st.divider()
        st.caption("Versão 5.6.0 - Campinas/SP")
        
    return menu

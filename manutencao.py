import streamlit as st
import time
import random

def mostrar_tela_manutencao():
    # --- CSS PARA ANIMAÇÃO DE CORES NA BARRA ---
    # --- CSS CORRIGIDO ---
    st.markdown("""
        <style>
            @keyframes colorChange {
                0% { background-color: #007bff; }   /* Azul Padrão */
                50% { background-color: #00d4ff; }  /* Azul Piscina */
                100% { background-color: #007bff; } /* Volta */
            }

            /* Seletor Universal para a barra de progresso do Streamlit */
            .stProgress > div > div > div > div {
                animation: colorChange 3s infinite ease-in-out !important;
            }

            /* Efeito de pulsação no texto */
            .construcao-msg {
                text-align: center;
                color: #007bff;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.3; }
                100% { opacity: 1; }
            }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.write("")
        st.title("🏗️ Área em Manutenção")
        
        # --- LÓGICA DA BARRA (CARREGA ATÉ 95%) ---
        progresso_texto = st.empty()
        barra_progresso = st.progress(0)

        if "progresso_v5" not in st.session_state:
            percentual = 0
            while percentual < 95:
                salto = random.randint(1, 4)
                percentual += salto
                if percentual > 95: percentual = 95
                
                barra_progresso.progress(percentual)
                progresso_texto.caption(f"🔵 Otimizando módulos... {percentual}%")
                time.sleep(random.uniform(0.01, 0.08))
            st.session_state.progresso_v5 = 95
        else:
            barra_progresso.progress(95)
            progresso_texto.caption("🔵 Módulos em fase de homologação... 95%")

        # --- CONTEÚDO ---
        st.warning("O sistema de cadastro está sendo finalizado.")
        
        st.markdown("""
            ### 🚧 O Futuro do Fluxo de Rotas
            **O que você poderá fazer aqui:**
            * 👤 **Perfil Profissional:** Gestão de motorista e veículo.
            * 📝 **Notas Inteligentes:** Observações fixas por endereço.
            * 🏢 **Gestão de Condomínios:** Portarias centrais, blocos e logradouros internos.
            * 📍 **Roteirizador Nativo:** Independência total de apps externos.
        """)
        
        st.markdown('<div class="construcao-msg">🛠️ FINALIZANDO ÚLTIMOS AJUSTES...</div>', unsafe_allow_html=True)
        
        st.divider()

        # --- BOTÃO DE VOLTAR (DENTRO DA FUNÇÃO) ---
        if st.button("⬅️ Voltar para a Página Inicial", use_container_width=True, type="primary"):
            st.session_state.pagina_atual = "home"
            # Limpa o estado para a barra animar de novo na próxima visita
            if "progresso_v5" in st.session_state:
                del st.session_state.progresso_v5
            st.rerun()

        
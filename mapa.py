import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import pandas as pd
import time

def mostrar_aba_mapa(df):
    st.subheader("📍 Roteiro Interativo")
    
    if df is None or df.empty:
        st.warning("⚠️ Nenhuma rota processada. Suba uma planilha na aba Início.")
        return

    # --- 1. ESTADO INICIAL ---
    if 'indice_parada' not in st.session_state:
        st.session_state.indice_parada = 0
    if 'entregas_concluidas' not in st.session_state:
        st.session_state.entregas_concluidas = set()
    if 'mapa_id' not in st.session_state:
        st.session_state.mapa_id = 0

    # --- 2. CONFIGURAÇÃO DO MAPA (COM ROTAÇÃO REAL) ---
    parada_selecionada = df.iloc[st.session_state.indice_parada]
    
    # Criamos o mapa base
    m = folium.Map(
        location=[parada_selecionada['Latitude'], parada_selecionada['Longitude']], 
        zoom_start=16,
        tiles="CartoDB positron",
        # Adicionamos essas opções de controle para permitir o toque
        control_scale=True
    )

    # GPS em tempo real
    LocateControl(auto_start=False, fly_to=True, keep_current_zoom_level=True).add_to(m)

    # SCRIPT EXTRA PARA FORÇAR A ROTAÇÃO NO CELULAR (Giro com 2 dedos)
    # Isso injeta um comando no mapa para liberar o giro que o Folium trava por padrão
    m.get_root().html.add_child(folium.Element("""
        <script>
            var map_element = document.querySelector('.folium-map');
            if (map_element) {
                var map = map_element.map;
                map.touchZoom.rotate = true;
                map.touchRotate.enable();
            }
        </script>
    """))

    # --- 3. MARCADORES ---
    for i, row in df.iterrows():
        if i in st.session_state.entregas_concluidas:
            cor_pino = "#2ecc71" 
        elif i == st.session_state.indice_parada:
            cor_pino = "#e74c3c" 
        else:
            cor_pino = "#3498db" 

        folium.Marker(
            [row['Latitude'], row['Longitude']],
            tooltip=f"Entrega {i}",
            icon=folium.DivIcon(
                html=f"""<div style="background-color: {cor_pino}; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; justify-content: center; align-items: center; font-weight: bold; border: 2px solid white; box-shadow: 2px 2px 5px rgba(0,0,0,0.4); font-size: 14px;">{i + 1}</div>"""
            )
        ).add_to(m)

    # --- 4. RENDERIZAÇÃO ---
    mapa_dados = st_folium(
        m, 
        width="100%", 
        height=350, 
        key=f"mapa_v{st.session_state.mapa_id}",
        returned_objects=["last_object_clicked_tooltip"]
    )

    # --- 5. LOGICA DE CLIQUE ---
    if mapa_dados and mapa_dados.get("last_object_clicked_tooltip"):
        tooltip = mapa_dados["last_object_clicked_tooltip"]
        try:
            novo_indice = int(tooltip.replace("Entrega ", ""))
            if novo_indice != st.session_state.indice_parada:
                st.session_state.indice_parada = novo_indice
                st.session_state.mapa_id += 1 
                st.rerun()
        except:
            pass

    # --- 6. CARD DE INFORMAÇÕES (MANTIDO) ---
    parada_atual = df.iloc[st.session_state.indice_parada]
    total_total = len(df)
    info_sequence = parada_atual.get('Sequence', 'N/A') 

    st.markdown("""
        <style>
            .card-entrega {
                background-color: #002b36;
                padding: 15px;
                border-radius: 12px;
                color: white !important;
                margin-top: 10px;
                border-left: 8px solid #268bd2;
            }
            .info-linha {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .badge-azul {
                background-color: #073642;
                padding: 3px 10px;
                border-radius: 15px;
                color: #2aa198;
                font-weight: bold;
                border: 1px solid #268bd2;
                font-size: 13px;
            }
        </style>
    """, unsafe_allow_html=True)

    status_txt = "✅ CONCLUÍDA" if st.session_state.indice_parada in st.session_state.entregas_concluidas else "🟦 PENDENTE"

    st.markdown(f"""
        <div class="card-entrega">
            <div class="info-linha">
                <span class="badge-azul">📦 {info_sequence}</span>
                <span style="font-weight: bold; color: #93a1a1;">PARADA {st.session_state.indice_parada + 1} de {total_total}</span>
            </div>
            <div style="font-size: 13px; color: #93a1a1; margin-bottom: 5px;">{status_txt}</div>
            <div style="font-size: 20px; font-weight: bold; margin: 5px 0;">📍 {parada_atual['Destination Address']}</div>
            <div style="font-size: 15px; color: #2aa198;">Bairro: {parada_atual.get('Bairro', 'N/A')}</div>
        </div>
    """, unsafe_allow_html=True)

    # BOTÕES DE AÇÃO E NAVEGAÇÃO (MANTIDOS)
    c1, c2 = st.columns(2)
    with c1:
        link_waze = f"https://waze.com/ul?ll={parada_atual['Latitude']},{parada_atual['Longitude']}&navigate=yes"
        st.link_button("🚗 WAZE", link_waze, use_container_width=True)
    with c2:
        if st.session_state.indice_parada in st.session_state.entregas_concluidas:
            if st.button("↩️ DESFAZER", use_container_width=True):
                st.session_state.entregas_concluidas.remove(st.session_state.indice_parada)
                st.session_state.mapa_id += 1 
                st.rerun()
        else:
            if st.button("✅ ENTREGUE", type="primary", use_container_width=True):
                st.session_state.entregas_concluidas.add(st.session_state.indice_parada)
                if st.session_state.indice_parada < len(df) - 1:
                    time.sleep(0.4)
                    st.session_state.indice_parada += 1
                st.session_state.mapa_id += 1
                st.rerun()

    nav1, nav2 = st.columns(2)
    if nav1.button("⬅️ ANTERIOR", use_container_width=True):
        if st.session_state.indice_parada > 0:
            st.session_state.indice_parada -= 1
            st.session_state.mapa_id += 1
            st.rerun()
    if nav2.button("PRÓXIMA ➡️", use_container_width=True):
        if st.session_state.indice_parada < len(df) - 1:
            st.session_state.indice_parada += 1
            st.session_state.mapa_id += 1
            st.rerun()

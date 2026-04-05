import streamlit as st
from funcoes import *

def mostrar_aba_notas():
    st.session_state.banco_notas = carregar_obs()
    st.subheader("📝 Gerenciar Notas")
    
    lista_opcoes = ["-- Selecione um endereço --"] + st.session_state.enderecos_planilha if st.session_state.enderecos_planilha else ["-- Planilha não carregada --"]
    endereco_selecionado = st.selectbox("📍 Buscar da Planilha:", lista_opcoes)
    
    if endereco_selecionado and endereco_selecionado not in ["-- Selecione um endereço --", "-- Planilha não carregada --"]:
        rua_sug, num_sug, comp_sug = normalizar_rua(endereco_selecionado), extrair_numero(endereco_selecionado), extrair_complemento_puro(endereco_selecionado)
    else:
        rua_sug, num_sug, comp_sug = "", "", ""

    with st.form("form_notas", clear_on_submit=True):
        col_r, col_n, col_c = st.columns([2, 1, 1])
        with col_r: rua_in = st.text_input("Rua", value=rua_sug).upper().strip()
        with col_n: num_in = st.text_input("Número", value=num_sug).strip()
        with col_c: comp_in = st.text_input("Complemento (AP)", value=comp_sug).upper().strip()
        obs_in = st.text_input("Nota / Observação")
        
        if st.form_submit_button("➕ Salvar Nota"):
            if rua_in and num_in and obs_in:
                banco = carregar_obs()
                chave = f"{rua_in}|{num_in}|{padronizar_complemento(comp_in)}"
                banco[chave] = obs_in
                salvar_obs(banco)
                st.success("Nota salva!")
                st.rerun()

    st.divider()
    
    if st.session_state.get('banco_notas'):
        st.subheader("📋 Notas Ativas")
        c_head1, c_head2, c_head3 = st.columns([2, 2, 1])
        c_head1.markdown("**⚠️ OBSERVAÇÃO**")
        c_head2.markdown("**📍 ENDEREÇO**")
        st.write("---")

        for chave, nota in list(st.session_state.banco_notas.items()):
            try:
                partes = chave.split('|')
                if len(partes) == 3:
                    end_visual = f"📍 {partes[0]}, {partes[1]} {partes[2]}"
                else:
                    end_visual = f"📍 {chave.replace('|', ', ')}"
                
                col_obs, col_end, col_del = st.columns([2, 2, 1])
                col_obs.markdown(f"⚠️ **{nota}**")
                col_end.markdown(f"{end_visual}")
                
                if col_del.button("🗑️ Apagar", key=f"del_v5_{chave}"):
                    banco_atual = carregar_obs()
                    if chave in banco_atual:
                        del banco_atual[chave]
                        salvar_obs(banco_atual)
                    st.rerun()
            except: continue
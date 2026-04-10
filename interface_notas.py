import streamlit as st
import re
# Importamos as novas funções de nuvem e as de tratamento de texto do seu funcoes.py
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas,
    normalizar_rua,
    extrair_numero,
    extrair_complemento_puro,
    padronizar_complemento
)

def mostrar_aba_notas():
    # BUSCA NA NUVEM em vez de arquivo local
    st.session_state.banco_notas = carregar_dados_fluxoderotas("observacoes")
    
    st.subheader("📝 Gerenciar Notas")
    
    lista_opcoes = ["-- Selecione um endereço --"] + st.session_state.enderecos_planilha if st.session_state.enderecos_planilha else ["-- Planilha não carregada --"]
    endereco_selecionado = st.selectbox("📍 Buscar da Planilha:", lista_opcoes)
    
    if endereco_selecionado and endereco_selecionado not in ["-- Selecione um endereço --", "-- Planilha não carregada --"]:
        rua_sug = normalizar_rua(endereco_selecionado)
        num_sug = extrair_numero(endereco_selecionado)
        comp_sug = extrair_complemento_puro(endereco_selecionado)
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
                # Carrega o estado atual da nuvem
                banco = carregar_dados_fluxoderotas("observacoes")
                chave = f"{rua_in}|{num_in}|{padronizar_complemento(comp_in)}"
                banco[chave] = obs_in
                
                # SALVA NA NUVEM (Firestore)
                if salvar_dados_fluxoderotas(banco, "observacoes"):
                    st.success("Nota salva na nuvem!")
                    st.rerun()
                else:
                    st.error("Erro ao salvar no banco de dados.")

    st.divider()
    
    if st.session_state.get('banco_notas'):
        st.subheader("📋 Notas Ativas")
        c_head1, c_head2, c_head3 = st.columns([2, 2, 1])
        c_head1.markdown("**⚠️ OBSERVAÇÃO**")
        c_head2.markdown("**📍 ENDEREÇO**")
        st.write("---")

        # Listamos o que veio do Firestore
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
                    # Remove da nuvem
                    banco_atual = carregar_dados_fluxoderotas("observacoes")
                    if chave in banco_atual:
                        del banco_atual[chave]
                        if salvar_dados_fluxoderotas(banco_atual, "observacoes"):
                            st.rerun()
                        else:
                            st.error("Erro ao apagar do banco.")
            except: 
                continue

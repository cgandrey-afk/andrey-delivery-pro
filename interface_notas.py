import streamlit as st
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas,
    padronizar_complemento
)

def mostrar_aba_notas():
    # 1. BUSCA NA NUVEM
    banco = carregar_dados_fluxoderotas("observacoes")
    st.session_state.banco_notas = banco
    
    st.subheader("📝 Gerenciar Notas e Alertas")

    # --- CAMPOS DE ENDEREÇO (DENTRO DO FORM PARA ORGANIZAÇÃO) ---
    with st.form("form_endereco"):
        st.markdown("### 🏠 Dados do Endereço (Obrigatórios)")
        rua_in = st.text_input("Rua *").upper().strip()
        
        col_num, col_comp, col_bairro = st.columns([1, 1, 2])
        num_in = col_num.text_input("Número *").strip()
        comp_in = col_comp.text_input("Complemento").upper().strip()
        bairro_in = col_bairro.text_input("Bairro *").upper().strip()

        col_cid, col_cep = st.columns([2, 1])
        cidade_in = col_cid.text_input("Cidade *", value="CAMPINAS").upper().strip()
        cep_in = col_cep.text_input("CEP").strip()
        
        # O botão do formulário apenas valida o endereço internamente
        st.form_submit_button("Confirmar Endereço", use_container_width=True)

    st.divider()
    
    # --- SELEÇÃO DE OBSERVAÇÃO (FORA DO FORM PARA SER INSTANTÂNEO) ---
    st.markdown("### ⚠️ Observação")
    opcao_selecionada = st.radio(
        "Selecione o tipo de alerta:",
        [
            "Nenhuma",
            "🚫 Abre PNR tentando dar golpe", 
            "🐕 Não jogar, cachorro destrói", 
            "🏠 Entregar no vizinho", 
            "📌 Outros"
        ],
        index=0
    )

    # Lógica Dinâmica: Aparece na hora!
    info_adicional = ""
    if opcao_selecionada == "🏠 Entregar no vizinho":
        info_adicional = st.text_input("Número ou Nome do Vizinho:", placeholder="Ex: Sr. João no 110").upper().strip()
    
    elif opcao_selecionada == "📌 Outros":
        info_adicional = st.text_area("Descreva a observação:", placeholder="Digite os detalhes aqui...").upper().strip()

    st.write("")

    # --- BOTÃO FINAL DE SALVAMENTO ---
    if st.button("➕ SALVAR NOTA NA NUVEM", type="primary", use_container_width=True):
        if not (rua_in and num_in and bairro_in and cidade_in):
            st.error("❌ Preencha os campos obrigatórios de endereço acima primeiro!")
        elif opcao_selecionada == "Nenhuma":
            st.warning("⚠️ Selecione uma opção de observação.")
        elif (opcao_selecionada in ["🏠 Entregar no vizinho", "📌 Outros"]) and not info_adicional:
            st.error(f"❌ Descreva os detalhes para a opção '{opcao_selecionada}'.")
        else:
            # Processamento final
            texto_limpo = opcao_selecionada.replace("🚫 ", "").replace("🐕 ", "").replace("🏠 ", "").replace("📌 ", "").upper()
            nota_final = f"{texto_limpo}: {info_adicional}" if info_adicional else texto_limpo
            
            chave = f"{rua_in}|{num_in}|{padronizar_complemento(comp_in)}"
            banco[chave] = f"{nota_final} ({bairro_in})"
            
            if salvar_dados_fluxoderotas(banco, "observacoes"):
                st.success("✅ Nota salva com sucesso!")
                st.rerun()

    st.divider()
    # (O restante do código de listagem permanece igual...)

    # 3. LISTAGEM (APENAS LOGADO)
    if st.session_state.get('banco_notas'):
        st.subheader("📋 Notas Ativas")
        for chave, nota in list(st.session_state.banco_notas.items()):
            partes = chave.split('|')
            end_visual = f"{partes[0]}, {partes[1]}"
            if len(partes) > 2 and partes[2]: end_visual += f" - {partes[2]}"
            
            c1, c2, c3 = st.columns([2, 3, 0.5])
            c1.markdown(f"**{end_visual}**")
            
            if "GOLPE" in nota:
                c2.error(nota)
            else:
                c2.info(nota)
            
            if c3.button("🗑️", key=f"del_v8_{chave}"):
                banco_atual = carregar_dados_fluxoderotas("observacoes")
                if chave in banco_atual:
                    del banco_atual[chave]
                    salvar_dados_fluxoderotas(banco_atual, "observacoes")
                    st.rerun()
                st.divider()

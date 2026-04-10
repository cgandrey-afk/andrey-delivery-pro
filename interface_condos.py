import streamlit as st
import re
from funcoes import (
    carregar_json,
    salvar_json,
    formatar_endereco_condo,
    CONDO_FILE
)

def mostrar_aba_condos():
    st.subheader("🏢 Cadastro de Condomínios")
    db_condo = carregar_json(CONDO_FILE)

    # --- INICIALIZAÇÃO DO STATE ---
    if 'temp_enderecos_grupo' not in st.session_state:
        st.session_state.temp_enderecos_grupo = []
    if 'editando_nome' not in st.session_state:
        st.session_state.editando_nome = None
    if 'reset_count' not in st.session_state:
        st.session_state.reset_count = 0

    rc = st.session_state.reset_count

    # --- SELEÇÃO INICIAL (O QUE FICA VISÍVEL) ---
    st.markdown("### ⚙️ Como deseja cadastrar?")
    
    # Buscamos o tipo se estiver editando para pré-selecionar
    val_atual = db_condo.get(st.session_state.editando_nome, {}) if st.session_state.editando_nome else {}
    idx_init = 0
    if val_atual.get("tipo") == "separado_por_bloco": idx_init = 2
    elif val_atual.get("tipo") == "multi_ruas": idx_init = 1

    tipo_selecionado = st.radio(
        "Selecione o modelo de condomínio:",
        ["Selecione...", "1 Portaria (Várias ruas/números para o mesmo local)", "Várias Portarias (Mesmo endereço, mas portarias por Bloco/Torre)"],
        index=idx_init,
        key=f"tipo_main_{rc}"
    )

    if tipo_selecionado == "Selecione...":
        st.info("Escolha uma opção acima para exibir o formulário.")
        # Se não houver nada selecionado, listamos os cadastrados lá embaixo e paramos o script aqui
        exibir_listagem_condos(db_condo, rc)
        return

    # Define a lógica baseada na escolha
    e_multi_portaria = "Várias Portarias" in tipo_selecionado
    tipo_final_string = "separado_por_bloco" if e_multi_portaria else "multi_ruas"

    # --- FORMULÁRIO (AGORA VISÍVEL) ---
    st.divider()
    if st.session_state.editando_nome:
        st.warning(f"📝 Editando: {st.session_state.editando_nome}")
        if st.button("❌ Cancelar Edição"):
            st.session_state.editando_nome = None
            st.session_state.temp_enderecos_grupo = []
            st.session_state.reset_count += 1
            st.rerun()

    nome_grupo = st.text_input("Nome do Condomínio", value=st.session_state.editando_nome if st.session_state.editando_nome else "", key=f"nome_{rc}")
    
    col_cid, col_bai, col_cep = st.columns([2, 2, 1])
    with col_cid:
        cidade_grupo = st.text_input("Cidade", value=val_atual.get("cidade", "CAMPINAS"), key=f"cid_{rc}").upper()
    with col_bai:
        bairro_grupo = st.text_input("Bairro", value=val_atual.get("bairro", ""), key=f"bai_{rc}").upper()
    with col_cep:
        cep_grupo = st.text_input("CEP", value=val_atual.get("cep", ""), key=f"cep_{rc}")

    # --- SEÇÃO DE ENDEREÇOS ---
    st.markdown("### 📍 Configuração dos Endereços")
    
    if e_multi_portaria:
        # MODO VÁRIAS PORTARIAS: Rua/Num são fixos para o grupo, varia o Bloco
        col_r, col_n = st.columns([3, 1])
        with col_r: rua_fixa = st.text_input("Rua Principal do Condomínio", value=val_atual.get("rua_fixa", ""), key=f"rf_{rc}")
        with col_n: num_fixo = st.text_input("Número", value=val_atual.get("num_fixo", ""), key=f"nf_{rc}")
        
        bloco_in = st.text_input("Bloco / Torre / Portão", placeholder="Ex: Bloco A ou Torre 2", key=f"bloco_in_{rc}")
        
        if st.button("➕ Adicionar Bloco/Portaria"):
            if rua_fixa and num_fixo and bloco_in:
                # Monta ex: "RUA EXEMPLO, 100 BLOCO A"
                novo_end = formatar_endereco_condo(f"{rua_fixa}, {num_fixo} {bloco_in}")
                if novo_end not in st.session_state.temp_enderecos_grupo:
                    st.session_state.temp_enderecos_grupo.append(novo_end)
                    st.rerun()
            else:
                st.error("Preencha a Rua, Número e o Bloco.")

    else:
        # MODO 1 PORTARIA: Rua/Num variam na lista
        col_r, col_n = st.columns([3, 1])
        with col_r: rua_in = st.text_input("Rua", key=f"ri_{rc}")
        with col_n: num_in = st.text_input("Número", key=f"ni_{rc}")
        
        if st.button("➕ Adicionar Endereço ao Grupo"):
            if rua_in and num_in:
                novo_end = formatar_endereco_condo(f"{rua_in}, {num_in}")
                if novo_end not in st.session_state.temp_enderecos_grupo:
                    st.session_state.temp_enderecos_grupo.append(novo_end)
                    st.rerun()
            else:
                st.error("Preencha Rua e Número.")

    # --- LISTAGEM TEMPORÁRIA ---
    if st.session_state.temp_enderecos_grupo:
        st.write("**Lista de Portarias/Endereços Vinculados:**")
        for idx, end in enumerate(st.session_state.temp_enderecos_grupo):
            c1, c2 = st.columns([5, 1])
            c1.code(end)
            if c2.button("🗑️", key=f"del_temp_{idx}_{rc}"):
                st.session_state.temp_enderecos_grupo.pop(idx)
                st.rerun()

    st.divider()

    # --- CAMPO DE PORTARIA PRINCIPAL (Só aparece no modo 1 Portaria) ---
    portaria_final = ""
    if not e_multi_portaria:
        portaria_final = st.text_input("Endereço da Portaria (Waze)", value=val_atual.get("portaria", ""), key=f"port_fin_{rc}")

    # --- SALVAMENTO ---
    if st.button("💾 SALVAR CADASTRO", type="primary"):
        if not nome_grupo or not st.session_state.temp_enderecos_grupo:
            st.error("Nome e ao menos um endereço são obrigatórios.")
        else:
            # Estrutura do JSON
            dados = {
                "tipo": tipo_final_string,
                "cidade": cidade_grupo,
                "bairro": bairro_grupo,
                "cep": cep_grupo,
                "enderecos": st.session_state.temp_enderecos_grupo
            }
            
            if e_multi_portaria:
                dados["portarias"] = st.session_state.temp_enderecos_grupo
                dados["rua_fixa"] = rua_fixa
                dados["num_fixo"] = num_fixo
            else:
                dados["portaria"] = formatar_endereco_condo(portaria_final)

            # Se mudou o nome, apaga o antigo
            if st.session_state.editando_nome and st.session_state.editando_nome != nome_grupo:
                if st.session_state.editando_nome in db_condo: del db_condo[st.session_state.editando_nome]

            db_condo[nome_grupo] = dados
            salvar_json(db_condo, CONDO_FILE)
            st.session_state.editando_nome = None
            st.session_state.temp_enderecos_grupo = []
            st.session_state.reset_count += 1
            st.success("Salvo com sucesso!")
            st.rerun()

    exibir_listagem_condos(db_condo, rc)

def exibir_listagem_condos(db_condo, rc):
    st.divider()
    st.write("### 🗂️ Condomínios Cadastrados")
    for nome, info in db_condo.items():
        with st.expander(f"{nome} ({info.get('bairro')})"):
            st.write(f"Tipo: {info.get('tipo')}")
            st.code("\n".join(info.get("enderecos", [])))
            
            c1, c2 = st.columns(2)
            if c1.button("📝 Editar", key=f"ed_{nome}_{rc}"):
                st.session_state.editando_nome = nome
                st.session_state.temp_enderecos_grupo = info.get("enderecos", []).copy()
                st.session_state.reset_count += 1
                st.rerun()
            if c2.button("🗑️ Excluir", key=f"ex_{nome}_{rc}"):
                del db_condo[nome]
                salvar_json(db_condo, CONDO_FILE)
                st.rerun()

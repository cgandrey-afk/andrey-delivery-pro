import streamlit as st
import re
# Importamos as novas funções de nuvem do seu funcoes.py
from funcoes import (
    carregar_dados_fluxoderotas, 
    salvar_dados_fluxoderotas,
    formatar_endereco_condo
)

def mostrar_aba_condos():
    st.subheader("🏢 Cadastro de Condomínios")
    
    # BUSCA NA NUVEM
    db_condo = carregar_dados_fluxoderotas("condominios")

    # --- INICIALIZAÇÃO DO STATE ---
    if 'temp_enderecos_grupo' not in st.session_state:
        st.session_state.temp_enderecos_grupo = []
    if 'editando_nome' not in st.session_state:
        st.session_state.editando_nome = None
    if 'reset_count' not in st.session_state:
        st.session_state.reset_count = 0

    rc = st.session_state.reset_count

    st.markdown("### ⚙️ Configuração do Grupo")
    
    if st.session_state.editando_nome:
        st.warning(f"📝 Editando: {st.session_state.editando_nome}")
        if st.button("❌ Cancelar Edição"):
            st.session_state.editando_nome = None
            st.session_state.temp_enderecos_grupo = []
            st.session_state.reset_count += 1
            st.rerun()

    nome_grupo = st.text_input("Nome do Condomínio (Ex: Cond. Jd. Paulicéia)", 
                               value=st.session_state.editando_nome if st.session_state.editando_nome else "", 
                               key=f"nome_{rc}")

    # --- SEÇÃO DE ADICIONAR ENDEREÇOS ---
    st.divider()
    st.markdown("### ➕ Adicionar Endereço ao Grupo")
    st.info("Cadastre cada Bloco/Rua com seu próprio Bairro e Cidade para garantir o agrupamento.")

    col_r, col_n = st.columns([3, 1])
    rua_in = col_r.text_input("Rua / Bloco (Ex: BLOCO T ou Rua Antônio Rodrigues)", key=f"ri_{rc}")
    num_in = col_n.text_input("Nº", key=f"ni_{rc}")
    
    col_b, col_c, col_z = st.columns([2, 2, 1])
    bair_in = col_b.text_input("Bairro deste endereço", key=f"bi_{rc}").upper()
    cida_in = col_c.text_input("Cidade", value="CAMPINAS", key=f"ci_{rc}").upper()
    cep_in = col_z.text_input("CEP", key=f"zp_{rc}")

    if st.button("➕ Vincular este Endereço"):
        if rua_in and num_in:
            # CRIAMOS O DICIONÁRIO COMPLETO
            novo_item = {
                "rua": rua_in.upper().strip(),
                "numero": num_in.upper().strip(),
                "bairro": bair_in.strip(),
                "cidade": cida_in.strip(),
                "cep": cep_in.strip()
            }
            
            # Evita duplicados na lista temporária
            if not any(isinstance(d, dict) and d.get('rua') == novo_item['rua'] and d.get('numero') == novo_item['numero'] for d in st.session_state.temp_enderecos_grupo):
                st.session_state.temp_enderecos_grupo.append(novo_item)
                st.rerun()
            else:
                st.warning("Este endereço já está na lista.")
        else:
            st.error("Rua e Número são obrigatórios.")

    # --- LISTAGEM DOS ENDEREÇOS ADICIONADOS ---
    if st.session_state.temp_enderecos_grupo:
        st.write("**Endereços na lista deste grupo:**")
        for idx, item in enumerate(st.session_state.temp_enderecos_grupo):
            c1, c2 = st.columns([5, 1])
            
            # Tratamento para exibir tanto o formato novo (dict) quanto o antigo (str)
            if isinstance(item, dict):
                texto_exibir = f"{item.get('rua')}, {item.get('numero')} - {item.get('bairro')} ({item.get('cidade')})"
            else:
                texto_exibir = str(item)
                
            c1.code(texto_exibir)
            if c2.button("🗑️", key=f"del_temp_{idx}_{rc}"):
                st.session_state.temp_enderecos_grupo.pop(idx)
                st.rerun()

    st.divider()

    # Endereço da Portaria (Onde o Waze deve levar)
    val_atual = db_condo.get(st.session_state.editando_nome, {}) if st.session_state.editando_nome else {}
    portaria_final = st.text_input("📍 Endereço da Portaria (Onde o Waze deve levar no final)", 
                                   value=val_atual.get("portaria", ""), 
                                   key=f"port_fin_{rc}")

    # --- SALVAMENTO NA NUVEM ---
    if st.button("💾 SALVAR GRUPO DE CONDOMÍNIO", type="primary"):
        if not nome_grupo or not st.session_state.temp_enderecos_grupo or not portaria_final:
            st.error("Nome, Endereços e Portaria são obrigatórios.")
        else:
            dados_novos = {
                "tipo": "multi_ruas",
                "portaria": portaria_final.upper().strip(),
                "enderecos": st.session_state.temp_enderecos_grupo # Lista de dicionários
            }
            
            # Se mudou o nome, apaga o registro antigo
            if st.session_state.editando_nome and st.session_state.editando_nome != nome_grupo:
                if st.session_state.editando_nome in db_condo: 
                    del db_condo[st.session_state.editando_nome]

            db_condo[nome_grupo] = dados_novos
            
            if salvar_dados_fluxoderotas(db_condo, "condominios"):
                st.session_state.editando_nome = None
                st.session_state.temp_enderecos_grupo = []
                st.session_state.reset_count += 1
                st.success("Grupo de condomínio salvo com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao salvar no banco de dados.")

    exibir_listagem_condos(db_condo, rc)

def exibir_listagem_condos(db_condo, rc):
    st.divider()
    st.write("### 🗂️ Condomínios Cadastrados")
    if not db_condo:
        st.info("Nenhum condomínio cadastrado na nuvem.")
        return

    for nome, info in db_condo.items():
        # Tenta pegar o bairro do primeiro endereço para exibir no cabeçalho
        primeiro_end = info.get("enderecos", [{}])[0]
        bairro_v = primeiro_end.get("bairro", "N/A") if isinstance(primeiro_end, dict) else "Legado"
        
        with st.expander(f"{nome} ({bairro_v})"):
            st.write(f"**Portaria (Waze):** {info.get('portaria')}")
            
            # Formata a lista para exibição
            lista_str = []
            for e in info.get("enderecos", []):
                if isinstance(e, dict):
                    lista_str.append(f"{e.get('rua')}, {e.get('numero')} - {e.get('bairro')}")
                else:
                    lista_str.append(str(e))
            
            st.code("\n".join(lista_str))
            
            c1, c2 = st.columns(2)
            if c1.button("📝 Editar", key=f"ed_{nome}_{rc}"):
                st.session_state.editando_nome = nome
                st.session_state.temp_enderecos_grupo = info.get("enderecos", []).copy()
                st.session_state.reset_count += 1
                st.rerun()
            
            if c2.button("🗑️ Excluir", key=f"ex_{nome}_{rc}"):
                del db_condo[nome]
                if salvar_dados_fluxoderotas(db_condo, "condominios"):
                    st.success("Excluído com sucesso!")
                    st.rerun()
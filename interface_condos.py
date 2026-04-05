import streamlit as st
import re
from funcoes import (
    carregar_json,
    salvar_json,
    formatar_endereco_condo,
    limpar_duplicidade_numero,
    CONDO_FILE
)

# --- FUNÇÃO CORRIGIDA PARA USAR O PADRÃO RUA, NUMERO BL X ---
def padronizar_portaria(texto):
    """Usa a lógica central de formatação para garantir a vírgula e espaços"""
    if not texto: return ""
    # A formatar_endereco_condo já resolve o RUA, NUMERO e o Bloco
    return formatar_endereco_condo(texto)


def mostrar_aba_condos():
    st.subheader("🏢 Cadastro de Condomínios")
    db_condo = carregar_json(CONDO_FILE)

    modo = st.radio(
        "O que você quer fazer?",
        [
            "1 portaria para vários endereços",
            "Várias portarias no mesmo endereço"
        ]
    )

    with st.form("form_condo"):
        nome_grupo = st.text_input("Nome do condomínio/grupo")

        # =========================
        # 🔵 CASO 1: Várias ruas -> 1 Portaria
        # =========================
        if modo == "1 portaria para vários endereços":
            st.info("Use quando várias ruas entregam no MESMO local")

            selecionados = st.multiselect(
                "Endereços da planilha",
                st.session_state.get('enderecos_planilha', [])
            )

            manuais = st.text_area("Ou digite manualmente (1 por linha)")

            lista_bruta = list(set(
                selecionados +
                [x.strip() for x in manuais.split('\n') if x.strip()]
            ))

            # Aqui garantimos que cada endereço da lista tenha a vírgula
            lista_formatada = sorted(list(set([
                formatar_endereco_condo(e)
                for e in lista_bruta
            ])))

            if lista_formatada:
                st.write("Endereços identificados:")
                st.code("\n".join(lista_formatada))

            portaria_input = st.text_input(
                "Endereço da portaria principal",
                placeholder="Ex: RUA CENTRAL, 100"
            )
            # Padroniza a portaria de destino
            portaria = padronizar_portaria(portaria_input)

        # =========================
        # 🔴 CASO 2: 1 Endereço -> Vários Blocos
        # =========================
        else:
            st.info("Use quando o mesmo endereço tem portarias diferentes por bloco/torre")

            end_base_input = st.text_input(
                "Endereço base",
                placeholder="Ex: RUA EMA, 150"
            )
            # Garante que a base já tenha a vírgula: RUA EMA, 150
            endereco_base = padronizar_portaria(end_base_input)

            portarias_input = st.text_area(
                "Portarias (uma por linha)",
                placeholder="Ex:\nBL A\nBL B\nBL C"
            )

            # Aqui montamos RUA, NUMERO + BLOCO garantindo espaço e vírgula
            lista_portarias = []
            for x in portarias_input.split('\n'):
                if x.strip():
                    # Monta o texto completo e deixa a padronizar_portaria arrumar a pontuação
                    texto_completo = f"{endereco_base} {x.strip()}"
                    lista_portarias.append(padronizar_portaria(texto_completo))

            if lista_portarias:
                st.write("Portarias identificadas (Padronizadas):")
                st.code("\n".join(lista_portarias))

        # =========================
        # SALVAR
        # =========================
        if st.form_submit_button("Salvar"):
            if not nome_grupo:
                st.error("Digite um nome")
                return

            if modo == "1 portaria para vários endereços":
                if not lista_formatada:
                    st.error("Adicione endereços")
                    return
                if not portaria:
                    st.error("Informe a portaria")
                    return

                db_condo[nome_grupo] = {
                    "tipo": "multi_ruas",
                    "portaria": portaria,
                    "enderecos": lista_formatada
                }

            else:
                if not endereco_base:
                    st.error("Informe o endereço base")
                    return
                if not lista_portarias:
                    st.error("Adicione portarias")
                    return

                db_condo[nome_grupo] = {
                    "tipo": "separado_por_bloco",
                    "portarias": lista_portarias
                }

            salvar_json(db_condo, CONDO_FILE)
            st.success("Salvo com sucesso!")
            st.rerun()

    # =========================
    # LISTAGEM
    # =========================
    st.write("## Condomínios cadastrados")
    if not db_condo:
        st.write("Nenhum cadastrado")

    for nome, info in db_condo.items():
        with st.expander(nome):
            if info['tipo'] == "multi_ruas":
                st.write("**Portaria de Entrega:**")
                st.code(info.get("portaria"))
                st.write("**Endereços Agrupados:**")
                st.code("\n".join(info.get("enderecos", [])))
            else:
                st.write("**Portarias por Bloco:**")
                st.code("\n".join(info.get("portarias", [])))

            if st.button("Excluir", key=f"del_{nome}"):
                del db_condo[nome]
                salvar_json(db_condo, CONDO_FILE)
                st.rerun()

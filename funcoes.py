import pandas as pd
import numpy as np
import json
import os
from difflib import SequenceMatcher
from num2words import num2words
from geopy.distance import geodesic
import re
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

# --- NOVA CONEXÃO FIRESTORE ---
def conectar_firestore():
    try:
        creds_info = st.secrets["firestoredb"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return firestore.Client(credentials=creds, project="fluxoderotas")
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

db = conectar_firestore()

# --- NOVAS FUNÇÕES DE NUVEM (FLUXODEROTAS) ---
def carregar_dados_fluxoderotas(nome_documento):
    try:
        if db:
            doc_ref = db.collection("fluxoderotas_config").document(nome_documento)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
        return {}
    except:
        return {}

def salvar_dados_fluxoderotas(dados, nome_documento):
    try:
        if db:
            doc_ref = db.collection("fluxoderotas_config").document(nome_documento)
            doc_ref.set(dados)
            return True
        return False
    except:
        return False

# --- MANTENHA TODAS AS SUAS OUTRAS FUNÇÕES ABAIXO (LIMPEZA, EXTRAÇÃO, AGRUPAMENTO) ---
# eh_nome_rua_generico, converter_numero_da_rua_ate_100, processar_agrupamento, etc...

# -----------------------------
# LIMPEZA E EXTRAÇÃO
# -----------------------------

def eh_nome_rua_generico(nome_rua):
    if not nome_rua: return False
    
    # Normaliza para comparação
    n = str(nome_rua).upper().strip()
    
    # 1. Se for apenas um número (Ex: "10", "1")
    if n.isdigit(): return True
    
    # 2. Lista expandida de nomes numéricos e genéricos
    nomes_genericos = [
        "UM", "DOIS", "TRES", "QUATRO", "CINCO", "SEIS", "SETE", "OITO", "NOVE", "DEZ",
        "ONZE", "DOZE", "TREZE", "QUATORZE", "QUINZE", "DEZESSEIS", "DEZESSETE", "DEZOITO", "DEZENOVE", "VINTE",
        "PRIMEIRA", "SEGUNDA", "TERCEIRA", "QUARTA", "QUINTA", "PROJETADA", "SEM NOME",
        "RUA A", "RUA B", "RUA C", "RUA D", "RUA E"
    ]
    
    # Verifica se o nome da rua contém EXATAMENTE uma dessas palavras isoladas
    for g in nomes_genericos:
        if re.search(rf'\b{g}\b', n):
            return True
            
    return False

def converter_numero_da_rua_ate_100(texto):
    if not texto: return ""
    t = str(texto).upper().strip()

    def realizar_conversao(match):
        # match.group(1) é a palavra "RUA "
        # match.group(2) é o número encontrado logo depois
        palavra_chave = match.group(1)
        num_str = match.group(2)
        
        try:
            num_int = int(num_str)
            # Só converte se for um número de rua razoável (1 a 100)
            # Isso evita converter por engano se alguém escrever "RUA 2026"
            if 1 <= num_int <= 100:
                extenso = num2words(num_int, lang='pt_BR').upper()
                return f"{palavra_chave}{extenso}"
            else:
                return f"{palavra_chave}{num_str}"
        except:
            return f"{palavra_chave}{num_str}"

    # REGEX EXPLICADA:
    # (\bRUA\s+) -> Grupo 1: A palavra RUA seguida de espaços
    # (\d+)      -> Grupo 2: O número colado nela
    # (?=\b)     -> Garante que o número terminou (fronteira de palavra)
    padrao = r'(\bRUA\s+)(\d+)(?=\b)'

    # Substitui apenas o que deu match na regra "RUA + NUMERO"
    t = re.sub(padrao, realizar_conversao, t, flags=re.IGNORECASE)
    
    return t
    
def extrair_bloco(texto):
    if pd.isna(texto): return ""
    # Normaliza: remove vírgulas e pontos para facilitar a busca
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # 1. Tenta o padrão clássico: PALAVRA + IDENTIFICADOR
    bl_match = re.search(r'\b(?:BLOCO|BLC|BL|PORTARIA)\s*([A-Z0-9/]+)\b', t)
    tr_match = re.search(r'\b(?:TORRE|T)\s*([A-Z0-9/]+)\b', t)
    ap_match = re.search(r'\b(?:AP|APT|APTO|UNIDADE)\s*([0-9/]+)\b', t)

    partes = []
    if bl_match: partes.append(f"BL {bl_match.group(1)}")
    if tr_match: partes.append(f"TORRE {tr_match.group(1)}")
    
    # 2. Se não achou "BLOCO" por nome, tenta pegar o que vem após o número da casa
    # Ex: Rua Ema, 150 - B (pega o B)
    if not partes:
        # Busca por um padrão: NUMERO DA CASA + (HIFEN ou ESPAÇO) + LETRA ISOLADA
        match_isolado = re.search(r'\d+\s*[-/]?\s*\b([A-Z])\b', t)
        if match_isolado:
            partes.append(f"BL {match_isolado.group(1)}")

    return " ".join(partes)

def sao_ruas_similares(rua1, rua2):
    if rua1 == rua2: return True
    return SequenceMatcher(None, str(rua1), str(rua2)).ratio() > 0.85

def limpar_duplicidade_numero(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    
    # Remove vírgulas e pontos para não interferir na posição do número
    texto = texto.replace(',', ' ').replace('.', ' ')
    
    # Remove espaços duplos que sobraram da remoção das vírgulas
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # Remove números repetidos (ex: 150 150)
    texto = re.sub(r'\b(\d+[A-Z]?)[\s]+\1\b', r'\1', texto)
    
    return texto

def limpar_rua_com_bairro(endereco, bairro_oficial):
    if pd.isna(endereco): return ""
    t = str(endereco).upper().strip()
    
    # 1. Limpeza inicial de pontuação
    t = t.replace(',', ' ').replace('.', ' ')
    
    # 2. Remover termos de "sujeira" que costumam grudar no nome da rua
    # Se encontrar AP, BLOCO ou EDIFICIO, cortamos tudo o que vem depois
    termos_corte = [r'\bAP\b', r'\bAPT\b', r'\bAPTO\b', r'\bEDIFICIO\b', r'\bED\b', r'\bCONDOMINIO\b', r'\bCD\b']
    for termo in termos_corte:
        t = re.split(termo, t)[0].strip()

    # 3. Lista de prefixos de bairro (mantendo sua lógica original)
    prefixos = {
        "JARDIM": ["JD", "JARD", "JARDIM"],
        "PARQUE": ["PQ", "PRQ", "PARQUE"],
        "VILA": ["V", "VL", "VILA"],
        "RESIDENCIAL": ["RES", "RESI", "RESIDENCIAL"]
    }

    bairro = str(bairro_oficial).upper().strip() if pd.notna(bairro_oficial) else ""
    
    if bairro:
        t = t.replace(bairro, "")
        for nome_cheio, abrevs in prefixos.items():
            if bairro.startswith(nome_cheio):
                nome_base_bairro = bairro.replace(nome_cheio, "").strip()
                for abrev in abrevs:
                    t = t.replace(f"{abrev} {nome_base_bairro}", "")

    # 4. Limpeza de espaços e remoção de números residenciais
    t = re.sub(r'\s+', ' ', t).strip()
    # A regex abaixo remove o número da casa e qualquer coisa que venha depois dele
    t = re.sub(r'\s\d+.*', '', t)
    
    return normalizar_rua(t)

def extrair_numero(texto):
    if pd.isna(texto): return ""
    # Primeiro limpamos o texto de vírgulas/pontos
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # Busca o primeiro conjunto de números que pode ter uma letra (ex: 150 ou 7B)
    match = re.search(r'\b(\d+[A-Z]?)\b', t)
    return match.group(1) if match else ""

def normalizar_rua(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper().replace(',', ' ').replace('.', ' ').strip()
    
    # Padronização de prefixos
    subs = {r'\bAV\b': 'AVENIDA', r'\bR\b': 'RUA', r'\bDR\b': 'DOUTOR', r'\bPROF\b': 'PROFESSOR'}
    for p, s in subs.items(): 
        t = re.sub(p, s, t)
        
    # CORREÇÃO: Remove palavras isoladas que sobraram no final do nome da rua
    # Isso evita "RUA JORNALISTA ERNESTO NAPOLI CONDOMINIO"
    travas_finais = [r'\bCONDOMINIO\b', r'\bEDIFICIO\b', r'\bED\b', r'\bAP\b']
    for trava in travas_finais:
        t = re.sub(trava + r'.*', '', t).strip()

    # Pega apenas o que vem antes do primeiro número isolado
    partes = re.split(r'\s\d+', t, maxsplit=1)
    return partes[0].strip()

def extrair_complemento_puro(texto):
    if pd.isna(texto): return ""
    match = re.search(r'\b(APT|APTO|AP|BLOCO|BL|TORRE|CASA)\b.*', str(texto).upper())
    return match.group(0).strip() if match else ""

def padronizar_complemento(texto):
    if not texto: return ""
    t = str(texto).upper().replace('-', '').replace('.', '')
    t = re.sub(r'\b(APARTAMENTO|APTO|APT)\b', 'AP', t)
    t = re.sub(r'\b(BLOCO)\b', 'BL', t)
    return t.strip()
    
def formatar_endereco_condo(texto):
    """Garante o padrão RUA, NUMERO BL X mesmo que digitado sem vírgula"""
    if pd.isna(texto): return ""
    
    # 1. Limpeza inicial de sujeira e espaços
    t = str(texto).upper().replace(',', ' ').strip()
    t = re.sub(r'\s+', ' ', t)
    
    # 2. Extrai as partes separadamente
    rua = normalizar_rua(t)
    num = extrair_numero(t)
    bloco = extrair_bloco(t) # Pega BL A, TORRE 1, etc.
    
    if rua and num:
        # Monta o padrão RUA, NUMERO
        base = f"{rua}, {num}"
        # Se houver bloco/torre, adiciona com espaço (sem grudar)
        if bloco:
            # Remove o bloco da base se ele foi pego por engano na rua
            base = base.replace(bloco, "").strip()
            return f"{base} {bloco}".replace(" ,", ",")
        return base
    
    return t

# -----------------------------
# REGRAS DE CONDOMÍNIO (A SUA SOLICITAÇÃO)
# -----------------------------
def verificar_separacao_bloco(row, db_condos):
    rua_num = f"{row['Rua_Base']}, {row['Num_Casa']}".upper()
    for info in db_condos.values():
        if info.get('tipo') == "separado_por_bloco":
            portarias = [str(p).upper() for p in info.get('portarias', [])]
            if any(rua_num in p for p in portarias):
                return True
    return False

def normalizar_termos_condo(texto):
    """Padroniza BLOCO/BLC/BL para 'BL' e TORRE/T para 'TORRE', mantendo o que vem depois."""
    if not texto: return ""
    t = str(texto).upper().replace(',', ' ').replace('.', ' ')
    
    # Padroniza variações mantendo o identificador (ex: BLOCO B -> BL B)
    t = re.sub(r'\b(BLOCO|BLC|BL)\s*([A-Z0-9]+)\b', r'BL \2', t)
    t = re.sub(r'\b(TORRE|T)\s*([A-Z0-9]+)\b', r'TORRE \2', t)
    
    # Remove espaços duplos
    return re.sub(r'\s+', ' ', t).strip()
    
def formatar_endereco_agrupado(row, db_condos):
    # 1. Preparação dos dados da planilha atual
    rua_planilha = str(row['Rua_Base']).upper().strip()
    num_planilha = str(row['Num_Casa']).upper().strip()
    bairro_planilha = str(row['Bairro']).upper().strip()
    cidade_planilha = str(row['City']).upper().strip()
    cep_planilha = "".join(filter(str.isdigit, str(row['Zipcode/Postal code'])))
    
    end_original = normalizar_termos_condo(row['Destination Address'])
    
    # --- TRAVAS DE RUA PURA ---
    travas_rua = ["VIELA", "CAMINHO", "CASA", "TERREO", "FUNDOS", "GARAGEM", "LOJA", "SALA"]
    if any(p in end_original for p in travas_rua):
        return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

    # 2. BUSCA NO CADASTRO
    for nome_grupo, info in db_condos.items():
        # Captura dados do cadastro (JSON)
        bairro_cad = str(info.get('bairro', '')).upper().strip()
        cidade_cad = str(info.get('cidade', '')).upper().strip()
        cep_cad = "".join(filter(str.isdigit, str(info.get('cep', ''))))

        # --- LÓGICA DE VALIDAÇÃO DE LOCALIDADE (CORRIGIDA) ---
        local_bate = False
        
        # Prioridade 1: CEP
        if cep_cad and cep_planilha == cep_cad:
            local_bate = True
        # Prioridade 2: Cidade + Bairro (com tolerância para "Jardim", "JD", etc)
        elif cidade_planilha == cidade_cad:
            # Verifica se um nome está contido no outro (resolve Pauliceia vs Jardim Pauliceia)
            if bairro_cad in bairro_planilha or bairro_planilha in bairro_cad:
                local_bate = True
            # Ou se a semelhança é alta (para erros de digitação)
            elif SequenceMatcher(None, bairro_planilha, bairro_cad).ratio() > 0.8:
                local_bate = True
            
        if not local_bate:
            continue # Se a localidade não bate, pula para o próximo condomínio do JSON

        # --- SE CHEGOU AQUI, A LOCALIDADE BATEU. AGORA TESTA O ENDEREÇO ---

        # CASO A: MULTI-RUAS (O novo layout que você fez)
        if info.get('tipo') == "multi_ruas":
            # Normaliza a lista de endereços do cadastro
            enderecos_lista = [normalizar_termos_condo(e) for e in info.get('enderecos', [])]
            # Endereço vindo da planilha
            atual_formatado = normalizar_termos_condo(f"{rua_planilha} {num_planilha}")
            
            if atual_formatado in enderecos_lista:
                portaria = str(info.get('portaria', '')).upper()
                return f"📍 {portaria}"

        # No CASO B: SEPARADO POR BLOCO
        elif info.get('tipo') == "separado_por_bloco":
            # Pegamos o que a regex extraiu da planilha (ex: "BL B TORRE 3")
            bloco_planilha = normalizar_termos_condo(row.get('Bloco', ''))
            match_condo_base = False
            
            # Guardamos para o Debug
            row['Debug_Bloco_Planilha'] = bloco_planilha
            
            for portaria_cadastrada in info.get('portarias', []):
                p_cad_norm = normalizar_termos_condo(portaria_cadastrada)
                
                # 1. Verifica se a rua e o número batem com esta portaria do JSON
                if rua_planilha in p_cad_norm and num_planilha in p_cad_norm:
                    match_condo_base = True
                    
                    # --- LÓGICA INTELIGENTE DE BUSCA E FORMATAÇÃO ---
                    
                    # A. Verifica se você cadastrou uma TORRE no JSON (ex: "TORRE 3")
                    match_t_json = re.search(r'TORRE\s*([A-Z0-9]+)', p_cad_norm)
                    if match_t_json:
                        id_torre = match_t_json.group(1)
                        # Se a planilha também tem essa TORRE, formata como T + número
                        if f"TORRE {id_torre}" in bloco_planilha:
                            return f"📍 {rua_planilha}, {num_planilha} T{id_torre}"

                    # B. Verifica se você cadastrou um BLOCO no JSON (ex: "BL B")
                    match_bl_json = re.search(r'BL\s*([A-Z0-9]+)', p_cad_norm)
                    if match_bl_json:
                        id_bloco = match_bl_json.group(1)
                        # Se a planilha também tem esse BLOCO, formata como BL + letra
                        if f"BL {id_bloco}" in bloco_planilha:
                            return f"📍 {rua_planilha}, {num_planilha} BL {id_bloco}"
            
            # Se reconheceu o condomínio mas o bloco/torre específico não deu match
            if match_condo_base:
                return f"📍 {rua_planilha}, {num_planilha}"
            
            if match_condo_base:
                return f"📍 {rua_planilha}, {num_planilha}"
    # 3. IDENTIFICAÇÃO GENÉRICA (Fora do cadastro)
    termos_condominio = [r'\bAP\b', r'\bAPT\b', r'\bAPTO\b', r'\bBL\b', r'\bBLOCO\b', r'\bTORRE\b', r'\bEDIFICIO\b']
    if any(re.search(p, end_original) for p in termos_condominio):
        return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

    return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

def montar_endereco_limpo(texto_completo, rua, num):
    """
    Pega apenas o que vem após o número da casa para evitar 'sujeira' no nome da rua.
    """
    num_esc = re.escape(num)
    # Procura o número e captura tudo o que vem depois
    match = re.search(rf"\b{num_esc}\b\s*,?\s*(.*)", texto_completo, re.IGNORECASE)
    
    if match:
        sobra = match.group(1).strip()
        if sobra:
            return f"{rua}, {num} {sobra}"
    
    return f"{rua}, {num}"


# -----------------------------
# FORMATAÇÃO DE SEQUÊNCIA
# -----------------------------
def formatar_sequencia_visual(lista_seq):
    numeros, adds = [], 0
    for s in lista_seq:
        s = str(s).strip()
        if not s or s == "-": 
            adds += 1
            continue
        # Extrai apenas os dígitos
        n = "".join(filter(str.isdigit, s))
        if n: 
            numeros.append(int(n))
        else: 
            adds += 1

    numeros = sorted(set(numeros))
    partes, i = [], 0
    while i < len(numeros):
        ini = numeros[i]
        fim = ini
        while i + 1 < len(numeros) and numeros[i + 1] == fim + 1:
            i += 1
            fim = numeros[i]
        if ini == fim: partes.append(f"{ini}")
        elif fim == ini + 1: partes.append(f"{ini} e {fim}")
        else: partes.append(f"{ini}–{fim}")
        i += 1

    total = len(numeros) + adds
    texto_numeros = ", ".join(partes)
    
    # --- CORREÇÃO DA VÍRGULA AQUI ---
    if adds > 0:
        # Se já tiver números, adiciona ", Adds: X". Se não, apenas "Adds: X"
        if texto_numeros:
            texto_final = f"{texto_numeros}, Adds: {adds}"
        else:
            texto_final = f"Adds: {adds}"
    else:
        texto_final = texto_numeros

    return f"Qtd: {total} ({texto_final})"

def aplicar_formatacao_final(row, notas_vivas):
    texto = formatar_sequencia_visual(row['Sequence'])
    for chave, nota in notas_vivas.items():
        try:
            r, n, c = chave.split('|')
            if row['Num_Casa'] == n and row['Comp_Padrao'] == c and SequenceMatcher(None, row['Rua_Base'], r).ratio() > 0.8:
                return f"{nota} | {texto}"
        except: continue
    return texto

def verificar_nota_local(row, notas_vivas): # Adicione notas_vivas aqui
    for chave in notas_vivas.keys():
        try:
            r, n, c = chave.split('|')
            if row['Num_Casa'] == n and row['Comp_Padrao'] == c and SequenceMatcher(None, row['Rua_Base'], r).ratio() > 0.8:
                return True
        except: continue
    return False

# -----------------------------
# PROCESSAMENTO PRINCIPAL
# -----------------------------
def processar_agrupamento(df_bruto, notas_vivas, db_condos):
    df = df_bruto.copy()
    
    # =========================================================
    # PASSO 1: PADRONIZAÇÃO TOTAL (ANTES DO AGRUPAMENTO)
    # =========================================================
    df['Destination Address'] = df['Destination Address'].apply(converter_numero_da_rua_ate_100)
    df['Destination Address'] = df['Destination Address'].apply(limpar_duplicidade_numero)
    df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)    
    df['Rua_Base'] = df.apply(lambda r: limpar_rua_com_bairro(r['Destination Address'], r['Bairro']), axis=1)
    df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
    df['Bloco'] = df['Destination Address'].apply(extrair_bloco)
    df['Separar_Bloco'] = df.apply(lambda r: verificar_separacao_bloco(r, db_condos), axis=1)
    df['Endereco_Formatado'] = df.apply(lambda r: formatar_endereco_agrupado(r, db_condos), axis=1)    
    
    #VERIFICA SE TEM NOTA PARA O ENDEREÇO
    df['Tem_Minha_Nota'] = df.apply(lambda r: verificar_nota_local(r, notas_vivas), axis=1)

    # =========================================================
    # PASSO 2: LÓGICA DE AGRUPAMENTO HIERÁRQUICA (CORRIGIDO)
    # =========================================================
    group_ids = np.zeros(len(df))
    curr = 1

    # --- OTIMIZAÇÃO: Geramos a lista de genéricos UMA VEZ fora do loop para não travar ---
    # Isso evita que o computador processe num2words milhares de vezes
    extensos_1_100 = [num2words(i, lang='pt_BR').upper() for i in range(1, 101)]
    outros_gen = ["PROJETADA", "SEM NOME", "A", "B", "C", "D", "E"]
    SET_GENERICOS = set(extensos_1_100 + outros_gen)

    def norm_b(b):
        if not b: return ""
        t = str(b).upper().strip()
        t = re.sub(r'\b(JD|JARD)\b', 'JARDIM', t)
        t = re.sub(r'\b(V|VL)\b', 'VILA', t)
        t = re.sub(r'\b(PQ|PRQ)\b', 'PARQUE', t)
        t = re.sub(r'\b(RES|RESI)\b', 'RESIDENCIAL', t)
        return t

    for i in range(len(df)):
        if group_ids[i] == 0:
            group_ids[i] = curr
            row_i = df.iloc[i]
            
            # Cache de dados da linha I
            rua_i = str(row_i['Rua_Base']).upper().strip()
            num_i = "".join(filter(str.isdigit, str(row_i['Num_Casa'])))
            bairro_i_norm = norm_b(row_i['Bairro'])
            nota_i = row_i['Tem_Minha_Nota']
            coord_i = (row_i['Latitude'], row_i['Longitude'])
            
            # Verifica se a rua I é genérica uma única vez
            is_gen_i = eh_nome_rua_generico(rua_i) 

            end_i = str(row_i['Endereco_Formatado']).upper().strip()
            comparar_i = end_i.replace("📍", "").replace(" ", "")

            for j in range(i + 1, len(df)):
                if group_ids[j] != 0: continue
                row_j = df.iloc[j]
                
                rua_j = str(row_j['Rua_Base']).upper().strip()
                bairro_j_norm = norm_b(row_j['Bairro'])

                # --- TRAVA DE SEGURANÇA: RUAS GENÉRICAS (Ex: Rua Dez) ---
                # Se for nome numérico ou genérico, o bairro PRECISA bater
                if is_gen_i or eh_nome_rua_generico(rua_j):
                    # Se bairros normalizados forem diferentes, pula o agrupamento
                    if bairro_i_norm != bairro_j_norm:
                        continue 

                # --- 1ª REGRA: NOTAS ---
                if nota_i != row_j['Tem_Minha_Nota']: continue

                # --- 2ª REGRA: BLOCOS E CONDOMÍNIOS (📍) ---
                end_j = str(row_j['Endereco_Formatado']).upper().strip()
                comparar_j = end_j.replace("📍", "").replace(" ", "")
                if (row_i['Separar_Bloco'] or row_j['Separar_Bloco'] or "📍" in end_i):
                    if comparar_i == comparar_j and comparar_i != "":
                        group_ids[j] = curr
                    continue 

                # --- 3ª REGRA: DISTÂNCIA GEOGRÁFICA (Casas comuns) ---
                num_j = "".join(filter(str.isdigit, str(row_j['Num_Casa'])))
                
                try:
                    distancia = geodesic(coord_i, (row_j['Latitude'], row_j['Longitude'])).meters
                    if distancia <= 100 and num_i == num_j and num_i != "":
                        # Se as ruas forem iguais ou similares
                        if rua_i == rua_j or is_gen_i or eh_nome_rua_generico(rua_j):
                            group_ids[j] = curr
                        elif SequenceMatcher(None, rua_i, rua_j).ratio() > 0.90:
                            group_ids[j] = curr
                except: pass

            curr += 1

    # No final do seu Passo 2, antes do Passo 3:
    df['GroupID'] = group_ids

    # --- GERAÇÃO DO DEBUG ATUALIZADO ---
    try:
        # Criamos as colunas de debug se elas não existirem (evita erro se não entrar no loop de condo)
        if 'Debug_Bloco_Planilha' not in df.columns:
            df['Debug_Bloco_Planilha'] = df['Bloco'] # Fallback para o bloco bruto

        colunas_debug = [
            'GroupID', 
            'Sequence', 
            'Destination Address', # Endereço original
            'Endereco_Formatado',  # Como o código transformou
            'Rua_Base', 
            'Num_Casa', 
            'Debug_Bloco_Planilha', # O que a regex extraiu para comparar
            'Tem_Minha_Nota', 
            'Separar_Bloco'
        ]
        df[colunas_debug].to_csv("debug_processamento.csv", index=False, encoding='utf-8-sig', sep=';')
        print("Debug salvo com sucesso em debug_processamento.csv")
    except Exception as e: 
        print(f"Erro ao gerar debug: {e}")

    # =========================================================
    # PASSO 3: AGRUPAMENTO E FORMATAÇÃO FINAL
    # =========================================================
    df_agrupado = df.groupby('GroupID').agg({
        'Sequence': lambda x: list(x),
        'Endereco_Formatado': 'first',
        'Bairro': 'first',
        'City': 'first',
        'Zipcode/Postal code': 'first',
        'Latitude': 'first',
        'Longitude': 'first',
        'Num_Casa': 'first',
        'Rua_Base': 'first',
        'Comp_Padrao': 'first'
    }).reset_index(drop=True)

    df_agrupado['Sequence'] = df_agrupado.apply(lambda row: aplicar_formatacao_final(row, notas_vivas), axis=1)
    df_agrupado = df_agrupado.rename(columns={'Endereco_Formatado': 'Destination Address'})
    
    # Emoji visual para itens agrupados
    df_agrupado['Destination Address'] = df_agrupado['Destination Address'].apply(
        lambda x: f"📍 {x}" if not str(x).startswith("📍") else x
    )

    return df_agrupado

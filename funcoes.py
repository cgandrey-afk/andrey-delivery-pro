import pandas as pd
import numpy as np
import json
import os
from difflib import SequenceMatcher
from num2words import num2words
from geopy.distance import geodesic
import re

OBS_FILE = "observacoes.json"
CONDO_FILE = "condominios.json"

# -----------------------------
# FUNÇÕES DE CARREGAMENTO
# -----------------------------
def carregar_obs():
    if os.path.exists(OBS_FILE):
        try:
            with open(OBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_obs(dic_obs):
    with open(OBS_FILE, "w", encoding="utf-8") as f:
        json.dump(dic_obs, f, indent=4, ensure_ascii=False)

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_json(dados, arquivo):
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar JSON: {e}")

# -----------------------------
# LIMPEZA E EXTRAÇÃO
# -----------------------------

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
    t = str(texto).upper().replace(',', ' ')
    
    # Regex melhorado: busca BL ou BLC ou BLOCO e pega o que vem depois
    # O ?: faz com que ele ignore a palavra "BLOCO" e pegue só o valor (A, B, 1, etc)
    bl_match = re.search(r'\b(?:BLOCO|BLC|BL)\s*([A-Z0-9]+)\b', t)
    tr_match = re.search(r'\b(?:TORRE|T)\s*([A-Z0-9]+)\b', t)
    
    partes = []
    if bl_match:
        partes.append(f"BL {bl_match.group(1)}")
    if tr_match:
        partes.append(f"TORRE {tr_match.group(1)}")
        
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
    
    # 2. Lista de prefixos de bairro e suas abreviações
    # Adicionamos as variações mais comuns encontradas em planilhas de entrega
    prefixos = {
        "JARDIM": ["JD", "JARD", "JARDIM"],
        "PARQUE": ["PQ", "PRQ", "PARQUE"],
        "VILA": ["V", "VL", "VILA"],
        "RESIDENCIAL": ["RES", "RESI", "RESIDENCIAL"],
        "CONJUNTO": ["CONJ", "CJ", "CONJUNTO"],        
        "CHACARA": ["CH", "CHAC", "CHACARA"],
        "LOTEAMENTO": ["LOT", "LOTEAMENTO"],
        "BOSQUE": ["BQ", "BSQ", "BOSQUE"],
        "SETOR": ["SEC", "SETOR"]
    }

    bairro = str(bairro_oficial).upper().strip() if pd.notna(bairro_oficial) else ""
    
    if bairro:
        # Remove o nome do bairro completo
        t = t.replace(bairro, "")
        
        # Remove as variações (Ex: Se o bairro é JARDIM AMENDOLA, remove JD AMENDOLA)
        for nome_cheio, abrevs in prefixos.items():
            # Se o bairro começa com um dos nomes cheios (ex: JARDIM)
            if bairro.startswith(nome_cheio):
                nome_base_bairro = bairro.replace(nome_cheio, "").strip()
                for abrev in abrevs:
                    t = t.replace(f"{abrev} {nome_base_bairro}", "")
            
            # Caso o bairro oficial já venha abreviado (ex: JD AMENDOLA)
            for abrev in abrevs:
                if bairro.startswith(abrev + " "):
                    nome_base_bairro = bairro.replace(abrev + " ", "").strip()
                    t = t.replace(f"{nome_cheio} {nome_base_bairro}", "")

    # 3. Limpeza de espaços duplos gerados pelos replaces
    t = re.sub(r'\s+', ' ', t).strip()

    # 4. Remove o número e tudo o que vem depois para sobrar só o NOME da rua
    # Importante: A regex \s\d+ evita cortar nomes de rua que tem números (RUA 10)
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
    # Remove pontuação antes de começar
    t = str(texto).upper().replace(',', ' ').replace('.', ' ').strip()
    
    subs = {r'\bAV\b': 'AVENIDA', r'\bR\b': 'RUA', r'\bDR\b': 'DOUTOR', r'\bPROF\b': 'PROFESSOR'}
    for p, s in subs.items(): 
        t = re.sub(p, s, t)
        
    # Pega apenas o que vem antes do número
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
    # 1. Preparação dos dados
    rua_planilha = str(row['Rua_Base']).upper().strip()
    num_planilha = str(row['Num_Casa']).upper().strip()
    end_original = normalizar_termos_condo(row['Destination Address'])
    
    # --- LISTA DE PALAVRAS QUE SÃO "RUA PURA" ---
    # Se aparecer qualquer uma dessas, o sistema PARA e não coloca "CONDOMINIO"
    travas_rua = ["VIELA", "CAMINHO", "CASA", "TERREO", "FUNDOS", "GARAGEM", "LOJA", "SALA"]
    
    if any(p in end_original for p in travas_rua):
        return montar_endereco_limpo(end_original, rua_planilha, num_planilha)

    # 2. REGRAS DO SEU CADASTRO (Aba 3) - Mantêm a prioridade alta
    for nome_grupo, info in db_condos.items():
        if info.get('tipo') == "separado_por_bloco":
            for portaria_cadastrada in info.get('portarias', []):
                p_cad_norm = normalizar_termos_condo(portaria_cadastrada)
                if rua_planilha in p_cad_norm and num_planilha in p_cad_norm:
                    termo_cadastro = p_cad_norm.replace(rua_planilha, "").replace(num_planilha, "").strip()
                    if termo_cadastro and f" {termo_cadastro}" in f" {end_original}":
                        return portaria_cadastrada

    # 3. REGRAS DE MULTI-RUAS (Aba 3)
    for info in db_condos.values():
        if info.get('tipo') == "multi_ruas":
            enderecos_lista = [normalizar_termos_condo(e) for e in info.get('enderecos', [])]
            if normalizar_termos_condo(f"{rua_planilha} {num_planilha}") in enderecos_lista:
                return str(info.get('portaria', '')).upper()

    # 4. IDENTIFICA CONDOMÍNIO (APENAS COM PALAVRAS CHAVE REAIS)
    # Removi as regex de "Letra+Numero" que causavam falsos positivos (como o EO de Terreo)
    termos_condominio = [
        r'\bAP\b', r'\bAPT\b', r'\bAPTO\b', r'\bAPARTAMENTO\b',
        r'\bBL\b', r'\bBLC\b', r'\bBLOCO\b', r'\bTORRE\b', 
        r'\bEDIFICIO\b', r'\bED\b', r'\bCONDOMINIO\b', r'\bCD\b'
    ]
    
    if any(re.search(p, end_original) for p in termos_condominio):
        return f"{rua_planilha}, {num_planilha} CONDOMINIO"

    # 5. SE NÃO CAIU EM NADA ACIMA, É RUA COMUM
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

def processar_caso_geral(texto_original, rua, num):
    """Função auxiliar para montar o endereço sem a palavra CONDOMINIO"""
    sobra = texto_original.replace(rua, "").replace(num, "").strip()
    sobra = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', sobra) 
    
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

# -----------------------------
# PROCESSAMENTO PRINCIPAL
# -----------------------------
def processar_agrupamento(df_bruto, notas_vivas, db_condos):
    df = df_bruto.copy()
    
    # 1. Preparação de colunas base
    df['Destination Address'] = df['Destination Address'].apply(converter_numero_da_rua_ate_100)
    df['Destination Address'] = df['Destination Address'].apply(limpar_duplicidade_numero)
    df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)
    df['Rua_Base'] = df.apply(lambda r: limpar_rua_com_bairro(r['Destination Address'], r['Bairro']), axis=1)
    df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
    df['Bloco'] = df['Destination Address'].apply(extrair_bloco)

    # 2. Identificação de Condomínios e Notas
    # Aqui o sistema decide se vira "CONDOMINIO", se usa o Bloco (Aba 3) ou se mantém o original (Casa/Viela)
    df['Separar_Bloco'] = df.apply(lambda r: verificar_separacao_bloco(r, db_condos), axis=1)
    df['Endereco_Formatado'] = df.apply(lambda r: formatar_endereco_agrupado(r, db_condos), axis=1)
    
    def verificar_nota(row):
        for chave in notas_vivas.keys():
            try:
                r, n, c = chave.split('|')
                if row['Num_Casa'] == n and row['Comp_Padrao'] == c and SequenceMatcher(None, row['Rua_Base'], r).ratio() > 0.8:
                    return True
            except: continue
        return False
    df['Tem_Minha_Nota'] = df.apply(verificar_nota, axis=1)

    # 3. Lógica de Agrupamento Inteligente (IDs)
    group_ids = np.zeros(len(df))
    curr = 1
    for i in range(len(df)):
        if group_ids[i] == 0:
            group_ids[i] = curr
            for j in range(i+1, len(df)):
                
                # Dados para comparação
                end_i = str(df.iloc[i]['Endereco_Formatado']).upper()
                end_j = str(df.iloc[j]['Endereco_Formatado']).upper()
                
                # --- PASSO 1: REGRA DE OURO (CADASTRO MANUAL / ABA 3) ---
                # Se um dos dois for um condomínio com separação por bloco/portaria,
                # a comparação é EXATA. Se o nome formatado for diferente, NÃO JUNTA.
                if df.iloc[i]['Separar_Bloco'] or df.iloc[j]['Separar_Bloco']:
                    if end_i == end_j:
                        group_ids[j] = curr
                    continue # Pula para o próximo 'j', ignorando a trava de 20m

                # --- PASSO 2: FILTRO DE NOTAS ---
                if df.iloc[i]['Tem_Minha_Nota'] != df.iloc[j]['Tem_Minha_Nota']:
                    continue

                # --- PASSO 3: TRAVA GEOGRÁFICA (20 METROS) ---
                coord_i = (df.iloc[i]['Latitude'], df.iloc[i]['Longitude'])
                coord_j = (df.iloc[j]['Latitude'], df.iloc[j]['Longitude'])
                
                distancia = 999
                try:
                    distancia = geodesic(coord_i, coord_j).meters
                except:
                    pass

                # Se estiver a mais de 20m, verificamos se o Bairro/CEP batem (Segurança)
                mesma_localidade = False
                if distancia <= 20:
                    mesma_localidade = True
                else:
                    b_i, b_j = str(df.iloc[i]['Bairro']).upper(), str(df.iloc[j]['Bairro']).upper()
                    c_i, c_j = str(df.iloc[i]['Zipcode/Postal code']), str(df.iloc[j]['Zipcode/Postal code'])
                    if b_i == b_j or c_i == c_j:
                        mesma_localidade = True

                if not mesma_localidade:
                    continue

                # --- PASSO 4: COMPARAÇÃO DE NOMES (VIELA / RUA / NÚMERO) ---
                
                # Função interna para extrair apenas os números (ex: 7B vira 7)
                def apenas_numeros(s):
                    return "".join(filter(str.isdigit, str(s)))

                num_i_puro = apenas_numeros(df.iloc[i]['Num_Casa'])
                num_j_puro = apenas_numeros(df.iloc[j]['Num_Casa'])
                rua_i = str(df.iloc[i]['Rua_Base']).upper().strip()
                rua_j = str(df.iloc[j]['Rua_Base']).upper().strip()

                # 1. Regra Especial para VIELA / CAMINHO
                # Agora ela aceita 7 e 7B se a Viela/Rua for a mesma
                if any(p in end_i for p in ["VIELA", "CAMINHO"]):
                    # Se o número base for igual (7 == 7) e a rua/viela for similar
                    if num_i_puro == num_j_puro and num_i_puro != "":
                        if rua_i == rua_j or SequenceMatcher(None, rua_i, rua_j).ratio() > 0.85:
                            group_ids[j] = curr
                            continue # Juntou, vai para o próximo

                # 2. Regra Geral (Casas de rua, Prédios não cadastrados)
                # Também aplicamos a lógica de número puro para juntar 7 e 7B na mesma rua
                if num_i_puro == num_j_puro and num_i_puro != "":
                    if rua_i == rua_j or SequenceMatcher(None, rua_i, rua_j).ratio() > 0.90:
                        group_ids[j] = curr
                
            curr += 1

    df['GroupID'] = group_ids

    # 4. Agrupamento Final (O que o app.py vai receber)
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

    # 5. Formatação Final de Exibição
    df_agrupado['Sequence'] = df_agrupado.apply(lambda row: aplicar_formatacao_final(row, notas_vivas), axis=1)
    
    # Adiciona o ícone 📍 apenas na visualização final para não atrapalhar a lógica acima
    df_agrupado = df_agrupado.rename(columns={'Endereco_Formatado': 'Destination Address'})
    df_agrupado['Destination Address'] = df_agrupado['Destination Address'].apply(
        lambda x: f"📍 {x}" if not str(x).startswith("📍") else x
    )

    return df_agrupado

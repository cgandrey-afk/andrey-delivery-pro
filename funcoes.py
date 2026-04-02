import pandas as pd
import numpy as np
import re
import json
import os
from difflib import SequenceMatcher

OBS_FILE = "observacoes.json"
CONDO_FILE = "condominios.json"

# --- FUNÇÕES DE CARREGAMENTO E SALVAMENTO ---

def carregar_obs():
    if os.path.exists(OBS_FILE):
        try:
            with open(OBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def salvar_obs(dic_obs):
    with open(OBS_FILE, "w", encoding="utf-8") as f:
        json.dump(dic_obs, f, indent=4, ensure_ascii=False)

def carregar_json(arquivo):
    if os.path.exists(arquivo):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def salvar_json(dados, arquivo):
    """Salva o dicionário de dados em um arquivo JSON."""
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar JSON: {e}")

# --- FUNÇÕES DE LIMPEZA E EXTRAÇÃO ---

def sao_ruas_similares(rua1, rua2):
    # Se forem idênticas, ok
    if rua1 == rua2: return True
    # Se forem 85% parecidas (ex: Umberto Vetoratto vs Umberto Vettorato), ok
    return SequenceMatcher(None, rua1, rua2).ratio() > 0.85

def limpar_duplicidade_numero(texto):
    if pd.isna(texto): return ""
    texto = str(texto).strip()
    padrao_repetido = r'\b(\d+)[\s,.]+\1\b'
    texto_limpo = re.sub(padrao_repetido, r'\1', texto)
    return texto_limpo.replace(', ,', ',').replace('  ', ' ')

def extrair_numero(texto):
    if pd.isna(texto): return ""
    texto_str = str(texto).strip()
    
    # Pega a PRIMEIRA sequência de números que aparece após um espaço
    # Ex: "Sylvio Carvalhaes 150, A34" -> Pega o 150 e para.
    match = re.search(r'\s(\d+)\b', texto_str)
    if match:
        return match.group(1)
    return ""
    
def normalizar_rua(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper().strip()
    
    subs = {
        r'\bAV\b': 'AVENIDA', r'\bR\b': 'RUA', r'\bEST\b': 'ESTRADA',
        r'\bAL\b': 'ALAMEDA', r'\bPC\b': 'PRACA', r'\bPROF\b': 'PROFESSOR',
        r'\bDR\b': 'DOUTOR', r'\bJD\b': 'JARDIM', r'\.': ''
    }
    for padrao, sub in subs.items():
        t = re.sub(padrao, sub, t)
    
    # Corta o texto assim que encontrar o primeiro número
    # Isso remove o "150, A34" do nome da rua
    partes = re.split(r'\s\d+', t, maxsplit=1)
    rua_limpa = partes[0].strip().replace(',', '')
    
    return rua_limpa

def limpar_para_agrupamento(rua, numero):
    """Cria a chave radical 'RUA, NUMERO' para ignorar lixo no final."""
    if not rua or not numero: return ""
    return f"{rua}, {numero}".strip().upper()

def formatar_endereco_condo(texto):
    """Usada na interface de condomínios para padronizar entradas."""
    rua = normalizar_rua(texto)
    num = extrair_numero(texto)
    return f"{rua}, {num}" if rua and num else str(texto).upper().strip()

def extrair_complemento_puro(texto):
    if pd.isna(texto): return ""
    t = str(texto).upper().strip()
    match_palavra = re.search(r'\b(APT|APTO|AP|APARTAMENTO|BLOCO|BL|SL|SALA|FUNDOS|CASA|TORRE)\b.*', t)
    if match_palavra: return match_palavra.group(0).strip()
    return ""

def padronizar_complemento(texto):
    if not texto: return ""
    t = str(texto).upper().strip().replace('-', '')
    t = re.sub(r'\b(APARTAMENTO|APTO|APT)\b', 'AP', t)
    t = re.sub(r'\b(BLOCO)\b', 'BL', t)
    return t.replace('.', '').replace('  ', ' ')

# --- FORMATAÇÃO VISUAL ---

def formatar_sequencia_visual(lista_seq):
    numeros = []
    contagem_adds = 0
    
    for s in lista_seq:
        s_str = str(s).strip()
        if s_str == "-" or s_str == "":
            contagem_adds += 1
            continue
            
        num_limpo = "".join(filter(str.isdigit, s_str.split('.')[0].split('-')[0]))
        if num_limpo:
            numeros.append(int(num_limpo))
        else:
            contagem_adds += 1

    texto_numeros = ""
    total_numerados = 0
    
    if numeros:
        numeros = sorted(list(set(numeros)))
        total_numerados = len(numeros)
        
        ranges = []
        if total_numerados > 0:
            start, last = numeros[0], numeros[0]
            for n in numeros[1:]:
                if n == last + 1:
                    last = n
                else:
                    # Regra do "e" para apenas 2 pacotes seguidos
                    if last == start + 1:
                        ranges.append(f"{start} e {last}")
                    else:
                        ranges.append(f"{start} ao {last}" if start != last else str(start))
                    start = last = n
            
            # Fecha o último range com a regra do "e"
            if last == start + 1:
                ranges.append(f"{start} e {last}")
            else:
                ranges.append(f"{start} ao {last}" if start != last else str(start))
            
            texto_numeros = ", ".join(ranges)

    total_geral = total_numerados + contagem_adds
    
    # Se só tem 1 pacote no total, não mostra a contagem final
    if total_geral <= 1:
        resultado = texto_numeros if texto_numeros else "1 Add"
        return f"📦 Pacotes: {resultado}"

    # Monta o texto dos ADDS
    texto_adds = ""
    if contagem_adds > 0:
        label_add = "Add" if contagem_adds == 1 else "Adds"
        prefixo = " + " if texto_numeros else ""
        texto_adds = f"{prefixo}{contagem_adds} {label_add}"

    # Monta o texto do Total (Apenas para 2 ou mais)
    texto_total = f" | Total: {total_geral} Pacotes"

    return f"📦 Pacotes: {texto_numeros}{texto_adds}{texto_total}"

def aplicar_formatacao_final(row, notas_vivas):
    texto_seq = formatar_sequencia_visual(row['Sequence'])
    r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
    nota_encontrada = ""
    for chave_s, nota_s in notas_vivas.items():
        try:
            partes_s = chave_s.split('|')
            if len(partes_s) == 3:
                r_s, n_s, c_s = partes_s
                if n_p == n_s and c_p == c_s and SequenceMatcher(None, r_p, r_s).ratio() > 0.8:
                    nota_encontrada = nota_s
                    break
        except: continue
    return f"⚠️ {nota_encontrada} | {texto_seq}" if nota_encontrada else texto_seq

# --- FUNÇÃO MESTRA ---

def processar_agrupamento(df_bruto, notas_vivas, db_condos):
    df = df_bruto.copy()
    
    # 1. Limpezas Iniciais e Extração
    df['Destination Address'] = df['Destination Address'].apply(limpar_duplicidade_numero)
    df['Num_Casa'] = df['Destination Address'].apply(extrair_numero)
    df['Rua_Base'] = df['Destination Address'].apply(normalizar_rua)
    df['Comp_Padrao'] = df['Destination Address'].apply(extrair_complemento_puro).apply(padronizar_complemento)
    
    # Chave para buscas rápidas
    df['Chave_Rua_Num'] = df.apply(lambda r: limpar_para_agrupamento(r['Rua_Base'], r['Num_Casa']), axis=1)

    # 2. Verificar Notas
    def verificar_nota(row):
        r_p, n_p, c_p = row['Rua_Base'], row['Num_Casa'], row['Comp_Padrao']
        for chave_s in notas_vivas.keys():
            try:
                p = chave_s.split('|')
                if len(p) == 3 and n_p == p[1] and c_p == p[2] and SequenceMatcher(None, r_p, p[0]).ratio() > 0.8:
                    return True
            except: continue
        return False
    df['Tem_Minha_Nota'] = df.apply(verificar_nota, axis=1)

    # 3. Definir Destinos (Regras de Condomínio da Aba 3)
    def definir_destino(row):
        chave = f"{row['Rua_Base']}, {row['Num_Casa']}"
        for principal, info in db_condos.items():
            membros = info.get('membros', [])
            if chave == principal or chave in membros:
                if info.get('tipo') == "Varios Condomínios com 1 Portaria":
                    return f"📍 {principal} (PORTARIA)"
                if info.get('tipo') == "Varias portaria de 1 condominio":
                    return "REGRA_SEPARAR"
        return row['Destination Address']

    df['Destino_Agrupamento'] = df.apply(definir_destino, axis=1)

    # 4. LOOP DE AGRUPAMENTO INTELIGENTE (Onde você deve colar o código)
    group_ids = np.zeros(len(df))
    curr = 1
    for i in range(len(df)):
        if group_ids[i] == 0:
            group_ids[i] = curr
            for j in range(i + 1, len(df)):
                # Bloqueio por nota: Se um tem nota e o outro não, não junta
                if df.iloc[i]['Tem_Minha_Nota'] != df.iloc[j]['Tem_Minha_Nota']:
                    continue
                
                # --- INÍCIO DA NOVA LÓGICA ---
                # 1. Os números das casas TÊM que ser iguais
                mesmo_numero = (df.iloc[i]['Num_Casa'] == df.iloc[j]['Num_Casa'] and df.iloc[i]['Num_Casa'] != "")
                
                # 2. As ruas têm que ser parecidas (Vetoratto vs Vettorato)
                mesma_rua = sao_ruas_similares(df.iloc[i]['Rua_Base'], df.iloc[j]['Rua_Base'])
                
                # 3. Ou se o destino final for o mesmo (Regras da Aba 3)
                mesmo_destino = (df.iloc[i]['Destino_Agrupamento'] == df.iloc[j]['Destino_Agrupamento'])
                
                # SE O NÚMERO É IGUAL E A RUA É PARECIDA -> JUNTA TUDO!
                if (mesmo_numero and mesma_rua) or mesmo_destino:
                    # Regra de separação por torres (Aba 3)
                    if df.iloc[i]['Destino_Agrupamento'] == "REGRA_SEPARAR" or df.iloc[j]['Destino_Agrupamento'] == "REGRA_SEPARAR":
                        if df.iloc[i]['Comp_Padrao'] == df.iloc[j]['Comp_Padrao']:
                            group_ids[j] = curr
                    else:
                        # Se não for regra de separar, junta pelo número da casa + rua similar
                        group_ids[j] = curr
                # --- FIM DA NOVA LÓGICA ---
            curr += 1

    df['GroupID'] = group_ids
    return df
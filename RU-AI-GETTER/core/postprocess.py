import re

def clean_menu_text(text: str) -> str:
    """
    Limpa e padroniza o texto extraído do cardápio para facilitar o parsing posterior.
    - Remove múltiplas quebras de linha
    - Remove espaços duplicados
    - Corrige caracteres estranhos comuns do OCR
    - Remove linhas vazias
    """
    # Remove múltiplas quebras de linha
    text = re.sub(r'\n+', '\n', text)
    # Remove espaços duplicados
    text = re.sub(r' +', ' ', text)
    # Corrige caracteres comuns do OCR
    text = text.replace('|', 'I').replace('—', '-')
    # Remove caracteres estranhos comuns do OCR
    text = re.sub(r'[\u201c\u201d\u201e\u201f\u2026\u00a0]', '', text)
    # Remove linhas vazias
    text = '\n'.join([l.strip() for l in text.splitlines() if l.strip()])
    return text

def extract_dates_and_weekdays(text: str) -> list:
    """
    Extrai datas (no formato dd/mm/yyyy, dd/mm/yy, dd-mm-yyyy, dd-mm-yy, d/m/yyyy, etc) e dias da semana do texto.
    Retorna uma lista de tuplas: (data, dia_semana, linha)
    """
    # Regex para datas
    date_regex = r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)'
    # Regex para dias da semana (português, case-insensitive)
    weekdays = r'(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)[- ]*feira?'
    results = []
    for i, line in enumerate(text.splitlines()):
        date_match = re.search(date_regex, line)
        weekday_match = re.search(weekdays, line, re.IGNORECASE)
        if date_match or weekday_match:
            results.append((date_match.group(1) if date_match else None,
                            weekday_match.group(0).capitalize() if weekday_match else None,
                            line.strip()))
    return results

def associate_dates_weekdays(text: str) -> list:
    """
    Tenta associar datas e dias da semana presentes no texto.
    Retorna uma lista de tuplas (data, dia_semana, bloco_texto) para facilitar o parsing pela IA.
    """
    lines = text.splitlines()
    # Extrai todas as datas e dias da semana
    date_regex = r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)'
    weekdays = r'(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)[- ]*feira?'
    blocks = []
    current_date = None
    current_weekday = None
    buffer = []
    for line in lines:
        date_match = re.search(date_regex, line)
        weekday_match = re.search(weekdays, line, re.IGNORECASE)
        # Se encontrar uma nova data ou dia, fecha o bloco anterior
        if date_match or weekday_match:
            if buffer and (current_date or current_weekday):
                blocks.append((current_date, current_weekday, '\n'.join(buffer).strip()))
                buffer = []
            if date_match:
                current_date = date_match.group(1)
            if weekday_match:
                current_weekday = weekday_match.group(0).capitalize()
        buffer.append(line)
    # Adiciona o último bloco
    if buffer and (current_date or current_weekday):
        blocks.append((current_date, current_weekday, '\n'.join(buffer).strip()))
    return blocks

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            raw = f.read()
        print(clean_menu_text(raw))

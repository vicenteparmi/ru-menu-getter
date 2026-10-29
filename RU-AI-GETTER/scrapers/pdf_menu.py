"""Read the CCA and Joinville PDF tables without an AI provider."""
import datetime as dt
import re

NO_MEALS = 'Sem refeições disponíveis'
WEEKDAYS = ['Segunda-Feira', 'Terça-Feira', 'Quarta-Feira', 'Quinta-Feira', 'Sexta-Feira', 'Sábado', 'Domingo']


def clean(value):
    return ' '.join((value or '').split())


def dates_in_text(text):
    dates = {dt.datetime.strptime(value, '%d/%m/%Y').date()
             for value in re.findall(r'\b\d{2}/\d{2}/\d{4}\b', text)}
    match = re.search(r'Cardápio\s+de\s+(\d{1,2})(?:[./](\d{1,2}))?\s+[aà]\s+(\d{1,2})[./](\d{1,2})[./](\d{4})', text, re.I)
    if match:
        day1, month1, day2, month2, year = match.groups()
        end = dt.date(int(year), int(month2), int(day2))
        start = dt.date(int(year), int(month1 or month2), int(day1))
        if start > end and month1:
            start = start.replace(year=start.year - 1)
        if not 0 <= (end-start).days <= 6:
            raise ValueError('Unexpected PDF week range')
        dates.update(start + dt.timedelta(days=n) for n in range((end-start).days+1))
    return sorted(dates)


def payload(date, meals):
    return {'weekday': WEEKDAYS[date.weekday()], 'menu': [m or [NO_MEALS] for m in meals], 'timestamp': 0}


def joinville_table(table):
    if not table or any(len(row) != 7 for row in table):
        raise ValueError('Expected seven Joinville columns')
    rows = [i for i, row in enumerate(table) if all(re.fullmatch(r'\d{2}/\d{2}/\d{4}', clean(cell)) for cell in row)]
    if len(rows) != 1:
        raise ValueError('Expected one explicit Joinville date row')
    index = rows[0]
    dates = [dt.datetime.strptime(clean(v), '%d/%m/%Y').date() for v in table[index]]
    if dates[0].weekday() != 0 or dates != [dates[0]+dt.timedelta(days=n) for n in range(7)]:
        raise ValueError('Joinville dates do not form a Monday-Sunday week')
    breakfast = [i for i, row in enumerate(table) if clean(row[0]).startswith('CAFÉ DA MANHÃ')]
    main = [i for i, row in enumerate(table) if clean(row[0]).startswith('ALMOÇO / JANTAR')]
    if len(breakfast) != 1 or len(main) != 1 or not index < breakfast[0] < main[0]:
        raise ValueError('Joinville meal sections changed')
    result = {}
    for col, date in enumerate(dates):
        morning = [clean(row[col]) for row in table[breakfast[0]+1:main[0]] if clean(row[col])]
        if col >= 5 and not morning:
            morning = [clean(row[5]) for row in table[breakfast[0]+1:main[0]] if clean(row[5])]
        if 'SEM ATENDIMENTO' in morning:
            morning = []
        elif len(morning) < 3:
            raise ValueError('Incomplete Joinville breakfast')
        else:
            morning.append('Exclusivo para alunos isentos de pagamento')
        items = [clean(row[col]) for row in table[main[0]+1:] if clean(row[col])]
        if 'SEM ATENDIMENTO' in items:
            items = []
        elif len(items) < 5 or not any('Arroz' in item for item in items):
            raise ValueError('Incomplete Joinville lunch/dinner')
        result[date.isoformat()] = payload(date, [morning, items, items.copy()])
    return result


def cca_table(table, text):
    dates = dates_in_text(text)
    if len(dates) != 5 or dates[0].weekday() != 0 or dates[-1].weekday() != 4:
        raise ValueError('Expected explicit Monday-Friday CCA range')
    header = next((i for i, row in enumerate(table) if any('Segunda' in clean(v) for v in row)), None)
    if header is None or any(len(row) != 15 for row in table[header:]):
        raise ValueError('CCA column layout changed')
    result = {}
    for day, date in enumerate(dates):
        cells = [' '.join(clean(v) for v in row[day*3:day*3+3] if clean(v)) for row in table[header+1:]]
        items = [v for v in cells if v and v not in {'Saladas', 'Acompanhamentos', 'Carne', 'Sobremesa'}]
        if any(v.upper() in ('FERIADO', 'SEM ATENDIMENTO', 'FECHADO') for v in items):
            items = []
        elif len(items) < 5 or not any('Arroz' in item for item in items):
            raise ValueError('Incomplete CCA daily column')
        # CCA's weekly food table covers lunch/dinner, without breakfast items.
        result[date.isoformat()] = payload(date, [[], items, items.copy()])
    return result


def parse_pdf(pdf_bytes, campus):
    import pdfplumber
    pdf_bytes.seek(0)
    with pdfplumber.open(pdf_bytes) as pdf:
        page = pdf.pages[0]
        tables = page.extract_tables()
        if len(tables) != 1:
            raise ValueError('Expected one PDF menu table')
        return joinville_table(tables[0]) if campus == 'joinville' else cca_table(tables[0], page.extract_text() or '')

"""Read UTFPR's dated two-column PDF without a paid API.

Unknown layouts are rejected, so the existing Gemini parser can handle them.
Coordinates separate lunch/dinner; explicit labels delimit each dish.
"""
import re
import unicodedata
from datetime import date

import pdfplumber
from models import WEEKDAYS_PT, validate_menu_data


class UnsupportedLayout(ValueError):
    pass


LABELS = ('prato principal', 'opcao vegana', 'guarnicao i', 'guarnicao ii',
          'salada i', 'salada ii', 'molho para salada', 'sobremesa')


def normalized(value):
    value = ''.join(c for c in unicodedata.normalize('NFD', value.lower())
                    if unicodedata.category(c) != 'Mn')
    # Some Canva PDFs repeat every glyph in overprinted labels.
    first = value.split()[0] if value.split() else ""
    overprinted = len(first) > 2 and len(first) % 2 == 0 and all(first[i] == first[i + 1] for i in range(0, len(first), 2))
    words = []
    for word in value.split():
        if overprinted and len(word) % 2 == 0 and all(word[i] == word[i + 1] for i in range(0, len(word), 2)):
            word = word[::2]
        words.append(word)
    return ' '.join(words)


def parse_meal(text, heading):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or normalized(lines.pop(0)) != heading:
        raise UnsupportedLayout(f'Expected {heading} heading')
    items, pending, labels = [], [], []
    for line in lines:
        label = normalized(line)
        if label in LABELS:
            if not pending:
                raise UnsupportedLayout(f'Missing dish for {label}')
            value = ' '.join(pending)
            items.append(('Opção vegana: ' if label == 'opcao vegana' else '') + value)
            labels.append(label)
            pending = []
            if label == 'sobremesa':
                break
        else:
            pending.append(line)
    if tuple(labels) != LABELS:
        raise UnsupportedLayout(f'Unexpected dish labels: {labels}')
    return ['Arroz', 'Arroz integral', 'Feijão', *items, 'Suco (200 ml)']


def parse_pdf(path, today=None):
    today = today or date.today()
    result = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            # Only add accompaniments explicitly declared by this template.
            norm = normalized(text)
            if not all(part in norm for part in ('arroz integral e feijao', '200ml de suco')):
                raise UnsupportedLayout('Missing shared accompaniments')
            dates = [w for w in page.extract_words() if re.fullmatch(r'\d{2}/\d{2}', w['text'])]
            if not dates:
                raise UnsupportedLayout('No explicit dates')
            for i, word in enumerate(dates):
                day, month = map(int, word['text'].split('/'))
                candidates = []
                for year in (today.year - 1, today.year, today.year + 1):
                    try:
                        candidates.append(date(year, month, day))
                    except ValueError:
                        pass
                menu_date = min(candidates, key=lambda d: abs((d - today).days))
                if abs((menu_date - today).days) > 45 or menu_date.isoformat() in result:
                    raise UnsupportedLayout('Ambiguous or stale date')
                end = dates[i + 1]['top'] - 60 if i + 1 < len(dates) else page.bbox[3]
                start = word['bottom'] + 1
                left = page.crop((0, start, page.width / 2, end)).extract_text() or ''
                right = page.crop((page.width / 2, start, page.width, end)).extract_text() or ''
                # Cross-check the date with the source's weekday heading.
                header = page.crop((0, max(0, word['top'] - 60), page.width, word['bottom'])).extract_text() or ''
                expected = normalized(WEEKDAYS_PT[menu_date.weekday()]).replace('-feira', '')
                if expected not in normalized(header):
                    raise UnsupportedLayout('Source weekday/date mismatch')
                lunch = parse_meal(left, 'almoco')
                if menu_date.weekday() == 5 and normalized(right).startswith('legenda'):
                    dinner = ['Sem refeições disponíveis']
                else:
                    dinner = parse_meal(right, 'jantar')
                result[menu_date.isoformat()] = {
                    'menu': [['Sem refeições disponíveis'], lunch, dinner],
                    'weekday': WEEKDAYS_PT[menu_date.weekday()], 'timestamp': 0,
                }
    valid, data, errors = validate_menu_data(result)
    if not valid:
        raise UnsupportedLayout(str(errors))
    return data

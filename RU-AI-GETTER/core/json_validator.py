"""
Módulo para validação e estruturação de JSON de cardápios dos RUs.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Importação opcional do jsonschema
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("[INFO] jsonschema não disponível. Usando validação básica.")


@dataclass
class MenuDay:
    """Estrutura para um dia de cardápio."""
    date: str  # formato YYYY-MM-DD
    menu: List[List[str]]  # [café_da_manhã, almoço, jantar]
    timestamp: int
    weekday: str


def validate_date_format(date_str: str) -> bool:
    """Valida se a data está no formato YYYY-MM-DD correto."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_date_format(date_str: str) -> Optional[str]:
    """Normaliza diferentes formatos de data para YYYY-MM-DD."""
    # Remove espaços e caracteres especiais
    date_str = re.sub(r'[^\d/\-.]', '', date_str.strip())
    
    # Padrões comuns de data
    patterns = [
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', r'\1-\2-\3'),  # YYYY-M-D ou YYYY-MM-DD
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', r'\3-\2-\1'),  # DD/MM/YYYY
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', r'\3-\2-\1'), # DD.MM.YYYY
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', r'\3-\2-\1'),  # DD-MM-YYYY
    ]
    
    for pattern, replacement in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                if len(match.groups()) == 3:
                    year, month, day = match.groups()
                    if len(year) == 4:
                        formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        # Se o primeiro grupo não for ano, reorganizar
                        day, month, year = match.groups()
                        formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    # Validar a data
                    if validate_date_format(formatted_date):
                        return formatted_date
            except:
                continue
    
    return None


def get_weekday_in_portuguese(date_str: str) -> str:
    """Retorna o dia da semana em português para uma data."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = [
            "Segunda-Feira", "Terça-Feira", "Quarta-Feira", 
            "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"
        ]
        return weekdays[date_obj.weekday()]
    except:
        return "Segunda-Feira"  # fallback


# Constante para o texto padrão quando não há refeições
NO_MEALS_TEXT = "Sem refeições disponíveis"

def clean_menu_items(items: List[str]) -> List[str]:
    """Limpa e normaliza os itens do menu."""
    cleaned_items = []
    for item in items:
        if isinstance(item, str):
            # Remove espaços extras e quebras de linha
            clean_item = re.sub(r'\s+', ' ', item.strip())
            # Remove caracteres especiais no início/fim
            clean_item = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', clean_item)
            if clean_item:
                # Normalizar variações do texto "sem refeições"
                clean_item = normalize_no_meals_text(clean_item)
                cleaned_items.append(clean_item)
    return cleaned_items


def normalize_no_meals_text(text: str) -> str:
    """Normaliza variações do texto 'sem refeições disponíveis' para o formato padrão."""
    text_lower = text.lower().strip()
    
    # Padrões que indicam "sem refeições" (mais abrangentes)
    no_meals_patterns = [
        r'sem\s+refei[çc][õo]es?\s+dispon[íi]veis?',
        r'sem\s+refei[çc][õoão]es?\s+dispon[íi]veis?',
        r'n[ãa]o\s+h[áa]\s+refei[çc][õoão]es?',
        r'refei[çc][õoão]es?\s+n[ãa]o\s+dispon[íi]veis?',
        r'card[áa]pio\s+n[ãa]o\s+dispon[íi]vel',
        r'menu\s+n[ãa]o\s+dispon[íi]vel',
        r'menu\s+indispon[íi]vel',
        r'sem\s+informa[çc][õoão]es?',
        r'n[ãa]o\s+informado',
        r'dados\s+corrompidos?',
        r'n[ãa]o\s+foi\s+poss[íi]vel\s+processar',
        r'sem\s+refei[çc][ãa]o',
        r'refei[çc][ãa]o\s+n[ãa]o\s+dispon[íi]vel',
        r'sem\s+refei[cç]oes?\s+dispon[iv]veis?',
        # Padrões mais específicos para capturar variações
        r'^sem\s+refei[çc]oes?\s+disponiveis?$',
        r'^sem\s+refei[çc][ãa]o\s+disponivel$',
        r'^cardapio\s+indisponivel$',
        r'^menu\s+indisponivel$'
    ]
    
    for pattern in no_meals_patterns:
        if re.search(pattern, text_lower):
            return NO_MEALS_TEXT
    
    return text


def validate_menu_structure(menu_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida e corrige a estrutura do JSON do cardápio.
    Garante que siga o formato esperado.
    """
    validated_data = {}
    
    for date_key, day_data in menu_data.items():
        # Normalizar data
        normalized_date = normalize_date_format(date_key)
        if not normalized_date:
            print(f"[AVISO] Data inválida ignorada: {date_key}")
            continue
        
        # Garantir estrutura básica
        if not isinstance(day_data, dict):
            print(f"[AVISO] Dados inválidos para {date_key}, usando estrutura padrão")
            day_data = {
                "menu": [[NO_MEALS_TEXT]],
                "timestamp": 0,
                "weekday": get_weekday_in_portuguese(normalized_date)
            }
        
        # Validar e corrigir menu
        menu = day_data.get("menu", [])
        if not isinstance(menu, list):
            menu = [[NO_MEALS_TEXT]]
        
        # Garantir que o menu tenha pelo menos uma refeição
        if not menu:
            menu = [[NO_MEALS_TEXT]]
        
        # Normalizar cada refeição
        normalized_menu = []
        for meal in menu:
            if isinstance(meal, list):
                cleaned_items = clean_menu_items(meal)
                if not cleaned_items:
                    cleaned_items = [NO_MEALS_TEXT]
                normalized_menu.append(cleaned_items)
            elif isinstance(meal, str):
                # Se o item é uma string, transformar em lista
                cleaned_items = clean_menu_items([meal])
                normalized_menu.append(cleaned_items if cleaned_items else [NO_MEALS_TEXT])
        
        # Garantir estrutura mínima [café, almoço, jantar] ou pelo menos uma refeição
        if len(normalized_menu) == 0:
            normalized_menu = [[NO_MEALS_TEXT]]
        
        validated_data[normalized_date] = {
            "menu": normalized_menu,
            "timestamp": 0,  # Sempre 0 como especificado
            "weekday": get_weekday_in_portuguese(normalized_date)
        }
    
    return validated_data


def create_json_schema() -> Dict[str, Any]:
    """Cria o schema JSON para structured output."""
    return {
        "type": "object",
        "patternProperties": {
            r"^\d{4}-\d{2}-\d{2}$": {
                "type": "object",
                "properties": {
                    "menu": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "minItems": 1
                    },
                    "timestamp": {
                        "type": "integer",
                        "const": 0
                    },
                    "weekday": {
                        "type": "string",
                        "enum": [
                            "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                            "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"
                        ]
                    }
                },
                "required": ["menu", "timestamp", "weekday"],
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }


def extract_and_validate_json(response_text: str) -> Dict[str, Any]:
    """
    Extrai JSON da resposta e valida sua estrutura.
    Tenta múltiplas estratégias para extrair JSON válido.
    """
    # Estratégia 1: Buscar JSON entre chaves
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, response_text)
    
    for match in matches:
        try:
            # Remover comentários JSON (que não são válidos em JSON)
            clean_json = re.sub(r'//.*?\n', '\n', match)
            clean_json = re.sub(r'/\*[\s\S]*?\*/', '', clean_json)
            
            parsed_json = json.loads(clean_json)
            if isinstance(parsed_json, dict) and parsed_json:
                # Validar e corrigir estrutura
                validated_json = validate_menu_structure(parsed_json)
                if validated_json:
                    return validated_json
        except json.JSONDecodeError:
            continue
    
    # Estratégia 2: Buscar por blocos de código JSON
    code_block_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    code_matches = re.findall(code_block_pattern, response_text, re.IGNORECASE)
    
    for match in code_matches:
        try:
            clean_json = re.sub(r'//.*?\n', '\n', match)
            clean_json = re.sub(r'/\*[\s\S]*?\*/', '', clean_json)
            
            parsed_json = json.loads(clean_json)
            if isinstance(parsed_json, dict) and parsed_json:
                validated_json = validate_menu_structure(parsed_json)
                if validated_json:
                    return validated_json
        except json.JSONDecodeError:
            continue
    
    # Se nenhuma estratégia funcionou, criar estrutura mínima
    return create_fallback_response()


def create_fallback_response() -> Dict[str, Any]:
    """Cria uma resposta de fallback quando não é possível extrair JSON válido."""
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday = get_weekday_in_portuguese(date_str)
    
    return {
        date_str: {
            "menu": [["Não foi possível processar o cardápio"]],
            "timestamp": 0,
            "weekday": weekday
        }
    }


def validate_json_format(json_data: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Valida se o JSON está no formato correto para cardápios.
    
    Args:
        json_data: Dados JSON para validar
        strict: Se True, aplica validação mais rigorosa
    
    Returns:
        Tuple[bool, List[str]]: (é_válido, lista_de_erros)
    """
    errors = []
    
    # Verificar se é um dicionário
    if not isinstance(json_data, dict):
        errors.append("O JSON deve ser um objeto/dicionário")
        return False, errors
    
    # Verificar se tem pelo menos uma data
    if not json_data:
        errors.append("O JSON não pode estar vazio")
        return False, errors
    
    # Validar cada entrada de data
    for date_key, day_data in json_data.items():
        # Validar formato da data
        if not validate_date_format(date_key):
            errors.append(f"Data '{date_key}' não está no formato YYYY-MM-DD")
            continue
        
        # Validar estrutura do dia
        if not isinstance(day_data, dict):
            errors.append(f"Dados para {date_key} devem ser um objeto")
            continue
        
        # Verificar campos obrigatórios
        required_fields = ['menu', 'timestamp', 'weekday']
        for field in required_fields:
            if field not in day_data:
                errors.append(f"Campo '{field}' faltando para {date_key}")
        
        # Validar menu
        if 'menu' in day_data:
            menu = day_data['menu']
            if not isinstance(menu, list):
                errors.append(f"Menu para {date_key} deve ser uma lista")
            else:
                if not menu:
                    errors.append(f"Menu para {date_key} não pode estar vazio")
                
                for i, meal in enumerate(menu):
                    if not isinstance(meal, list):
                        errors.append(f"Refeição {i} para {date_key} deve ser uma lista")
                    else:
                        if not meal:
                            errors.append(f"Refeição {i} para {date_key} não pode estar vazia")
                        
                        for j, item in enumerate(meal):
                            if not isinstance(item, str):
                                errors.append(f"Item {j} da refeição {i} para {date_key} deve ser string")
                            elif strict and not item.strip():
                                errors.append(f"Item {j} da refeição {i} para {date_key} não pode estar vazio")
        
        # Validar timestamp
        if 'timestamp' in day_data:
            if not isinstance(day_data['timestamp'], int):
                errors.append(f"Timestamp para {date_key} deve ser um inteiro")
            elif day_data['timestamp'] != 0:
                errors.append(f"Timestamp para {date_key} deve ser 0")
        
        # Validar weekday
        if 'weekday' in day_data:
            valid_weekdays = [
                "Segunda-Feira", "Terça-Feira", "Quarta-Feira",
                "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"
            ]
            if day_data['weekday'] not in valid_weekdays:
                errors.append(f"Dia da semana '{day_data['weekday']}' inválido para {date_key}")
            elif strict:
                # Verificar se o dia da semana corresponde à data
                expected_weekday = get_weekday_in_portuguese(date_key)
                if day_data['weekday'] != expected_weekday:
                    errors.append(f"Dia da semana '{day_data['weekday']}' não corresponde à data {date_key} (esperado: {expected_weekday})")
    
    return len(errors) == 0, errors


def validate_with_jsonschema(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida JSON usando jsonschema para validação mais rigorosa (se disponível).
    """
    errors = []
    
    if not HAS_JSONSCHEMA:
        # Fallback para validação básica se jsonschema não estiver disponível
        return validate_json_format(json_data, strict=True)
    
    try:
        schema = create_json_schema()
        # Validar usando jsonschema
        jsonschema.validate(json_data, schema)
        
        # Validação adicional específica do domínio
        for date_key, day_data in json_data.items():
            # Verificar se a data é válida
            try:
                datetime.strptime(date_key, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Data '{date_key}' inválida")
            
            # Verificar se o dia da semana corresponde à data
            expected_weekday = get_weekday_in_portuguese(date_key)
            if day_data.get('weekday') != expected_weekday:
                errors.append(f"Dia da semana inconsistente para {date_key}")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        if HAS_JSONSCHEMA and "ValidationError" in str(type(e)):
            errors.append(f"Erro de schema: {e.message}")
        else:
            errors.append(f"Erro na validação: {str(e)}")
        return False, errors


def repair_json_format(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tenta reparar automaticamente problemas comuns no JSON.
    """
    if not isinstance(json_data, dict):
        return create_fallback_response()
    
    repaired_data = {}
    
    for date_key, day_data in json_data.items():
        # Tentar normalizar a data
        normalized_date = normalize_date_format(date_key)
        if not normalized_date:
            print(f"[REPARO] Ignorando data inválida: {date_key}")
            continue
        
        # Garantir estrutura básica do dia
        if not isinstance(day_data, dict):
            day_data = {"menu": [[NO_MEALS_TEXT]], "timestamp": 0, "weekday": get_weekday_in_portuguese(normalized_date)}
        
        # Reparar menu
        menu = day_data.get("menu", [])
        if not isinstance(menu, list):
            menu = [["Formato de menu inválido"]]
        elif not menu:
            menu = [[NO_MEALS_TEXT]]
        
        repaired_menu = []
        for meal in menu:
            if isinstance(meal, list):
                cleaned_meal = []
                for item in meal:
                    item_str = str(item).strip()
                    if item_str:
                        # Normalizar texto de "sem refeições"
                        normalized_item = normalize_no_meals_text(item_str)
                        cleaned_meal.append(normalized_item)
                
                if not cleaned_meal:
                    cleaned_meal = [NO_MEALS_TEXT]
                repaired_menu.append(cleaned_meal)
            elif isinstance(meal, str) and meal.strip():
                normalized_item = normalize_no_meals_text(meal.strip())
                repaired_menu.append([normalized_item])
        
        if not repaired_menu:
            repaired_menu = [[NO_MEALS_TEXT]]
        
        # Construir entrada reparada
        repaired_data[normalized_date] = {
            "menu": repaired_menu,
            "timestamp": 0,
            "weekday": get_weekday_in_portuguese(normalized_date)
        }
    return repaired_data if repaired_data else create_fallback_response()


def comprehensive_json_validator(json_data: Dict[str, Any], auto_repair: bool = True) -> Tuple[bool, Dict[str, Any], List[str]]:
    """
    Validador abrangente que combina múltiplas estratégias de validação.
    
    Args:
        json_data: JSON para validar
        auto_repair: Se True, tenta reparar automaticamente
    
    Returns:
        Tuple[bool, Dict[str, Any], List[str]]: (é_válido, dados_processados, erros)
    """
    original_errors = []
    
    # SEMPRE aplicar normalização primeiro
    processed_data = validate_menu_structure(json_data)
    
    # Primeira validação - formato básico
    is_valid_basic, basic_errors = validate_json_format(processed_data, strict=False)
    original_errors.extend([f"[BÁSICO] {error}" for error in basic_errors])
    
    # Se auto_repair está ativado e há erros, tentar reparar
    if auto_repair and not is_valid_basic:
        print(f"[VALIDADOR] Tentando reparar {len(basic_errors)} erros...")
        processed_data = repair_json_format(processed_data)
        
        # Validar novamente após reparo
        is_valid_repaired, repaired_errors = validate_json_format(processed_data, strict=False)
        if is_valid_repaired:
            print("[VALIDADOR] Reparo bem-sucedido!")
            return True, processed_data, original_errors
        else:
            original_errors.extend([f"[PÓS-REPARO] {error}" for error in repaired_errors])
    
    # Validação com jsonschema (se disponível)
    try:
        is_valid_schema, schema_errors = validate_with_jsonschema(processed_data)
        if not is_valid_schema:
            original_errors.extend([f"[SCHEMA] {error}" for error in schema_errors])
    except Exception as e:
        original_errors.append(f"[SCHEMA] Falha na validação por schema: {e}")
    
    # Validação estrita final
    is_valid_strict, strict_errors = validate_json_format(processed_data, strict=True)
    if not is_valid_strict:
        original_errors.extend([f"[ESTRITO] {error}" for error in strict_errors])
    
    # Determinar se é válido o suficiente para uso
    critical_errors = [error for error in original_errors if any(keyword in error.lower() for keyword in ['faltando', 'vazio', 'inválido', 'corrompido'])]
    is_usable = len(critical_errors) == 0
    
    return is_usable, processed_data, original_errors


def test_json_validator():
    """
    Função para testar o validador com diferentes cenários.
    """
    print("=== TESTE DO VALIDADOR JSON ===\n")
    
    # Teste 1: JSON válido
    valid_json = {
        "2025-06-05": {
            "menu": [
                ["Pão francês", "Café com leite"],
                ["Arroz", "Feijão", "Bife acebolado", "Salada verde"],
                ["Sopa de legumes", "Pão integral"]
            ],
            "timestamp": 0,
            "weekday": "Quinta-Feira"
        }
    }
    
    print("1. Testando JSON válido:")
    is_valid, processed, errors = comprehensive_json_validator(valid_json)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
    if errors:
        print("   Avisos:", errors[:3])
    print()
    
    # Teste 2: JSON com problemas menores
    problematic_json = {
        "2025-06-06": {
            "menu": [
                [""],  # Item vazio
                ["Arroz", "Feijão", "Frango grelhado"],
                []  # Refeição vazia
            ],
            "timestamp": 0,
            "weekday": "Sexta-Feira"
        }
    }
    
    print("2. Testando JSON com problemas menores:")
    is_valid, processed, errors = comprehensive_json_validator(problematic_json)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
    print(f"   Erros encontrados: {len(errors)}")
    if errors:
        print("   Primeiros erros:", errors[:3])
    print()
    
    # Teste 3: JSON completamente inválido
    invalid_json = {
        "data-inválida": {
            "menu": "não é uma lista",
            "timestamp": "deveria ser inteiro",
            "weekday": "Dia-Inválido"
        }
    }
    
    print("3. Testando JSON completamente inválido:")
    is_valid, processed, errors = comprehensive_json_validator(invalid_json)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
    print(f"   Erros encontrados: {len(errors)}")
    print("   JSON reparado:", json.dumps(processed, ensure_ascii=False, indent=2)[:200] + "...")
    print()
    
    # Teste 4: String JSON malformada
    malformed_response = '''
    {
        "2025-06-07": {
            "menu": [
                ["Arroz", "Feijão"] // comentário inválido
            ],
            "timestamp": 0,
            "weekday": "Sábado"
        }
    }
    '''
    
    print("4. Testando extração de JSON malformado:")
    extracted = extract_and_validate_json(malformed_response)
    is_valid, processed, errors = comprehensive_json_validator(extracted)
    print(f"   Resultado: {'✅ VÁLIDO' if is_valid else '❌ INVÁLIDO'}")
    print(f"   JSON extraído e processado: {bool(extracted)}")
    print()


if __name__ == "__main__":
    test_json_validator()

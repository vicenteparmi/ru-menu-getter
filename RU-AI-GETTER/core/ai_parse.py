import requests
import os
import json

def parse_menu_with_ollama(text: str, model: str = "gemma3:4b", host: str = None, image_path: str = None) -> dict:
    """
    Envia o texto (e opcionalmente uma imagem) do cardápio para o Ollama (MCP) e retorna o JSON estruturado.
    """
    if host is None:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    # Importar validador JSON
    try:
        from core.json_validator import extract_and_validate_json, create_fallback_response
    except ImportError:
        print("[AVISO] json_validator não encontrado, usando método básico")
        extract_and_validate_json = None
        create_fallback_response = None
    
    # Prompt melhorado com instruções mais claras
    prompt = (
        "Você deve extrair e estruturar as informações de cardápio do restaurante universitário em formato JSON. "
        "Siga EXATAMENTE o formato especificado abaixo.\n\n"
        
        "REGRAS IMPORTANTES:\n"
        "1. Use APENAS o formato YYYY-MM-DD para datas\n"
        "2. Cada dia deve ter: menu (array de arrays), timestamp (sempre 0), weekday (dia da semana em português)\n"
        "3. O array 'menu' representa as refeições: [café da manhã/lanche, almoço, jantar]\n"
        "4. Se não houver informação para uma refeição, use EXATAMENTE ['Sem refeições disponíveis']\n"
        "5. Capitalize adequadamente os nomes dos pratos\n"
        "6. Mantenha opções vegetarianas/veganas quando presentes\n"
        "7. Inclua acompanhamentos e saladas quando mencionados\n\n"
        
        "FORMATO DE SAÍDA (JSON válido, sem comentários):\n"
        "{\n"
        '  "2025-06-05": {\n'
        '    "menu": [\n'
        '      ["Sem refeições disponíveis"],\n'
        '      ["Bife acebolado", "Opção vegana: hambúrguer de feijão", "Arroz", "Feijão", "Salada verde"],\n'
        '      ["Frango grelhado", "Opção vegetariana: lasanha de berinjela", "Purê de batata", "Salada mista"]\n'
        '    ],\n'
        '    "timestamp": 0,\n'
        '    "weekday": "Quinta-Feira"\n'
        '  }\n'
        "}\n\n"
        
        "TEXTO DO CARDÁPIO A SER PROCESSADO:\n" + text + "\n\n"
        
        "Retorne APENAS o JSON válido, sem texto adicional:"
    )
    
    data = {
        "model": model, 
        "prompt": prompt, 
        "stream": False,
        "options": {
            "temperature": 0.1,  # Baixa temperatura para mais consistência
            "top_p": 0.8,
            "top_k": 40,
        }
    }
    
    files = None
    if image_path:
        import base64
        try:
            with open(image_path, "rb") as imgf:
                img_b64 = base64.b64encode(imgf.read()).decode("utf-8")
            data["images"] = [img_b64]
        except Exception as e:
            print(f"[AVISO] Erro ao carregar imagem {image_path}: {e}")
    
    try:
        response = requests.post(
            f"{host}/api/generate",
            json=data,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        response_text = result.get('response', '')
        print(f"[DEBUG] Resposta do Ollama: {response_text[:500]}...")
        
        # Usar validador se disponível
        if extract_and_validate_json:
            return extract_and_validate_json(response_text)
        else:
            # Método básico de fallback
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("Nenhum JSON encontrado na resposta")
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
            
    except Exception as e:
        print(f"[ERRO] Falha no parsing com Ollama: {e}")
        if create_fallback_response:
            return create_fallback_response()
        else:
            raise ValueError(f"Falha ao extrair JSON da resposta do Ollama: {e}\nResposta: {response_text if 'response_text' in locals() else 'N/A'}")

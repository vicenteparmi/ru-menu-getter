import base64
import os
import json
from google import genai
from google.genai import types
import env_config

def format_menu_ai(content_text, pdf_paths=None, image_paths=None, system_instruction=None):
    """
    Recebe o conteúdo do cardápio (texto), lista de pdfs e imagens, envia para Gemini, retorna objeto formatado.
    """
    client = genai.Client(
        api_key=getattr(env_config, 'GEMINI_API_KEY', None)
    )

    model = "gemini-2.5-flash-lite"

    # Garante que content_text seja string
    if isinstance(content_text, list):
        content_text = content_text[0] if content_text else ""
    elif content_text is None:
        content_text = ""

    # Garante que pdf_paths e image_paths sejam listas
    pdf_paths = pdf_paths if pdf_paths is not None else []
    image_paths = image_paths if image_paths is not None else []

    contents = [content_text]

    # Adiciona PDFs via upload
    for pdf_path in pdf_paths:
        if pdf_path:
            try:
                uploaded_pdf = client.files.upload(file=pdf_path)
                contents.append(uploaded_pdf)
            except Exception as e:
                print(f"[AI_PARSE] Erro ao fazer upload do PDF {pdf_path}: {e}")

    # Adiciona imagens via upload
    for img_path in image_paths:
        if img_path:
            try:
                uploaded_img = client.files.upload(file=img_path)
                contents.append(uploaded_img)
            except Exception as e:
                print(f"[AI_PARSE] Erro ao fazer upload da imagem {img_path}: {e}")

    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
        ),
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text=system_instruction or "Formate o cardápio em JSON estruturado."),
        ],
    )

    response_str = ""
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                response_str += chunk.text
    except Exception as stream_err:
        print(f"[AI_PARSE] Erro durante streaming da resposta: {stream_err}")
        return None

    # Tenta converter para objeto JSON
    try:
        response_obj = json.loads(response_str)
        if isinstance(response_obj, dict) and "response" in response_obj:
            return json.loads(response_obj["response"])
        return response_obj
    except Exception as e:
        print(f"[AI_PARSE] Erro ao converter resposta: {e}\nResposta recebida: {response_str}")
        return None

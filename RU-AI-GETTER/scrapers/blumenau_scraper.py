# Scraper para o RU de Blumenau

import requests
from bs4 import BeautifulSoup, Tag
from PIL import Image
import pytesseract
import io
import re
import os
from datetime import datetime
from urllib.parse import urljoin
from .base_scraper import RestaurantScraper

class BlumenauScraper(RestaurantScraper):
    BASE_URL = "https://ru.blumenau.ufsc.br/cardapios/"

    def get_menu_text(self, date=None):
        html = self.fetch_html(self.BASE_URL)
        soup = BeautifulSoup(html, 'html.parser')
        # Busca links de imagem em todo o HTML (regex para png/jpg/jpeg)
        img_urls = re.findall(r'(https?://[^\s"\)]+\.(?:png|jpg|jpeg))', html, re.IGNORECASE)
        tried_urls = set()
        for url in img_urls:
            if url in tried_urls:
                continue
            tried_urls.add(url)
            try:
                resp = requests.get(url)
                resp.raise_for_status()
                image = Image.open(io.BytesIO(resp.content))
                # Salva a imagem para uso posterior (ex: IA multimodal)
                try:
                    saved_path = self.save_file(resp.content, 'cardapio_blumenau.png', 'binary')
                    if saved_path:
                        print(f"[DEBUG] Imagem salva em: {saved_path}")
                except Exception as e:
                    print(f"[DEBUG] Falha ao salvar imagem: {e}")
                text = pytesseract.image_to_string(image, lang='por')
                if len(text.strip()) > 30:
                    return text
            except Exception as e:
                print(f"[DEBUG] Falha ao tentar imagem direta: {url} - {e}")
                continue
        # Busca imagens que provavelmente são cardápio
        img_tags = soup.find_all('img')
        cardapio_imgs = [img for img in img_tags if isinstance(img, Tag) and img.get('src') and ('cardapio' in str(img.get('src', '')).lower() or 'menu' in str(img.get('src', '')).lower())]
        imgs_to_try = cardapio_imgs if cardapio_imgs else [img for img in img_tags if isinstance(img, Tag)]
        for img in imgs_to_try:
            img_url = img.get('src')
            if not img_url or img_url in tried_urls:
                continue
            tried_urls.add(img_url)
            if not str(img_url).startswith('http'):
                img_url = urljoin(self.BASE_URL, str(img_url))
            try:
                resp = requests.get(str(img_url))
                resp.raise_for_status()
                image = Image.open(io.BytesIO(resp.content))
                # Salva a imagem para uso posterior (ex: IA multimodal)
                try:
                    saved_path = self.save_file(resp.content, 'cardapio_blumenau.png', 'binary')
                    if saved_path:
                        print(f"[DEBUG] Imagem salva em: {saved_path}")
                except Exception as e:
                    print(f"[DEBUG] Falha ao salvar imagem: {e}")
                text = pytesseract.image_to_string(image, lang='por')
                # Se o texto extraído for razoável, retorna
                if len(text.strip()) > 30:
                    return text
            except Exception as e:
                print(f"[DEBUG] Falha ao tentar <img>: {img_url} - {e}")
                continue
        # Fallback: buscar PDF
        pdf_links = re.findall(r'(https?://[^\s"\)]+\.pdf)', html, re.IGNORECASE)
        for pdf_url in pdf_links:
            try:
                pdf_bytes = self.download_pdf(pdf_url)
                import pdfplumber
                with pdfplumber.open(pdf_bytes) as pdf:
                    text = "\n".join(page.extract_text() or '' for page in pdf.pages)
                if len(text.strip()) > 30:
                    return text
            except Exception as e:
                print(f"[DEBUG] Falha ao tentar PDF: {pdf_url} - {e}")
                continue
        raise Exception("Nenhuma imagem ou PDF de cardápio válido encontrado ou OCR falhou.")

    def get_menu_image_path(self):
        """
        Retorna o caminho da última imagem salva do cardápio, se existir.
        """
        return self.get_latest_download('cardapio_blumenau_*.png')

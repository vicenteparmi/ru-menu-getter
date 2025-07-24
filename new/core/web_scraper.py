import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import os

class WebScraper:
    def __init__(self, base_url, scrape_type, city_code, ru_name, save_params=None, selection_mode="last", content_selector=None):
        self.base_url = base_url
        self.scrape_type = scrape_type
        self.city_code = city_code
        self.ru_name = ru_name
        self.save_params = save_params or {}
        self.selection_mode = selection_mode
        self.content_selector = content_selector  # Ex: '#conteudo', '.cardapio', etc

    def fetch_html(self):
        resp = requests.get(self.base_url)
        resp.raise_for_status()
        return resp.text

    def save_file(self, content, filename):
        folder = self.save_params.get('folder', 'downloaded_files')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, 'wb') as f:
            f.write(content)
        return path

    def scrape(self, date=None):
        html = self.fetch_html()
        soup = BeautifulSoup(html, 'html.parser')
        result = {
            'city_code': self.city_code,
            'ru_name': self.ru_name,
            'files': [],
            'texts': []
        }

        # Limpa a pasta de arquivos antes de iniciar o scrape
        folder = self.save_params.get('folder', 'downloaded_files')
        if os.path.exists(folder):
            for f in os.listdir(folder):
                file_path = os.path.join(folder, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        if self.scrape_type == 'pdf':
            links = soup.find_all('a', href=True)
            pdf_links = []
            for a in links:
                if isinstance(a, Tag):
                    href = a.get('href')
                    if isinstance(href, str) and href.lower().endswith('.pdf'):
                        pdf_links.append(href)
            url = None
            if pdf_links:
                if self.selection_mode == "first":
                    url = pdf_links[0]
                elif self.selection_mode == "last":
                    url = pdf_links[-1]
                elif self.selection_mode == "by_date":
                    # Exemplo: selecionar por data (pode ser customizado)
                    url = pdf_links[-1]  # Default para último, pode ser ajustado
                else:
                    url = pdf_links[-1]
            if isinstance(url, str):
                full_url = url if url.startswith('http') else urljoin(self.base_url, url)
                resp = requests.get(full_url)
                resp.raise_for_status()
                filename = self.save_params.get('filename', f"cardapio_{self.ru_name}_{os.path.basename(str(url))}")
                path = self.save_file(resp.content, filename)
                result['files'].append(path)

        elif self.scrape_type == 'image':
            # Limpa a pasta de arquivos antes de iniciar o scrape
            folder = self.save_params.get('folder', 'downloaded_files')
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    file_path = os.path.join(folder, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            # Busca imagens apenas dentro do <article> principal
            article = soup.find('article')
            img_tags = article.find_all('img') if isinstance(article, Tag) else []
            img_links = []
            for img in img_tags:
                if isinstance(img, Tag):
                    src = img.get('src')
                    if isinstance(src, str):
                        # Ignora ícones comuns
                        if any(x in src.lower() for x in ['icon', 'logo', 'favicon', 'svg']):
                            continue
                        img_links.append(src)
            src = None
            if img_links:
                if self.selection_mode == "first":
                    src = img_links[0]
                elif self.selection_mode == "last":
                    src = img_links[-1]
                elif self.selection_mode == "by_date":
                    src = img_links[-1]  # Default para último, pode ser ajustado
                else:
                    src = img_links[-1]
            if isinstance(src, str):
                full_url = src if src.startswith('http') else urljoin(self.base_url, src)
                resp = requests.get(full_url)
                resp.raise_for_status()
                filename = self.save_params.get('filename', f"cardapio_{self.ru_name}_{os.path.basename(src)}")
                path = self.save_file(resp.content, filename)
                result['files'].append(path)

        elif self.scrape_type == 'pdf_or_image':
            links = soup.find_all('a', href=True)
            pdf_links = []
            for a in links:
                if isinstance(a, Tag):
                    href = a.get('href')
                    if isinstance(href, str) and href.lower().endswith('.pdf'):
                        pdf_links.append(href)
            url = None
            if pdf_links:
                if self.selection_mode == "first":
                    url = pdf_links[0]
                elif self.selection_mode == "last":
                    url = pdf_links[-1]
                elif self.selection_mode == "by_date":
                    url = pdf_links[-1]  # Default para último, pode ser ajustado
                else:
                    url = pdf_links[-1]
            if isinstance(url, str):
                full_url = url if url.startswith('http') else urljoin(self.base_url, url)
                resp = requests.get(full_url)
                resp.raise_for_status()
                filename = self.save_params.get('filename', f"cardapio_{self.ru_name}_{os.path.basename(url)}")
                path = self.save_file(resp.content, filename)
                result['files'].append(path)
            else:
                img_tags = soup.find_all('img')
                img_links = []
                for img in img_tags:
                    if isinstance(img, Tag):
                        src = img.get('src')
                        if isinstance(src, str):
                            img_links.append(src)
                src = None
                if img_links:
                    if self.selection_mode == "first":
                        src = img_links[0]
                    elif self.selection_mode == "last":
                        src = img_links[-1]
                    elif self.selection_mode == "by_date":
                        src = img_links[-1]  # Default para último, pode ser ajustado
                    else:
                        src = img_links[-1]
                if isinstance(src, str):
                    full_url = src if src.startswith('http') else urljoin(self.base_url, src)
                    resp = requests.get(full_url)
                    resp.raise_for_status()
                    filename = self.save_params.get('filename', f"cardapio_{self.ru_name}_{os.path.basename(src)}")
                    path = self.save_file(resp.content, filename)
                    result['files'].append(path)

        elif self.scrape_type == 'text':
            text_blocks = soup.find_all('p')
            for block in text_blocks:
                txt = block.get_text(strip=True)
                if txt and len(txt) > 20:
                    result['texts'].append(txt)

        return result
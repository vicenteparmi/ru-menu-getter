import requests
from bs4 import BeautifulSoup
import pdfplumber
import datetime
import re
import io
import os
from datetime import datetime as dt

class RestaurantScraper:
    """
    Classe base para scrapers de restaurantes. Permite fácil extensão para novos restaurantes.
    """
    def fetch_html(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def find_pdf_url(self, html, date=None):
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        pdf_links = [a['href'] for a in links if a['href'].lower().endswith('.pdf')]
        if not pdf_links:
            return None
        if date is None:
            date = datetime.date.today()

        def extract_date_from_link(link):
            match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{2,4})', link)
            if match:
                try:
                    parts = re.split(r'[./-]', match.group(1))
                    if len(parts[-1]) == 2:
                        parts[-1] = '20' + parts[-1]
                    return datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                except Exception:
                    return None
            return None

        pdf_links_with_dates = [(link, extract_date_from_link(link)) for link in pdf_links]
        pdf_links_with_dates = [x for x in pdf_links_with_dates if x[1] is not None]
        if not pdf_links_with_dates:
            return pdf_links[0]
        pdf_links_with_dates.sort(key=lambda x: abs((x[1] - date).days))
        return pdf_links_with_dates[0][0]

    def download_pdf(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return io.BytesIO(resp.content)

    def extract_text_from_pdf(self, pdf_bytes):
        with pdfplumber.open(pdf_bytes) as pdf:
            text = "\n".join(page.extract_text() or '' for page in pdf.pages)
        return text

    def get_downloads_dir(self):
        """Retorna o diretório de downloads, criando-o se necessário."""
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', 'downloaded_files')
        os.makedirs(downloads_dir, exist_ok=True)
        return downloads_dir

    def save_file(self, content, filename, file_type='binary'):
        """
        Salva um arquivo no diretório de downloads com timestamp.
        
        Args:
            content: Conteúdo do arquivo (bytes para binário, str para texto)
            filename: Nome base do arquivo (ex: 'cardapio_blumenau')
            file_type: 'binary' ou 'text'
        
        Returns:
            str: Caminho completo do arquivo salvo
        """
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        extension = self._get_file_extension(filename)
        if not extension:
            extension = '.png' if file_type == 'binary' else '.txt'
        
        # Remove extensão existente do filename se houver
        base_name = filename.split('.')[0]
        full_filename = f"{base_name}_{timestamp}{extension}"
        
        file_path = os.path.join(self.get_downloads_dir(), full_filename)
        
        try:
            mode = 'wb' if file_type == 'binary' else 'w'
            encoding = None if file_type == 'binary' else 'utf-8'
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            print(f"[DEBUG] Arquivo salvo em: {file_path}")
            return file_path
        except Exception as e:
            print(f"[DEBUG] Falha ao salvar arquivo: {e}")
            return None

    def _get_file_extension(self, filename):
        """Extrai a extensão do nome do arquivo."""
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return None

    def get_latest_download(self, pattern):
        """
        Retorna o arquivo mais recente que corresponde ao padrão.
        
        Args:
            pattern: Padrão glob (ex: 'cardapio_blumenau_*.png')
        
        Returns:
            str|None: Caminho do arquivo mais recente ou None
        """
        import glob
        search_pattern = os.path.join(self.get_downloads_dir(), pattern)
        files = glob.glob(search_pattern)
        if files:
            return max(files)  # Ordenação lexicográfica funciona com timestamp YYYYMMDD_HHMMSS
        return None

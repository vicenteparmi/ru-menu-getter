require 'firebase'
require 'open-uri'
require 'nokogiri'
require 'date'
require 'net/http'
require 'openssl'

# Dry run mode check
DRY_RUN = false
DEBUG_PRINT = false

# Configuration
firebase = nil
unless DRY_RUN
  BASE_URL = ENV['BASE_URL']
  FIREBASE_KEY = ENV['FIREBASE_KEY']
  if BASE_URL.nil? || FIREBASE_KEY.nil?
    puts "AVISO: Credenciais do Firebase ausentes. Executando sem envio."
  else
    begin
      puts "Tentando conectar ao Firebase com URL: #{BASE_URL[0..5]}..."
      firebase = Firebase::Client.new(BASE_URL, FIREBASE_KEY)
      test_resp = firebase.get('test')
      puts "Conexão com Firebase estabelecida com sucesso: #{test_resp.success?}"
    rescue => e
      puts "ERRO ao configurar Firebase: #{e.message}"
    end
  end
end

UF_REG_URL = "https://www.ufrgs.br/prae/cardapio-ru/"

MONTH_MAP = {
  'janeiro' => 1, 'fevereiro' => 2, 'março' => 3, 'abril' => 4,
  'maio' => 5, 'junho' => 6, 'julho' => 7, 'agosto' => 8,
  'setembro' => 9, 'outubro' => 10, 'novembro' => 11, 'dezembro' => 12
}

WEEKDAY_NAME_PT = {
  0 => 'Domingo', 1 => 'Segunda-Feira', 2 => 'Terça-Feira',
  3 => 'Quarta-Feira', 4 => 'Quinta-Feira', 5 => 'Sexta-Feira', 6 => 'Sábado'
}

# Maps the start of a column header to Ruby's wday value
HEADER_TO_WDAY = {
  'SEGUNDA' => 1, 'TERCA' => 2, 'TERÇA' => 2, 'QUARTA' => 3,
  'QUINTA' => 4, 'SEXTA' => 5, 'SABADO' => 6, 'SÁBADO' => 6, 'DOMINGO' => 0
}

def fetch_with_retry(url, max_retries = 5, timeout = 45)
  retries = 0
  begin
    uri = URI(url)
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')
    http.open_timeout = timeout
    http.read_timeout = timeout
    http.verify_mode = OpenSSL::SSL::VERIFY_NONE if http.use_ssl?
    request = Net::HTTP::Get.new(uri)
    request['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    request['Accept'] = 'text/html,application/xhtml+xml,application/xml'
    request['Accept-Language'] = 'pt-BR,pt;q=0.9'
    response = http.request(request)
    return response.body if response.is_a?(Net::HTTPSuccess)
    raise "HTTP #{response.code}"
  rescue => e
    retries += 1
    if retries < max_retries
      puts "Tentativa #{retries}/#{max_retries} falhou: #{e.message}. Aguardando #{2**retries}s..."
      sleep(2**retries)
      retry
    end
    raise e
  end
end

def clean_text(text)
  text.to_s.strip.gsub(/\s+/, ' ')
end

# Parses "Almoço 23 a 27 de março" → { meal_index:, initial_date:, days_count: }
def extract_date_range(title)
  title_clean = clean_text(title)
  current_year = Date.today.year

  meal_index = if title_clean.downcase.include?('jantar')
                 2
               elsif title_clean.downcase.include?('café') || title_clean.downcase.include?('lanche')
                 0
               else
                 1 # almoço
               end

  if m = title_clean.match(/(\d{1,2})\s+a\s+(\d{1,2})\s+de\s+([[:alpha:]]+)/i)
    month = MONTH_MAP[m[3].downcase]
    return nil unless month
    initial = Date.new(current_year, month, m[1].to_i)
    final   = Date.new(current_year, month, m[2].to_i)
    {
      meal_index:   meal_index,
      initial_date: initial.strftime('%Y-%m-%d'),
      days_count:   (final - initial).to_i
    }
  else
    nil
  end
end

def header_to_wday(header_text)
  normalized = header_text.upcase.strip
  HEADER_TO_WDAY.find { |k, _| normalized.start_with?(k) }&.last
end

def scrape_menu(ru_key, toggles, city, firebase)
  puts "Scraping #{city} -> #{ru_key}"

  toggles.each do |toggle|
    # CSS class changed from .elementor-toggle-title to .elementor-tab-title
    title = clean_text(toggle.at_css('.elementor-tab-title')&.text)
    next if title.nil? || title.empty?

    puts "- Toggle: #{title}"

    info = extract_date_range(title)
    unless info
      puts "  AVISO: não foi possível extrair datas de '#{title}'"
      next
    end

    dates = (0..info[:days_count]).map do |i|
      date = Date.parse(info[:initial_date]) + i
      [date.strftime('%Y-%m-%d'), date.wday]
    end

    table = toggle.at_css('.elementor-tab-content table')
    unless table
      puts "  Tabela não encontrada para '#{title}'"
      next
    end

    rows = table.css('tr')
    if rows.empty?
      puts "  Tabela vazia para '#{title}'"
      next
    end

    headers = rows.first.css('th, td').map { |td| clean_text(td.text) }
    puts "  Colunas: #{headers.join(' | ')}"

    # Map column index → date info using weekday header matching
    col_map = {}
    headers.each_with_index do |h, col_i|
      wday = header_to_wday(h)
      next unless wday
      date_entry = dates.find { |_, w| w == wday }
      col_map[col_i] = date_entry[0] if date_entry
    end

    # Collect food items per column
    col_foods = Hash.new { |h, k| h[k] = [] }
    rows[1..].each do |row|
      row.css('td').each_with_index do |cell, col_i|
        text = clean_text(cell.text)
        col_foods[col_i] << text unless text.empty?
      end
    end

    col_map.each do |col_i, date_str|
      meal_content = if col_foods[col_i].empty? || col_foods[col_i].any? { |m| m.match?(/FECHADO|RECESSO/i) }
                      ["Sem refeições disponíveis"]
                    else
                      col_foods[col_i]
                    end

      weekday_num = Date.parse(date_str).wday
      weekday     = WEEKDAY_NAME_PT[weekday_num]

      if DEBUG_PRINT
        puts "\n#{'=' * 50}"
        puts "RU: #{ru_key.upcase} | Data: #{date_str} (#{weekday})"
        puts "Refeição: #{title}"
        puts '-' * 50
        meal_content.each { |item| puts "- #{item}" }
        puts '=' * 50
      end

      next if DRY_RUN || firebase.nil?

      path = "archive/menus/#{city}/rus/#{ru_key}/menus/#{date_str}"
      begin
        # Fetch existing data to preserve other meal slots
        existing = firebase.get(path).body || {}
        menus_array = Array.new(3) { ["Sem refeições disponíveis"] }
        if existing["menu"].is_a?(Array)
          (0..2).each do |i|
            next if i == info[:meal_index]
            menus_array[i] = existing["menu"][i] if existing["menu"][i] && !existing["menu"][i].empty?
          end
        end
        menus_array[info[:meal_index]] = meal_content

        payload = { menu: menus_array, weekday: weekday, timestamp: Time.now.to_i }
        resp = firebase.update(path, payload)
        if resp.success?
          puts "  ✅ Firebase: #{path}"
        else
          puts "  ❌ Firebase falhou (#{resp.code}): #{path}"
        end
      rescue => e
        puts "  ❌ ERRO Firebase: #{e.message}"
      end
    end
  end
end

# Main execution
begin
  puts 'Iniciando UFRGS menu scraper...'
  puts 'MODO DRY-RUN ativado' if DRY_RUN

  html = fetch_with_retry(UF_REG_URL)
  doc  = Nokogiri::HTML(html)

  # Find sections identified by the elementor image-box title containing "RU\d+"
  sections = doc.css('section.elementor-section').select do |sec|
    sec.at_css('.elementor-image-box-title')&.text =~ /RU\d+/i
  end

  if sections.empty?
    puts "ERRO: Nenhuma seção de RU encontrada."
    puts "Seções elementor encontradas: #{doc.css('section.elementor-section').size}"
    exit 1
  end

  puts "Encontradas #{sections.size} seções de RU."

  restaurants = sections.map do |sec|
    title = clean_text(sec.at_css('.elementor-image-box-title')&.text)
    num   = title[/RU(\d+)/i, 1]
    { key: format('ru%02d', num.to_i), toggles: sec.css('.elementor-toggle-item') }
  end.uniq { |r| r[:key] }  # deduplicate desktop/mobile Elementor duplicates

  restaurants.each do |ru|
    puts "\n--- #{ru[:key]} (#{ru[:toggles].size} toggles) ---"
    scrape_menu(ru[:key], ru[:toggles], 'poa', firebase)
    sleep 1
  end

  puts "\nScraper UFRGS concluído!"
rescue => e
  puts "Fatal: #{e.message}"
  puts e.backtrace.first(10).join("\n")
  exit 1
end

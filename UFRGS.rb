require 'firebase'
require 'open-uri'
require 'nokogiri'
require 'date'
require 'net/http'
require 'openssl'

# Dry run mode check
DRY_RUN = false
# Debug print mode - exibe sempre os dados no terminal
DEBUG_PRINT = false

# Configuration
firebase = nil
unless DRY_RUN
  BASE_URL = ENV['BASE_URL']
  FIREBASE_KEY = ENV['FIREBASE_KEY']
  if BASE_URL.nil? || FIREBASE_KEY.nil?
    puts "AVISO: Credenciais do Firebase ausentes. Executando em modo dry-run."
    #DRY_RUN = true
  else
    begin
      puts "Tentando conectar ao Firebase com URL: #{BASE_URL[0..5]}..."
      firebase = Firebase::Client.new(BASE_URL, FIREBASE_KEY)
      # Testar conexão com o Firebase
      test_resp = firebase.get('test')
      puts "Conexão com Firebase estabelecida com sucesso: #{test_resp.success?}"
    rescue => e
      puts "ERRO ao configurar Firebase: #{e.message}"
      DRY_RUN = true
    end
  end
end

# Data structure for RUs
data = {
  "poa" => {
    "rus" => {
      "ru01" => {},
      "ru02" => {},
      "ru03" => {},
      "ru04" => {},
      "ru05" => {},
      "ru06" => {},
    },
  },
}

UF_REG_URL = "https://www.ufrgs.br/prae/cardapio-ru/"

# Fetch with retry and SSL handling
def fetch_with_retry(url, max_retries=3, timeout=30)
  retries = 0
  begin
    uri = URI(url)
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')
    http.open_timeout = timeout
    http.read_timeout = timeout
    if http.use_ssl?
      # Usar VERIFY_NONE em ambientes CI/CD como GitHub Actions
      puts "Detectado ambiente CI/CD, usando SSL VERIFY_NONE"
      http.verify_mode = OpenSSL::SSL::VERIFY_NONE
    end

    request = Net::HTTP::Get.new(uri)
    request['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    response = http.request(request)
    return response.body if response.is_a?(Net::HTTPSuccess)
    raise "HTTP #{response.code}"
  rescue Net::OpenTimeout, Net::ReadTimeout, OpenSSL::SSL::SSLError => e
    puts "Erro de SSL/timeout (tentativa #{retries+1}/#{max_retries}): #{e.message}"
    retries += 1
    if retries < max_retries
      sleep 2**retries
      retry
    else
      puts "Tentando método alternativo com open-uri após falha SSL..."
      return fetch_with_open_uri(url)
    end
  rescue StandardError => e
    puts "Erro padrão (tentativa #{retries+1}/#{max_retries}): #{e.message}"
    retries += 1
    if retries < max_retries
      sleep 2**retries
      retry
    else
      raise e
    end
  end
end

# Fallback using open-uri
def fetch_with_open_uri(url, max_retries=3)
  retries = 0
  begin
    puts "Tentando acessar #{url} com open-uri (tentativa #{retries+1}/#{max_retries})"
    options = {
      'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      read_timeout: 60,
      ssl_verify_mode: OpenSSL::SSL::VERIFY_NONE
    }
    
    # Adiciona outros cabeçalhos para simular melhor um navegador real
    options['Accept'] = 'text/html,application/xhtml+xml,application/xml'
    options['Accept-Language'] = 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    
    result = URI.open(url, options).read
    puts "Conexão bem-sucedida com open-uri (#{result.bytesize} bytes)"
    return result
  rescue StandardError => e
    puts "Erro com open-uri: #{e.class} - #{e.message}"
    retries += 1
    if retries < max_retries
      sleep_time = 2**retries
      puts "Aguardando #{sleep_time}s antes de tentar novamente..."
      sleep sleep_time
      retry
    end
    raise e
  end
end

# Extract date range from title string
def extract_date_range(string)
  meal_type = string.split.first
  current_year = Date.today.year

  if m = string.match(/(\d{1,2})\s*a\s*(\d{1,2})\s*de\s*(\w+)/i)
    start_day, end_day, month_name = m[1], m[2], m[3].downcase
    month = {
      'janeiro'=>'01','fevereiro'=>'02','março'=>'03','abril'=>'04','maio'=>'05','junho'=>'06',
      'julho'=>'07','agosto'=>'08','setembro'=>'09','outubro'=>'10','novembro'=>'11','dezembro'=>'12'
    }[month_name]
    initial = Date.strptime("#{start_day}/#{month}/#{current_year}", '%d/%m/%Y')
    final   = Date.strptime("#{end_day}/#{month}/#{current_year}", '%d/%m/%Y')
  elsif m = string.match(/(\d{1,2}\/\d{1,2})(?:\/\d{2,4})?\s*a\s*(\d{1,2}\/\d{1,2})(?:\/\d{2,4})?/i)
    initial = Date.parse(m[1])
    final   = Date.parse(m[2])
  else
    initial = final = Date.today
  end

  {
    meal_type:   meal_type,
    initial_date: initial.strftime('%Y-%m-%d'),
    final_date:   final.strftime('%Y-%m-%d'),
    days_count:   (final - initial).to_i
  }
end

# Clean text content
def clean_text(text)
  text.to_s.strip.gsub(/\s+/, ' ')
end

# Helper method to print menu data in terminal
def print_menu_data(ru_key, date_str, weekday, meal_type, menu)
  puts "\n" + "=" * 50
  puts "RU: #{ru_key.upcase} | Data: #{date_str} (#{weekday})"
  puts "Refeição: #{meal_type}"
  puts "-" * 50
  menu.each do |item|
    puts "- #{item}"
  end
  puts "=" * 50 + "\n"
end

# Scrape menu for a single RU
def scrape_menu(ru_key, toggles, city, firebase=nil)
  puts "Scraping #{city} -> #{ru_key}"
  
  # Debug do estado do Firebase
  puts "Estado do Firebase: #{DRY_RUN ? 'DRY_RUN ativado' : 'Firebase ' + (firebase.nil? ? 'não inicializado' : 'inicializado')}"
  
  toggles.each do |toggle|
    title = clean_text(toggle.at_css('.elementor-toggle-title')&.text)
    next if title.nil? || title.empty?
    
    # Remover verificação de FECHADO para exibir todos os menus
    is_closed = toggle.text.include?('FECHADO')
    puts "- Toggle: #{title} #{'(FECHADO)' if is_closed}"

    info = extract_date_range(title)
    dates = (0..info[:days_count]).map do |i|
      date = Date.parse(info[:initial_date]) + i
      [date.strftime('%Y-%m-%d'), date.strftime('%A')]
    end

    table = toggle.at_css('.elementor-tab-content table')
    if !table
      puts "  Tabela não encontrada para #{title}"
      next
    end

    headers = table.css('tr').first.css('td').map { |td| clean_text(td.text) }
    puts "  Colunas encontradas: #{headers.join(' | ')}"
    
    meals = Array.new(headers.size) { [] }
    table.css('tr:not(:first-child)').each do |row|
      row.css('td').each_with_index do |cell, idx|
        text = clean_text(cell.text)
        meals[idx] << text unless text.empty?
      end
    end

    meal_id = if info[:meal_type].downcase.include?('jantar')
                2
              elsif info[:meal_type].downcase.include?('almoço')
                1
              else
                0
              end

    dates.each_with_index do |(date_str, weekday), idx|
      # Sempre imprimir o menu independentemente de estar vazio ou fechado
      if idx < meals.size
        if meals[idx].empty? || meals[idx].any? { |m| m.match(/FECHADO|RECESSO/) }
          puts "\n" + "=" * 50
          puts "RU: #{ru_key.upcase} | Data: #{date_str} (#{weekday})"
          puts "Refeição: #{info[:meal_type]}"
          puts "-" * 50
          puts "AVISO: Menu vazio ou fechado."
          puts "=" * 50 + "\n"
        else
          print_menu_data(ru_key, date_str, weekday, info[:meal_type], meals[idx])
        end
      else
        puts "\n" + "=" * 50
        puts "RU: #{ru_key.upcase} | Data: #{date_str} (#{weekday})"
        puts "AVISO: Dados indisponíveis para esta data."
        puts "=" * 50 + "\n"
      end
      
      # Enviar para o Firebase se não estiver em modo DRY_RUN e tiver dados
      if !DRY_RUN && !firebase.nil? && idx < meals.size
        begin
          path = "archive/menus/#{city}/rus/#{ru_key}/menus/#{date_str}"
          
          # Primeiro, buscar dados existentes
          existing_data = firebase.get(path).body || {}
          
          # Garantir que o array de menus sempre tenha 3 posições (café, almoço, jantar)
          menus_array = Array.new(3) { ["Sem refeições disponíveis"] }
          
          # Preservar dados existentes de outras refeições se houver
          if existing_data["menu"] && existing_data["menu"].is_a?(Array)
            # Só copiar dados existentes que não são a refeição atual
            (0..2).each do |i|
              if i != meal_id && existing_data["menu"][i] && !existing_data["menu"][i].empty?
                menus_array[i] = existing_data["menu"][i]
              end
            end
          end
          
          # Atualizar apenas a refeição específica
          # Se meals[idx] estiver vazio ou contiver indicação de fechado, usar "Sem refeições disponíveis"
          meal_content = if meals[idx].empty? || meals[idx].any? { |m| m.match(/FECHADO|RECESSO/) }
                          ["Sem refeições disponíveis"]
                        else
                          meals[idx]
                        end
          
          menus_array[meal_id] = meal_content
          
          payload = {
            menu: menus_array,
            weekday: weekday,
            timestamp: Time.now.to_i
          }
          
          puts "Tentando enviar dados para Firebase: #{path}"
          resp = firebase.update(path, payload)
          
          if resp.success?
            puts "✅ Firebase atualizado com sucesso: #{path} (#{resp.code})"
          else
            puts "❌ Falha ao atualizar Firebase: #{path} - Código: #{resp.code}, Resposta: #{resp.body}"
          end
        rescue => e
          puts "❌ ERRO durante atualização do Firebase: #{e.message}"
        end
      elsif DRY_RUN
        puts "⚠️ Modo DRY_RUN ativado - Dados não enviados para Firebase"
      elsif firebase.nil?
        puts "⚠️ Cliente Firebase não inicializado - Dados não enviados"
      elsif idx >= meals.size || meals[idx].empty?
        puts "⚠️ Sem dados para enviar ao Firebase"
      end
    end
  end
end

# Main execution
begin
  puts 'Starting UFRGS menu scraper'
  puts 'MODO DRY-RUN: Os dados serão exibidos no terminal, sem envio para o Firebase' if DRY_RUN
  puts 'MODO DEBUG-PRINT: Os cardápios serão exibidos no terminal independente do modo' if DEBUG_PRINT
  
  html = fetch_with_retry(UF_REG_URL, 5, 45)
  doc  = Nokogiri::HTML(html)

  # Mostra o conteúdo HTML obtido se DEBUG_PRINT estiver ativado
  if DEBUG_PRINT
    puts "HTML obtido: #{html[0..1000]}..." # Exibe uma amostra do HTML obtido
  end

  # Verifica se o HTML contém a seção esperada
  unless doc.at_css('section.elementor-section')
    puts "AVISO: Estrutura HTML inesperada. Verifique o site."
    exit
  end

  # Verificar se conseguiu extrair alguma informação
  if doc.nil? || doc.css('section.elementor-section').empty?
    puts "AVISO: Não foi possível extrair conteúdo do site. HTML obtido:"
    puts html[0..1000] + "..." # Exibe uma amostra do HTML obtido
  end

  sections = doc.css('section.elementor-section').select do |sec|
    sec.at_css('.elementor-image-box-title')&.text =~ /^RU\d+/i
  end

  restaurants = sections.map do |sec|
    title = clean_text(sec.at_css('.elementor-image-box-title')&.text)
    num   = title[/RU(\d+)/i,1]
    { key: format('ru%02d', num.to_i), toggles: sec.css('.elementor-toggle-item') }
  end

  restaurants.each do |ru|
    scrape_menu(ru[:key], ru[:toggles], 'poa', firebase)
    sleep 2
  end
rescue => e
  puts "Fatal: #{e.message}"; puts e.backtrace
end

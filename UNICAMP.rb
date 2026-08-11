#!/usr/bin/env ruby
# frozen_string_literal: true

require 'cgi'
require 'date'
require 'json'
require 'net/http'
require 'openssl'
require 'optparse'
require 'time'
require 'timeout'
require 'uri'
require 'nokogiri'

module UnicampMenus
  NO_MEALS = 'Sem refeições disponíveis'
  WEEKDAYS = %w[Domingo Segunda-Feira Terça-Feira Quarta-Feira Quinta-Feira Sexta-Feira Sábado].freeze

  CAMPINAS_CARDAPIO_URL = 'https://www.prefeitura.unicamp.br/cardapio/'
  CAMPINAS_MENU_URL = 'https://sistemas.prefeitura.unicamp.br/apps/cardapio/index.php'
  REGIONAL_PAGE_URL = 'https://prefeituralimeira.unicamp.br/restaurantes-universitarios/'
  REGIONAL_MENU_URL = 'https://sistemas.prefeituralimeira.unicamp.br/RU/view/site/cardapio.php'

  RESTAURANTS = {
    'cam' => {
      'name' => 'Campinas, São Paulo',
      'university' => 'UNICAMP',
      'rus' => {
        'ru' => ['Restaurante Universitário (RU)', 'Av. Érico Veríssimo, 50 - Cidade Universitária, Campinas - SP'],
        'ra' => ['Refeitório da Administração (RA)', 'Rua Bernardo Sayão, 198 - Cidade Universitária, Campinas - SP'],
        'rs' => ['Restaurante da Saturnino (RS)', 'Rua Saturnino de Brito, 314 - Cidade Universitária, Campinas - SP']
      }
    },
    'lim' => {
      'name' => 'Limeira, São Paulo',
      'university' => 'UNICAMP',
      'rus' => {
        'rli' => ['Restaurante Campus I (RLI)', 'Rua Paschoal Marmo, 1888 - Jardim Nova Itália, Limeira - SP, 13484-332'],
        'rlii' => ['Restaurante Campus II (RLII)', 'Rua Pedro Zaccaria, 1300 - Jardim São Paulo, Limeira - SP, 13484-350']
      }
    },
    'pir' => {
      'name' => 'Piracicaba, São Paulo',
      'university' => 'UNICAMP',
      'rus' => {
        'rfop' => ['Restaurante FOP (RFOP)', 'Av. Limeira, 901 - Areião, Piracicaba - SP, 13414-903']
      }
    }
  }.freeze

  class Error < StandardError; end

  TRANSIENT_NETWORK_ERRORS = [IOError, SystemCallError, Timeout::Error, OpenSSL::SSL::SSLError, EOFError].freeze

  class HttpClient
    USER_AGENT = 'CampusDine menu scraper/1.0 (+https://vicx.dev.br/campusdine/)'

    def get(url, params: {}, encoding: nil)
      uri = URI(url)
      uri.query = URI.encode_www_form(params) unless params.empty?
      request(uri, Net::HTTP::Get.new(uri), encoding: encoding)
    end

    def post(url, form:, encoding: nil)
      uri = URI(url)
      req = Net::HTTP::Post.new(uri)
      req.set_form_data(form)
      request(uri, req, encoding: encoding)
    end

    private

    def request(uri, req, encoding:)
      req['User-Agent'] = USER_AGENT
      req['Accept'] = 'text/html,application/json'
      response = with_retries do
        Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == 'https',
                       open_timeout: 15, read_timeout: 30) { |http| http.request(req) }
      end
      raise Error, "HTTP #{response.code} em #{uri}" unless response.is_a?(Net::HTTPSuccess)

      body = response.body
      return body unless encoding

      body.force_encoding(encoding).encode('UTF-8', invalid: :replace, undef: :replace)
    end

    def with_retries
      attempts = 0
      begin
        attempts += 1
        yield
      rescue *TRANSIENT_NETWORK_ERRORS => e
        raise if attempts >= 3

        warn "[HTTP] Falha transitória (#{e.class}); tentativa #{attempts + 1}/3"
        sleep(attempts)
        retry
      end
    end
  end

  module TextHelpers
    module_function

    def clean(value)
      CGI.unescapeHTML(value.to_s).gsub(/\u00a0/, ' ').gsub(/\s+/, ' ').strip
    end

    def lines(node)
      copy = node.dup
      copy.css('br').each { |br| br.replace("\n") }
      CGI.unescapeHTML(copy.text).split(/\r?\n/).map { |line| clean(line) }.reject(&:empty?)
    end

    def normalized(value)
      clean(value).downcase.unicode_normalize(:nfd).gsub(/\p{Mn}/, '').gsub(/[^a-z0-9]+/, ' ').strip
    end

    def weekday(date)
      WEEKDAYS[date.wday]
    end
  end

  class MealBuilder
    class << self
      def combine(standard, vegan)
        raise Error, 'Cardápio padrão ausente' if standard.nil? || standard.empty?
        raise Error, 'Cardápio vegano ausente' if vegan.nil? || vegan.empty?

        standard_norms = standard.map { |item| TextHelpers.normalized(strip_label(item)) }
        result = standard.dup
        vegan.each_with_index do |item, index|
          value = strip_label(item)
          next if index.positive? && standard_norms.include?(TextHelpers.normalized(value))

          result << "Opção vegana: #{value}"
        end
        result.uniq
      end

      private

      def strip_label(item)
        item.sub(/\A(?:Prato principal|Acompanhamentos?|Guarnição|Salada|Sobremesa|Refresco):\s*/i, '')
      end
    end
  end

  class CampinasParser
    RESTAURANT_CODES = %w[RU RA RS].freeze

    def parse_breakfast(html)
      doc = Nokogiri::HTML(html)
      text = doc.xpath('//li').map { |node| TextHelpers.clean(node.text) }
                .find { |line| line.match?(/Cardápio café da manhã:/i) }
      raise Error, 'Café da manhã de Campinas não encontrado' unless text

      value = text.sub(/.*Cardápio café da manhã:\s*/i, '').sub(/[.]\z/, '')
      items = value.split(/,|\s+e\s+/i).map { |item| TextHelpers.clean(item).capitalize }.reject(&:empty?)
      raise Error, 'Café da manhã de Campinas vazio' if items.empty?

      items
    end

    def discover_dates(html)
      doc = Nokogiri::HTML(html)
      dates = doc.css('a[href*="?d="]').filter_map do |link|
        query = URI.decode_www_form(URI(link['href']).query.to_s).to_h
        Date.iso8601(query['d']) if query['d']
      rescue Date::Error, URI::InvalidURIError
        nil
      end.uniq.sort
      raise Error, 'Nenhuma data publicada para Campinas' if dates.empty?

      dates
    end

    def parse_day(html, expected_date:, breakfast:)
      raise Error, "Cardápio de Campinas ausente em #{expected_date}" if html.match?(/Não existe cardápio cadastrado/i)

      doc = Nokogiri::HTML(html)
      title = TextHelpers.clean(doc.at_css('.navbar-brand')&.text)
      raise Error, "Data de Campinas ausente em #{expected_date}" if title.empty?
      unless title.include?(expected_date.strftime('%d/%m'))
        raise Error, "Data inesperada em Campinas: #{title.inspect}, esperado #{expected_date.strftime('%d/%m')}"
      end

      cards = {}
      doc.css('.menu-section').each do |section|
        section_title = TextHelpers.clean(section.at_css('.menu-section-title')&.text)
        next unless section_title.match?(/\A(?:Almoço|Jantar)(?: Vegano)?\z/i)

        item_name = TextHelpers.clean(section.at_css('.menu-item-name')&.text)
        description = section.at_css('.menu-item-description')
        next if item_name.empty? && description.nil?

        cards[section_title.downcase] = parse_card(section)
      end

      meals = {
        lunch: build_meal(cards, 'almoço'),
        dinner: build_meal(cards, 'jantar')
      }
      raise Error, "Nenhuma refeição encontrada em Campinas para #{expected_date}" if meals.values.compact.empty?

      build_restaurant_days(expected_date, meals, breakfast)
    end

    private

    def parse_card(section)
      name = TextHelpers.clean(section.at_css('.menu-item-name')&.text)
      description = section.at_css('.menu-item-description')
      raise Error, 'Prato principal ou descrição ausente em Campinas' if name.empty? || description.nil?

      all_text = TextHelpers.clean(description.text)
      service_sentence = all_text[/As refeições serão servidas[^.]*\./i]
      raise Error, "Indicação de restaurantes ausente para #{name}" unless service_sentence

      restaurants = RESTAURANT_CODES.select { |code| service_sentence.match?(/\b#{code}\b/i) }
      raise Error, "Indicação de restaurantes ambígua: #{service_sentence}" if restaurants.empty?

      menu_lines = TextHelpers.lines(description).take_while { |line| !line.match?(/\AObservações?:/i) }
      { items: ["Prato principal: #{name}", *menu_lines], restaurants: restaurants.sort }
    end

    def build_meal(cards, name)
      standard = cards[name]
      vegan = cards["#{name} vegano"]
      return nil if standard.nil? && vegan.nil?
      raise Error, "Par padrão/vegano incompleto para #{name}" if standard.nil? || vegan.nil?
      unless standard[:restaurants] == vegan[:restaurants]
        raise Error, "Restaurantes divergentes entre os cardápios de #{name}"
      end

      { items: MealBuilder.combine(standard[:items], vegan[:items]), restaurants: standard[:restaurants] }
    end

    def build_restaurant_days(date, meals, breakfast)
      { 'ru' => 'RU', 'ra' => 'RA', 'rs' => 'RS' }.each_with_object({}) do |(key, code), result|
        lunch = meals[:lunch]&.dig(:restaurants)&.include?(code) ? meals[:lunch][:items] : [NO_MEALS]
        dinner = meals[:dinner]&.dig(:restaurants)&.include?(code) ? meals[:dinner][:items] : [NO_MEALS]
        active = lunch != [NO_MEALS] || dinner != [NO_MEALS]
        next unless active

        serves_breakfast = key == 'rs' || (key == 'ru' && (1..5).cover?(date.wday))
        result[key] = payload(date, [serves_breakfast ? breakfast : [NO_MEALS], lunch, dinner])
      end
    end

    def payload(date, menu)
      { 'weekday' => TextHelpers.weekday(date), 'menu' => menu, 'timestamp' => 0 }
    end
  end

  class RegionalParser
    def discover_dates(html)
      doc = Nokogiri::HTML(html)
      dates = doc.css('input[name="data"]').filter_map do |input|
        Date.iso8601(input['value'])
      rescue Date::Error
        nil
      end.uniq.sort
      raise Error, 'Nenhuma data publicada para Limeira/Piracicaba' if dates.empty?

      dates
    end

    def parse_day(html, expected_date:)
      doc = Nokogiri::HTML(html)
      heading = doc.css('div').find { |node| TextHelpers.clean(node.text).start_with?(expected_date.strftime('%d/%m/%Y')) }
      raise Error, "Data regional ausente ou inesperada em #{expected_date}" unless heading

      lunch = parse_meal(doc.at_css('#normal'), 'almoço')
      dinner = parse_meal(doc.at_css('#vegetariano'), 'jantar')
      breakfast = parse_breakfast(doc)
      raise Error, "Nenhuma refeição regional encontrada para #{expected_date}" if [breakfast, lunch, dinner].compact.empty?

      distribute(expected_date, breakfast, lunch, dinner)
    end

    private

    def parse_meal(container, name)
      return nil unless container

      tables = container.css('table')
      return nil if tables.empty?
      raise Error, "Quantidade inesperada de tabelas para #{name}: #{tables.length}" unless tables.length == 2

      standard = parse_table(tables[0])
      vegan = parse_table(tables[1])
      MealBuilder.combine(standard, vegan)
    end

    def parse_table(table)
      items = table.css('td').filter_map do |cell|
        lines = TextHelpers.lines(cell)
        next if lines.empty? || lines.first.match?(/\ANota Técnica:/i)

        label = TextHelpers.clean(cell.at_css('strong')&.text).sub(/:\z/, '')
        values = lines.reject { |line| TextHelpers.normalized(line) == TextHelpers.normalized(label) }
        values = values.take_while { |line| !line.match?(/\ANota Técnica:/i) }
        next if values.empty? && label.empty?

        if values.empty?
          TextHelpers.clean(label.split.map(&:capitalize).join(' '))
        elsif label.empty?
          values.join(' ')
        else
          "#{label.split.map(&:capitalize).join(' ')}: #{values.join(' ')}"
        end
      end
      raise Error, 'Tabela regional sem itens' if items.empty?

      items
    end

    def parse_breakfast(doc)
      heading = doc.xpath("//*[contains(translate(normalize-space(text()), 'abcdefghijklmnopqrstuvwxyzáãâàéêíóõôúç', 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÃÂÀÉÊÍÓÕÔÚÇ'), 'CAFÉ DA MANHÃ')]").last
      return nil unless heading

      table = heading.xpath('following::table[1]').first
      return nil unless table

      items = table.css('td').map { |cell| TextHelpers.clean(cell.text).sub(/[.]\z/, '') }.reject(&:empty?)
      items.reject { |item| item.match?(/sujeito a alterações/i) }
    end

    def distribute(date, breakfast, lunch, dinner)
      schedule = if (1..5).cover?(date.wday)
                   { 'rli' => [true, true, true], 'rlii' => [true, true, true], 'rfop' => [true, true, true] }
                 elsif date.saturday?
                   { 'rlii' => [true, true, true], 'rfop' => [false, true, true] }
                 else
                   { 'rlii' => [true, true, false], 'rfop' => [false, true, false] }
                 end

      schedule.each_with_object({}) do |(restaurant, slots), result|
        menu = [breakfast, lunch, dinner].each_with_index.map do |meal, index|
          slots[index] && meal && !meal.empty? ? meal : [NO_MEALS]
        end
        next if menu.all? { |meal| meal == [NO_MEALS] }

        result[restaurant] = { 'weekday' => TextHelpers.weekday(date), 'menu' => menu, 'timestamp' => 0 }
      end
    end
  end

  class FirebaseStore
    def initialize(base_url:, auth:, http: HttpClient.new)
      raise Error, 'BASE_URL não configurada' if base_url.to_s.empty?
      raise Error, 'FIREBASE_KEY não configurada' if auth.to_s.empty?

      @base_url = base_url.sub(%r{/+$}, '')
      @auth = auth
      @http = http
    end

    def setup_restaurants
      RESTAURANTS.each do |city_key, city|
        patch("menus/#{city_key}", { 'name' => city['name'], 'university' => city['university'] })
        city['rus'].each do |restaurant_key, (name, address)|
          patch("menus/#{city_key}/rus/#{restaurant_key}", {
                  'name' => name,
                  'address' => address,
                  'displayMessage' => false,
                  'isNew' => true,
                  'status' => 'beta',
                  'updateFrequency' => 'daily',
                  'updateModeIsAuto' => true
                })
        end
      end
    end

    def upload(all_menus)
      timestamp = Time.now.to_i
      all_menus.each do |city, restaurants|
        restaurants.each do |restaurant, dates|
          dates.each do |date, payload|
            data = payload.merge('timestamp' => timestamp)
            path = "archive/menus/#{city}/rus/#{restaurant}/menus/#{date}"
            put(path, data)
            stored = get(path)
            raise Error, "Falha ao verificar #{path}" unless stored == data

            puts "[FIREBASE] #{city}/#{restaurant}/#{date} gravado e verificado"
          end
        end
      end
    end

    private

    def firebase_uri(path)
      uri = URI("#{@base_url}/#{path}.json")
      uri.query = URI.encode_www_form(auth: @auth)
      uri
    end

    def request(path, klass, body: nil)
      uri = firebase_uri(path)
      req = klass.new(uri)
      req['Content-Type'] = 'application/json'
      req['User-Agent'] = HttpClient::USER_AGENT
      req.body = JSON.generate(body) if body
      attempts = 0
      begin
        attempts += 1
        response = Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == 'https',
                                   open_timeout: 15, read_timeout: 30) { |http| http.request(req) }
      rescue *TRANSIENT_NETWORK_ERRORS => e
        raise if attempts >= 3

        warn "[FIREBASE] Falha transitória em #{path} (#{e.class}); tentativa #{attempts + 1}/3"
        sleep(attempts)
        retry
      end
      raise Error, "Firebase HTTP #{response.code} em #{path}: #{response.body.to_s[0, 200]}" unless response.is_a?(Net::HTTPSuccess)

      JSON.parse(response.body)
    end

    def patch(path, body) = request(path, Net::HTTP::Patch, body: body)
    def put(path, body) = request(path, Net::HTTP::Put, body: body)
    def get(path) = request(path, Net::HTTP::Get)
  end

  class Runner
    def initialize(http: HttpClient.new)
      @http = http
    end

    def collect
      result = Hash.new { |cities, city| cities[city] = Hash.new { |restaurants, ru| restaurants[ru] = {} } }
      collect_campinas(result)
      collect_regional(result)
      result
    end

    private

    def collect_campinas(result)
      parser = CampinasParser.new
      breakfast = parser.parse_breakfast(@http.get(CAMPINAS_CARDAPIO_URL))
      index = @http.get(CAMPINAS_MENU_URL, encoding: 'ISO-8859-1')
      parser.discover_dates(index).each do |date|
        html = @http.get(CAMPINAS_MENU_URL, params: { d: date.iso8601 }, encoding: 'ISO-8859-1')
        parser.parse_day(html, expected_date: date, breakfast: breakfast).each do |restaurant, payload|
          result['cam'][restaurant][date.iso8601] = payload
        end
      end
    end

    def collect_regional(result)
      parser = RegionalParser.new
      index = @http.get(REGIONAL_MENU_URL)
      parser.discover_dates(index).each do |date|
        html = @http.post(REGIONAL_MENU_URL, form: { data: date.iso8601 })
        parser.parse_day(html, expected_date: date).each do |restaurant, payload|
          city = restaurant == 'rfop' ? 'pir' : 'lim'
          result[city][restaurant][date.iso8601] = payload
        end
      end
    end
  end

  module Env
    module_function

    def load(path = File.join(__dir__, '.env'))
      return unless File.file?(path)

      File.foreach(path) do |line|
        next if line.strip.empty? || line.lstrip.start_with?('#') || !line.include?('=')

        key, value = line.split('=', 2)
        value = value.strip.sub(/\A(["'])(.*)\1\z/, '\\2')
        ENV[key.strip] ||= value
      end
    end
  end

  module CLI
    module_function

    def run(argv)
      options = { dry_run: false, setup: false }
      OptionParser.new do |parser|
        parser.banner = 'Uso: ruby UNICAMP.rb [--dry-run] [--setup]'
        parser.on('--dry-run', 'Coleta e valida sem escrever no Firebase') { options[:dry_run] = true }
        parser.on('--setup', 'Cria/atualiza metadados-base antes do upload') { options[:setup] = true }
      end.parse!(argv)

      Env.load
      menus = Runner.new.collect
      summary = menus.transform_values do |restaurants|
        restaurants.transform_values { |dates| dates.keys.sort }
      end
      puts JSON.pretty_generate(summary)
      return 0 if options[:dry_run]

      store = FirebaseStore.new(base_url: ENV['BASE_URL'], auth: ENV['FIREBASE_KEY'])
      store.setup_restaurants if options[:setup]
      store.upload(menus)
      puts '[UNICAMP] Coleta, upload e verificação concluídos.'
      0
    rescue OptionParser::ParseError, Error, Date::Error, URI::InvalidURIError, JSON::ParserError,
           *TRANSIENT_NETWORK_ERRORS => e
      warn "[UNICAMP ERROR] #{e.class}: #{e.message}"
      1
    end
  end
end

exit UnicampMenus::CLI.run(ARGV) if $PROGRAM_NAME == __FILE__

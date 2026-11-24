# frozen_string_literal: true

require 'date'
require 'firebase'
require 'json'
require 'nokogiri'
require 'open-uri'

module UfrgsMenus
  SOURCE = 'https://www.ufrgs.br/prae/cardapio-restaurante-universitario/'
  UNITS = (1..6).map { |number| format('ru%02d', number) }.freeze
  WEEKDAYS = %w[Domingo Segunda-Feira Terça-Feira Quarta-Feira Quinta-Feira Sexta-Feira Sábado].freeze
  NO_MEAL = 'Sem refeições disponíveis'
  SLOTS = { 'almoço' => 1, 'janta' => 2, 'jantar' => 2, 'café' => 0 }.freeze

  def self.parse(html, today:)
    page = Nokogiri::HTML(html, nil, 'UTF-8')
    menus = {}
    page.css('h5').each do |heading|
      number = heading.text.strip[/\ARU(0[1-6])\s*[-–]/i, 1]
      next unless number

      unit = "ru#{number}"
      raise "Unidade duplicada: #{unit}" if menus.key?(unit)

      accordion = heading.ancestors.lazy.map { |node| node.at_css('.accordion') }.find(&:itself)
      next unless accordion

      days = {}
      accordion.css('.accordion-item').each do |section|
        period = section.at_css('.accordion-button')&.text.to_s.strip.downcase.split.first
        slot = SLOTS[period]
        next unless slot

        section.css('table').each do |table|
          headers = table.css('thead th')
          next if headers.empty?

          body = table.css('tbody tr').map { |row| row.css('td') }
          if body.any? { |row| row.size != headers.size || row.any? { |cell| cell['colspan'].to_i > 1 } }
            raise "Colunas inesperadas em #{unit}"
          end
          headers.each_with_index do |header, column|
            short_date = header.at_css('small')&.text.to_s.strip
            date = (today - 6..today + 7).find { |day| day.strftime('%d/%m') == short_date }
            next unless date

            weekday = header.children.select(&:text?).map(&:text).join.strip
            unless weekday&.downcase == WEEKDAYS[date.wday].split('-').first.downcase
              raise "Dia da semana divergente em #{unit}: #{short_date}"
            end
            meals = days[date.iso8601] ||= { weekday: WEEKDAYS[date.wday], menu: Array.new(3) { [NO_MEAL] } }
            foods = body.map { |row| row[column].text.split.join(' ') }.reject { |item| item.empty? || item == '-' }
            next if foods.empty? || foods.any? { |item| item.match?(/\A(?:FECHADO|RECESSO|SEM ATENDIMENTO)\b/i) }
            raise "Refeição duplicada em #{unit}/#{date}" unless meals[:menu][slot] == [NO_MEAL]

            meals[:menu][slot] = foods
          end
        end
      end
      menus[unit] = days.reject { |_, day| day[:menu].all? { |meal| meal == [NO_MEAL] } }
    end
    missing = UNITS.reject { |unit| menus[unit] && !menus[unit].empty? }
    raise "Cardápio recente ausente: #{missing.join(', ')}" unless missing.empty?

    menus
  end

  def self.run
    ENV['TZ'] = 'America/Sao_Paulo'
    html = URI(SOURCE).open(open_timeout: 15, read_timeout: 25, &:read)
    menus = parse(html, today: Date.today)
    if ARGV.include?('--dry-run') || ENV.values_at('BASE_URL', 'FIREBASE_KEY').any? { |value| value.to_s.empty? }
      puts JSON.pretty_generate(menus)
      return
    end

    firebase = Firebase::Client.new(ENV.fetch('BASE_URL'), ENV.fetch('FIREBASE_KEY'))
    timestamp = Time.now.to_i
    expected = menus.each_with_object({}) do |(unit, days), records|
      days.each do |date, day|
        records["poa/rus/#{unit}/menus/#{date}"] = day.merge(timestamp: timestamp).transform_keys(&:to_s)
      end
    end
    changes = expected.each_with_object({}) do |(path, day), fields|
      day.each { |key, value| fields["#{path}/#{key}"] = value }
    end
    response = firebase.update('archive/menus', changes)
    raise "Falha ao gravar UFRGS: HTTP #{response.code}" unless response.success?

    expected.each do |path, day|
      stored = firebase.get("archive/menus/#{path}")
      unless stored.success? && stored.body.is_a?(Hash) && stored.body.slice(*day.keys) == day
        raise "Divergência ao reler #{path}"
      end

      puts "#{path}: gravado e verificado"
    end
  end
end

UfrgsMenus.run if $PROGRAM_NAME == __FILE__

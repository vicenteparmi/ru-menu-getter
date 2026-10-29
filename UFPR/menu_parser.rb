# frozen_string_literal: true
require 'nokogiri'
require 'date'
require 'cgi'

module UfprMenuParser
  class Error < StandardError; end
  NO_MEALS = 'Sem refeições disponíveis'
  WEEKDAYS = %w[Domingo Segunda-Feira Terça-Feira Quarta-Feira Quinta-Feira Sexta-Feira Sábado].freeze
  MEALS = { 'café da manhã' => 0, 'almoço' => 1, 'jantar' => 2 }.freeze

  def self.clean(text)
    CGI.unescapeHTML(text.to_s).gsub(/\u00a0/, ' ').gsub(/\s+/, ' ').strip
  end

  def self.parse(html, today: Date.today)
    doc = Nokogiri::HTML(html)
    result = {}
    pending = nil
    closed = false
    doc.css('p, figure.wp-block-table').each do |node|
      if node.name == 'p'
        heading = clean(node.css('strong').map(&:text).join(' '))
        match = heading.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4}|\d{2})\b/)
        next unless match && heading.match?(/Segunda|Terça|Terca|Quarta|Quinta|Sexta|Sábado|Sabado|Domingo|FERIADO|RECESSO/i)
        raise Error, "Tabela ausente para #{pending}" if pending && !closed && pending <= today
        year = match[3].length == 2 ? 2000 + match[3].to_i : match[3].to_i
        pending = Date.new(year, match[2].to_i, match[1].to_i)
        closed = heading.match?(/FERIADO|RECESSO|FECHADO/i)
        result[pending.iso8601] = payload(pending, [[], [], []]) if closed
      else
        next unless pending
        raise Error, "Data duplicada: #{pending}" if result.key?(pending.iso8601) && !closed
        meals = closed ? [[], [], []] : parse_table(node)
        result[pending.iso8601] = payload(pending, meals)
        pending = nil
        closed = false
      end
    end
    raise Error, "Tabela ausente para #{pending}" if pending && !closed && pending <= today
    warn "[UFPR] #{pending}: cabeçalho futuro sem tabela; cardápio ainda não publicado" if pending && !closed && pending > today
    raise Error, 'Nenhum cardápio com data explícita encontrado' if result.empty?
    result
  rescue Date::Error => e
    raise Error, "Data inválida na fonte: #{e.message}"
  end

  def self.parse_table(table)
    meals = [[], [], []]
    current = nil
    table.css('tr').each do |row|
      cells = row.xpath('./th|./td')
      header = clean(cells.map(&:text).join(' ')).downcase
      if MEALS.key?(header)
        current = MEALS[header]
        next
      end
      cells.each do |cell|
        copy = cell.dup
        copy.css('br').each { |br| br.replace("\n") }
        copy.css('img').remove
        items = copy.text.split(/\r?\n/).map { |line| clean(line) }.reject(&:empty?)
        next if items.empty?
        raise Error, 'Itens sem cabeçalho de refeição' if current.nil?
        meals[current].concat(items)
      end
    end
    raise Error, 'Tabela sem refeições reconhecidas' if meals.all?(&:empty?)
    meals.map(&:uniq)
  end

  def self.payload(date, meals)
    { 'weekday' => WEEKDAYS[date.wday],
      'menu' => meals.map { |items| items.empty? ? [NO_MEALS] : items },
      'timestamp' => 0 }
  end
end

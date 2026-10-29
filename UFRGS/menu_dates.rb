# frozen_string_literal: true
require 'date'

module UfrgsMenuDates
  MONTHS = {
    'janeiro' => 1, 'fevereiro' => 2, 'março' => 3, 'abril' => 4,
    'maio' => 5, 'junho' => 6, 'julho' => 7, 'agosto' => 8,
    'setembro' => 9, 'outubro' => 10, 'novembro' => 11, 'dezembro' => 12
  }.freeze

  def self.extract(title, today: Date.today)
    text = title.to_s.strip.gsub(/\s+/, ' ').downcase
    match = text.match(/(\d{1,2})\s+a\s+(\d{1,2})\s+de\s+([[:alpha:]]+)(?:\s+(?:de\s+)?(\d{4}))?/)
    return nil unless match && MONTHS[match[3]]

    years = match[4] ? [match[4].to_i] : [today.year - 1, today.year, today.year + 1]
    ranges = years.filter_map do |year|
      first = Date.new(year, MONTHS[match[3]], match[1].to_i)
      last = Date.new(year, MONTHS[match[3]], match[2].to_i)
      [first, last] if (0..6).cover?((last - first).to_i)
    rescue Date::Error
      nil
    end
    range = ranges.min_by { |first, last| [(first - today).abs, (last - today).abs].min }
    return nil unless range
    first, last = range
    # Old archive accordions must never be relabelled with the current year.
    return nil if last < today - 7 || first > today + 14

    meal = if text.include?('jantar')
             2
           elsif text.include?('café') || text.include?('lanche')
             0
           else
             1
           end
    { meal_index: meal, initial_date: first.iso8601, days_count: (last - first).to_i }
  end
end

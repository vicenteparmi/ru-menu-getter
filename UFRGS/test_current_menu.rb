# frozen_string_literal: true

require 'minitest/autorun'
require_relative 'UFRGS'

class CurrentUfrgsMenuTest < Minitest::Test
  def source(weekday: 'Terça', date: '24/11')
    sections = UfrgsMenus::UNITS.map do |unit|
      <<~HTML
        <article>
          <div><h5>#{unit.upcase} - Campus</h5></div>
          <div class="accordion">
            <div class="accordion-item">
              <button class="accordion-button">Almoço das 11:00 às 14:00</button>
              <table><thead><tr><th>#{weekday}<br><small>#{date}</small></th></tr></thead>
              <tbody><tr><td>Almoço de #{unit}</td></tr></tbody></table>
            </div>
          </div>
        </article>
      HTML
    end
    '<article><h5>RU01 Anexo - Restaurante separado</h5></article>' + sections.join
  end

  def test_read_each_unit_and_keep_meal_slots
    result = UfrgsMenus.parse(source, today: Date.new(2026, 11, 24))
    assert_equal UfrgsMenus::UNITS, result.keys
    result.each do |unit, days|
      assert_equal [[UfrgsMenus::NO_MEAL], ["Almoço de #{unit}"], [UfrgsMenus::NO_MEAL]],
                   days.fetch('2026-11-24').fetch(:menu)
    end
  end

  def test_rejects_stale_dates_and_wrong_weekdays
    today = Date.new(2026, 11, 24)
    assert_raises(RuntimeError) { UfrgsMenus.parse(source(date: '10/11'), today: today) }
    assert_raises(RuntimeError) { UfrgsMenus.parse(source(weekday: 'Segunda'), today: today) }
  end
end

require 'minitest/autorun'
require_relative 'menu_dates'

class UfrgsMenuDatesTest < Minitest::Test
  def test_current_week
    result = UfrgsMenuDates.extract('Almoço 26 a 30 de outubro', today: Date.new(2026, 10, 29))
    assert_equal '2026-10-26', result[:initial_date]
    assert_equal 4, result[:days_count]
    assert_equal 1, result[:meal_index]
  end

  def test_old_december_title_does_not_become_future_menu
    assert_nil UfrgsMenuDates.extract('Almoço 29 a 30 de dezembro', today: Date.new(2026, 8, 17))
  end

  def test_previous_december_near_new_year
    result = UfrgsMenuDates.extract('Jantar 29 a 31 de dezembro', today: Date.new(2027, 1, 1))
    assert_equal '2026-12-29', result[:initial_date]
    assert_equal 2, result[:meal_index]
  end

  def test_explicit_year_is_respected
    assert_nil UfrgsMenuDates.extract('Almoço 26 a 30 de outubro de 2025', today: Date.new(2026, 10, 29))
  end

  def test_invalid_or_unreasonable_ranges
    ['Almoço 30 a 26 de outubro', 'Almoço 01 a 30 de outubro', 'Almoço 29 a 31 de fevereiro', 'Sem datas'].each do |title|
      assert_nil UfrgsMenuDates.extract(title, today: Date.new(2026, 10, 29))
    end
  end
end

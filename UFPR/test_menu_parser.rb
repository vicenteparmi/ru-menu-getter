require 'minitest/autorun'
require_relative 'menu_parser'

class UfprMenuParserTest < Minitest::Test
  def day(date, main)
    <<~HTML
      <p><strong>Quinta-Feira #{date}</strong></p>
      <figure class="wp-block-table"><table>
        <tr><td><strong>Almoço</strong></td></tr>
        <tr><td>#{main}<br>Opção vegana: Feijão<br>Salada</td></tr>
      </table></figure>
    HTML
  end

  def test_real_central_menu_preserves_meals_vegan_and_allergens
    result = UfprMenuParser.parse(File.read(File.join(__dir__, 'fixtures/central-2026-10-29.html')))
    assert_equal ['2026-10-29'], result.keys
    value = result['2026-10-29']
    assert_equal 'Quinta-Feira', value['weekday']
    assert_equal 3, value['menu'].size
    assert value['menu'][0].any? { |item| item.include?('Pão de milho') && item.include?('Contém glúten') }
    assert value['menu'][1].any? { |item| item.include?('Lombo ao molho ferrugem') }
    assert value['menu'][1].any? { |item| item.include?('Opção vegana: tomate recheado') }
    assert value['menu'][2].any? { |item| item.include?('Tirinhas de carne') }
  end

  def test_toledo_future_heading_without_table_does_not_discard_today
    html = File.read(File.join(__dir__, 'fixtures/toledo-2026-10-29.html'))
    result = UfprMenuParser.parse(html, today: Date.new(2026, 10, 29))
    assert_equal ['2026-10-29'], result.keys
    assert result['2026-10-29']['menu'][1].any? { |item| item.include?('Estrogonofe de carne') }
  end

  def test_each_table_belongs_to_its_own_date
    result = UfprMenuParser.parse(day('28/10/2026', 'Primeiro') + day('29/10/2026', 'Segundo'))
    assert_equal 'Primeiro', result['2026-10-28']['menu'][1].first
    assert_equal 'Segundo', result['2026-10-29']['menu'][1].first
    assert_equal [UfprMenuParser::NO_MEALS], result['2026-10-29']['menu'][0]
    assert_equal [UfprMenuParser::NO_MEALS], result['2026-10-29']['menu'][2]
  end

  def test_holiday_without_table_does_not_shift_next_day
    result = UfprMenuParser.parse('<p><strong>Quarta-Feira 28/10/2026 FERIADO</strong></p>' + day('29/10/2026', 'Segundo'))
    assert_equal [[UfprMenuParser::NO_MEALS]] * 3, result['2026-10-28']['menu']
    assert_equal 'Segundo', result['2026-10-29']['menu'][1].first
  end

  def test_missing_table_is_rejected_instead_of_shifting_dates
    assert_raises(UfprMenuParser::Error) do
      UfprMenuParser.parse('<p><strong>Quarta-Feira 28/10/2026</strong></p>' + day('29/10/2026', 'Segundo'))
    end
  end

  def test_invalid_date_duplicate_date_and_empty_page_are_rejected
    [day('31/02/2026', 'Arroz'), day('29/10/2026', 'Arroz') * 2, '<html>Indisponível</html>'].each do |html|
      assert_raises(UfprMenuParser::Error) { UfprMenuParser.parse(html) }
    end
  end

  def test_unrecognized_meal_is_not_assigned_to_lunch
    assert_raises(UfprMenuParser::Error) do
      UfprMenuParser.parse(day('29/10/2026', 'Arroz').sub('Almoço', 'Cabeçalho desconhecido'))
    end
  end
end

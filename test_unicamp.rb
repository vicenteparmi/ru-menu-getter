# frozen_string_literal: true

require 'minitest/autorun'
require_relative 'UNICAMP'

class UnicampMenusTest < Minitest::Test
  CAMPINAS_BREAKFAST = <<~HTML
    <html><body><ul><li>Cardápio café da manhã: Café com leite, achocolatado, pão, margarina, geleia e fruta.</li></ul></body></html>
  HTML

  def campinas_html(date:, lunch_restaurants:, dinner: true, dinner_restaurants: lunch_restaurants)
    cards = campinas_card('Almoço', lunch_restaurants, 'Carne com legumes', 'Arroz e feijão') +
            campinas_card('Almoço Vegano', lunch_restaurants, 'Grão-de-bico', 'Arroz integral e feijão')
    if dinner
      cards += campinas_card('Jantar', dinner_restaurants, 'Frango assado', 'Arroz e feijão') +
               campinas_card('Jantar Vegano', dinner_restaurants, 'Lentilha', 'Arroz integral e feijão')
    end
    <<~HTML
      <html><body>
        <a class="navbar-brand">Cardápio #{date.strftime('%d/%m')}</a>
        <a href="?d=#{date.iso8601}">Hoje</a>
        #{cards}
      </body></html>
    HTML
  end

  def campinas_card(title, restaurants, main, side)
    <<~HTML
      <div class="menu-section">
        <h2 class="menu-section-title">#{title}</h2>
        <div class="menu-item-name">#{main}</div>
        <div class="menu-item-description">#{side}<br>Salada<br>Observações:<br>As refeições serão servidas somente no #{restaurants.join(', ')}.</div>
      </div>
    HTML
  end

  def regional_html(date:, dinner: true)
    dinner_html = dinner ? regional_meal('vegetariano', 'Jantar bovino', 'Jantar vegano') : '<div id="vegetariano"></div>'
    <<~HTML
      <html><body>
        <input name="data" value="#{date.iso8601}">
        <div class="col-12 h3 text-center">#{date.strftime('%d/%m/%Y')} (Dia)</div>
        #{regional_meal('normal', 'Almoço bovino', 'Almoço vegano')}
        #{dinner_html}
        <div class="text-bg-primary">CAFÉ DA MANHÃ</div>
        <table><tr><td>Pão e fruta.</td></tr><tr><td>Leite e café.</td></tr></table>
      </body></html>
    HTML
  end

  def regional_meal(id, standard, vegan)
    <<~HTML
      <div id="#{id}"><table><tr><td><strong>PRATO PRINCIPAL:</strong><br>#{standard}</td></tr><tr><td><strong>ACOMPANHAMENTOS:</strong><br>Arroz e feijão</td></tr></table><table><tr><td><strong>PRATO PRINCIPAL:</strong><br>#{vegan}</td></tr><tr><td><strong>ACOMPANHAMENTOS:</strong><br>Arroz integral e feijão</td></tr></table></div>
    HTML
  end

  def test_campinas_creates_three_meal_slots_and_vegan_items
    parser = UnicampMenus::CampinasParser.new
    date = Date.new(2026, 8, 11)
    breakfast = parser.parse_breakfast(CAMPINAS_BREAKFAST)
    result = parser.parse_day(campinas_html(date: date, lunch_restaurants: %w[RA RU RS]),
                              expected_date: date, breakfast: breakfast)

    assert_equal %w[ra rs ru], result.keys.sort
    assert_equal 3, result['ru']['menu'].length
    assert_equal [UnicampMenus::NO_MEALS], result['ra']['menu'][0]
    assert result['ru']['menu'][1].any? { |item| item.start_with?('Opção vegana:') }
  end

  def test_campinas_only_publishes_rs_when_source_says_rs
    parser = UnicampMenus::CampinasParser.new
    date = Date.new(2026, 8, 12)
    result = parser.parse_day(campinas_html(date: date, lunch_restaurants: ['RS']),
                              expected_date: date, breakfast: ['Café'])

    assert_equal ['rs'], result.keys
  end

  def test_campinas_preserves_missing_dinner_slot
    parser = UnicampMenus::CampinasParser.new
    date = Date.new(2026, 8, 16)
    result = parser.parse_day(campinas_html(date: date, lunch_restaurants: ['RS'], dinner: false),
                              expected_date: date, breakfast: ['Café'])

    assert_equal [UnicampMenus::NO_MEALS], result['rs']['menu'][2]
    assert_equal 3, result['rs']['menu'].length
  end

  def test_campinas_rejects_different_standard_and_vegan_restaurants
    parser = UnicampMenus::CampinasParser.new
    date = Date.new(2026, 8, 11)
    html = campinas_html(date: date, lunch_restaurants: ['RU'])
           .sub('somente no RU.', 'somente no RS.')

    assert_raises(UnicampMenus::Error) do
      parser.parse_day(html, expected_date: date, breakfast: ['Café'])
    end
  end

  def test_campinas_real_page_with_missing_standard_dinner_service_sentence
    html = File.read(File.join(__dir__, 'tests/fixtures/unicamp-campinas-2026-10-28.html'), encoding: 'ISO-8859-1').encode('UTF-8')
    result = UnicampMenus::CampinasParser.new.parse_day(html, expected_date: Date.new(2026, 10, 28), breakfast: ['Café'])
    assert_equal %w[ra rs ru], result.keys.sort
    result.each_value do |payload|
      assert_includes payload['menu'][2], 'Prato principal: FILEZINHO DE FRANGO AO MOLHO DE ERVAS'
      assert payload['menu'][2].any? { |item| item.start_with?('Opção vegana:') }
    end
  end

  def test_campinas_can_use_standard_card_service_when_vegan_card_omits_it
    date = Date.new(2026, 10, 29)
    html = campinas_html(date: date, lunch_restaurants: ['RS'])
    doc = Nokogiri::HTML(html)
    doc.css('.menu-section')[3].at_css('.menu-item-description').content = 'Arroz integral e feijão'
    result = UnicampMenus::CampinasParser.new.parse_day(doc.to_html, expected_date: date, breakfast: ['Café'])
    assert_equal ['rs'], result.keys
    refute_equal [UnicampMenus::NO_MEALS], result['rs']['menu'][2]
  end

  def test_campinas_does_not_infer_dinner_restaurants_from_lunch
    date = Date.new(2026, 10, 29)
    doc = Nokogiri::HTML(campinas_html(date: date, lunch_restaurants: ['RS']))
    doc.css('.menu-section').drop(2).each do |card|
      card.at_css('.menu-item-description').content = 'Arroz e feijão'
    end
    assert_raises(UnicampMenus::Error) do
      UnicampMenus::CampinasParser.new.parse_day(doc.to_html, expected_date: date, breakfast: ['Café'])
    end
  end

  def test_campinas_rejects_unknown_explicit_restaurants_even_when_pair_is_valid
    date = Date.new(2026, 10, 29)
    html = campinas_html(date: date, lunch_restaurants: ['RS']).sub('somente no RS.', 'somente no XYZ.')
    assert_raises(UnicampMenus::Error) do
      UnicampMenus::CampinasParser.new.parse_day(html, expected_date: date, breakfast: ['Café'])
    end
  end

  def test_runner_keeps_regional_menus_when_campinas_fails
    runner_class = Class.new(UnicampMenus::Runner) do
      def collect_campinas(_result) = raise UnicampMenus::Error, 'source failed'
      def collect_regional(result)
        result['lim']['rli']['2026-10-29'] = { 'menu' => [['Café'], ['Almoço'], ['Jantar']] }
      end
    end
    runner = runner_class.new
    result = runner.collect
    assert_equal ['lim'], result.keys
    assert_equal 1, runner.errors.length
    assert_match 'Campinas', runner.errors.first
    assert_equal result, runner.collect(campus: 'regional')
    assert_empty runner.errors
  end

  def test_runner_keeps_valid_campinas_dates_after_a_bad_day
    date = Date.new(2026, 10, 29)
    index = '<a href="?d=2026-10-28">Yesterday</a><a href="?d=2026-10-29">Today</a>'
    day_html = campinas_html(date: date, lunch_restaurants: ['RS'])
    http = Object.new
    http.define_singleton_method(:get) do |url, params: {}, **_kwargs|
      if url == UnicampMenus::CAMPINAS_CARDAPIO_URL
        UnicampMenusTest::CAMPINAS_BREAKFAST
      elsif params.empty?
        index
      elsif params[:d] == '2026-10-28'
        '<html>bad day</html>'
      else
        day_html
      end
    end
    runner = UnicampMenus::Runner.new(http: http)
    result = runner.collect(campus: 'campinas')
    assert_equal ['2026-10-29'], result['cam']['rs'].keys
    assert_equal 1, runner.errors.length
    assert_match '2026-10-28', runner.errors.first
  end

  def test_regional_weekday_distributes_to_all_three_restaurants
    parser = UnicampMenus::RegionalParser.new
    date = Date.new(2026, 8, 11)
    result = parser.parse_day(regional_html(date: date), expected_date: date)

    assert_equal %w[rfop rli rlii], result.keys.sort
    result.each_value { |payload| assert_equal 3, payload['menu'].length }
  end

  def test_regional_saturday_excludes_rli_and_rfop_breakfast
    parser = UnicampMenus::RegionalParser.new
    date = Date.new(2026, 8, 15)
    result = parser.parse_day(regional_html(date: date), expected_date: date)

    assert_equal %w[rfop rlii], result.keys.sort
    assert_equal [UnicampMenus::NO_MEALS], result['rfop']['menu'][0]
    refute_equal [UnicampMenus::NO_MEALS], result['rlii']['menu'][0]
  end

  def test_regional_sunday_has_no_dinner
    parser = UnicampMenus::RegionalParser.new
    date = Date.new(2026, 8, 16)
    result = parser.parse_day(regional_html(date: date, dinner: false), expected_date: date)

    assert_equal [UnicampMenus::NO_MEALS], result['rlii']['menu'][2]
    assert_equal [UnicampMenus::NO_MEALS], result['rfop']['menu'][2]
  end

  def test_invalid_html_is_rejected
    assert_raises(UnicampMenus::Error) do
      UnicampMenus::CampinasParser.new.discover_dates('<html></html>')
    end
    assert_raises(UnicampMenus::Error) do
      UnicampMenus::RegionalParser.new.parse_day('<html></html>', expected_date: Date.today)
    end
  end

  def test_campinas_rejects_explicit_no_menu_response
    assert_raises(UnicampMenus::Error) do
      UnicampMenus::CampinasParser.new.parse_day(
        'Não existe cardápio cadastrado no momento!',
        expected_date: Date.new(2026, 8, 17),
        breakfast: ['Café']
      )
    end
  end
end

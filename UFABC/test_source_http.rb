require 'minitest/autorun'
require 'stringio'
require 'net/http'
require_relative 'source_http'

class UfabcSourceTest < Minitest::Test
  URL = 'https://proap.ufabc.edu.br/nutricao-e-restaurantes-universitarios/cardapio-semanal'

  def fetch_with(responses)
    calls = 0
    opener = lambda do |url, **options, &block|
      assert_equal URL, url
      assert_equal 20, options[:read_timeout]
      calls += 1
      response = responses.shift
      raise response if response.is_a?(Exception)
      block.call(StringIO.new(response))
    end
    result = nil
    URI.stub(:open, opener) do
      UfabcSource.stub(:sleep, nil) { result = yield }
    end
    [result, calls]
  end

  def http_error(code)
    io = StringIO.new
    io.define_singleton_method(:status) { [code, 'test'] }
    OpenURI::HTTPError.new(code, io)
  end

  def test_recovers_after_timeout_and_temporary_server_error
    result, calls = fetch_with([Net::ReadTimeout.new, http_error('503'), 'Cardápio: Almoço']) { UfabcSource.get(URL) }
    assert_equal 'Cardápio: Almoço', result
    assert_equal 3, calls
  end

  def test_retries_invalid_content_without_returning_it
    result, calls = fetch_with(['Indisponível', 'Almoço']) { UfabcSource.get(URL) }
    assert_equal 'Almoço', result
    assert_equal 2, calls
  end

  def test_exhaustion_still_fails_the_collector
    fetch_with([Timeout::Error.new] * 3) do
      assert_raises(Timeout::Error) { UfabcSource.get(URL) }
    end
  end

  def test_permanent_http_error_is_not_retried
    fetch_with([http_error('404')]) do
      assert_raises(OpenURI::HTTPError) { UfabcSource.get(URL) }
    end
  end
end

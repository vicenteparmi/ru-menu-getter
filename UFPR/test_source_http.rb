require 'minitest/autorun'
require 'minitest/mock'
require_relative 'source_http'

class UfprSourceHttpTest < Minitest::Test
  def test_bundled_intermediate_is_verified_against_system_roots
    certificate = OpenSSL::X509::Certificate.new(File.read(UfprSource::INTERMEDIATE))
    store = OpenSSL::X509::Store.new
    store.set_default_paths
    assert store.verify(certificate), store.error_string
    assert_includes certificate.subject.to_s, 'RNP ICPEdu GR46 OV TLS CA 2025'
    assert_equal 'E10747D4DA7BAB09CBA9952F019D3534CB9FBA070BF13D8791B1699CD2FF59DD',
                 OpenSSL::Digest::SHA256.hexdigest(certificate.to_der).upcase
    assert_instance_of OpenSSL::X509::Store, UfprSource.certificate_store
  end

  def test_untrusted_intermediate_is_rejected
    store = Object.new
    def store.set_default_paths; end
    def store.verify(_certificate) = false
    def store.error_string = 'untrusted'
    OpenSSL::X509::Store.stub(:new, store) do
      assert_raises(UfprSource::Error) { UfprSource.certificate_store }
    end
  end

  def test_only_expected_https_source_is_allowed
    ['http://p4e.ufpr.br/', 'https://example.com/', 'file:///tmp/menu', 'https://user@p4e.ufpr.br/'].each do |url|
      assert_raises(UfprSource::Error) { UfprSource.get(url) }
    end
  end
  def test_interrupted_tls_read_is_retried
    http = Net::HTTP.new('p4e.ufpr.br', 443)
    calls = 0
    request = lambda do |_request|
      calls += 1
      raise OpenSSL::SSL::SSLError, 'SSL_read: unexpected eof while reading' if calls == 1
      response = Net::HTTPOK.new('1.1', '200', 'OK')
      def response.body = '<html>menu</html>'
      response
    end
    Net::HTTP.stub(:new, http) do
      http.stub(:request, request) do
        UfprSource.stub(:sleep, nil) do
          assert_equal '<html>menu</html>', UfprSource.get('https://p4e.ufpr.br/ru/')
        end
      end
    end
    assert_equal 2, calls
  end

  def test_certificate_failure_is_not_retried
    http = Net::HTTP.new('p4e.ufpr.br', 443)
    calls = 0
    request = lambda do |_request|
      calls += 1
      raise OpenSSL::SSL::SSLError, 'certificate verify failed'
    end
    Net::HTTP.stub(:new, http) do
      http.stub(:request, request) do
        assert_raises(OpenSSL::SSL::SSLError) { UfprSource.get('https://p4e.ufpr.br/ru/') }
      end
    end
    assert_equal 1, calls
  end

end

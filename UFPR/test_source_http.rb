require 'minitest/autorun'
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
end

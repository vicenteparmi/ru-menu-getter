# frozen_string_literal: true
require 'net/http'
require 'openssl'
require 'uri'
require 'timeout'

module UfprSource
  class Error < StandardError; end
  INTERMEDIATE = File.join(__dir__, 'certs/rnp-icpedu-gr46-2025.pem')

  # Complete the server's missing chain, retaining the OS's trusted roots.
  # The bundled intermediate must itself verify against those roots.
  def self.certificate_store
    store = OpenSSL::X509::Store.new
    store.set_default_paths
    issuer = OpenSSL::X509::Certificate.new(File.read(INTERMEDIATE))
    raise Error, "UFPR intermediate verification failed: #{store.error_string}" unless store.verify(issuer)

    store.add_cert(issuer)
    store
  end

  def self.get(url, attempts: 3)
    uri = URI(url)
    unless uri.scheme == 'https' && uri.host == 'p4e.ufpr.br' && uri.userinfo.nil?
      raise Error, 'Unexpected UFPR source URL'
    end
    attempts.times do |index|
      begin
        http = Net::HTTP.new(uri.host, uri.port)
        http.use_ssl = true
        http.verify_mode = OpenSSL::SSL::VERIFY_PEER
        http.verify_hostname = true
        http.cert_store = certificate_store
        http.open_timeout = 10
        http.read_timeout = 20
        request = Net::HTTP::Get.new(uri)
        request['User-Agent'] = 'CampusDine UFPR menu collector/1.0'
        response = http.request(request)
        raise Error, "UFPR HTTP #{response.code}" unless response.is_a?(Net::HTTPSuccess)

        return response.body.force_encoding('UTF-8')
      rescue Timeout::Error, IOError, SystemCallError, Error => error
        raise if index == attempts - 1
        warn "[UFPR] #{error.class}; retry #{index + 2}/#{attempts}"
        sleep(index + 1)
      end
    end
  end
end

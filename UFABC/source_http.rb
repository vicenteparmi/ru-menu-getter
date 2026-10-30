# frozen_string_literal: true
require 'open-uri'
require 'timeout'

module UfabcSource
  class Error < StandardError; end
  USER_AGENT = 'Mozilla/5.0 (compatible; CampusDine/1.0)'

  def self.get(url, attempts: 3)
    raise ArgumentError, 'attempts must be positive' unless attempts.positive?

    attempts.times do |index|
      begin
        html = URI(url).open( 'User-Agent' => USER_AGENT, open_timeout: 10, read_timeout: 20, &:read)
        raise Error, 'UFABC source returned no menu content' unless html.match?(/cardápio|almoço/i)

        return html
      rescue OpenURI::HTTPError => error
        # Retry rate limiting and server failures, but surface permanent HTTP errors.
        raise unless error.io.status.first.match?(/\A(?:429|5\d\d)\z/)
        raise if index == attempts - 1

        warn "[UFABC] HTTP #{error.io.status.first}; retry #{index + 2}/#{attempts}"
        sleep(2 * (index + 1))
      rescue Timeout::Error, IOError, SystemCallError, Error => error
        raise if index == attempts - 1

        warn "[UFABC] #{error.class}; retry #{index + 2}/#{attempts}"
        sleep(2 * (index + 1))
      end
    end
  end
end

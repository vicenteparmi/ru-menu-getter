# Initial version: 2023-03-07
# Updated: 2025-02-21
# Currently supports: RU Central, RU Politécnico, RU Matinhos, RU Botânico, RU Agrárias, RU Palotina, RU Mirassol, RU CEM, RU Toledo, RU Jandaia do Sul
# Author: @vicenteparmi

require 'firebase'
require 'open-uri'
require 'nokogiri'
require 'json'
require 'date'

# Create the array with all the info
data = {
  "cwb" => {
    "rus" => {
      "ru-central" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-central/"
      },
      "ru-politecnico" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-centro-politecnico/"
      },
      "ru-botanico" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-jardim-botanico/"
      },
      "ru-agrarias" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-agrarias/"
      }
    },
  },
  "mat" => {
    "rus" => {
      "ru-mat" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-matinhos/"
      },
    },
  },
  "pal" => {
    "rus" => {
      "ru-pal" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-palotina/"
      },
    },
  },
  "pon" => {
    "rus" => {
      "ru-cem" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-cem/"
      },
      "ru-mir" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-mirassol/"
      }
    }
  },
  "tol" => {
    "rus" => {
      "ru-toledo" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-toledo/"
      },
    }
  },
  "jan" => {
    "rus" => {
      "ru-jandaia" => {
        "url" => "https://p4e.ufpr.br/ru/cardapio-ru-jandaia-do-sul/"
      },
    }
  }
}

require_relative 'UFPR/source_http'

require_relative 'UFPR/menu_parser'
require 'optparse'

options = { dry_run: false, output: nil }
OptionParser.new do |parser|
  parser.on('--dry-run', 'Coleta e valida sem escrever no Firebase') { options[:dry_run] = true }
  parser.on('--output FILE', 'Salva JSON coletado para conferência') { |path| options[:output] = path }
end.parse!

failed_rus = []
collected = {}
firebase = nil
unless options[:dry_run]
  abort 'BASE_URL e FIREBASE_KEY são obrigatórias para upload' if ENV['BASE_URL'].to_s.empty? || ENV['FIREBASE_KEY'].to_s.empty?
  firebase = Firebase::Client.new(ENV['BASE_URL'], ENV['FIREBASE_KEY'])
end

data.each do |city, city_data|
  city_data['rus'].each do |restaurant, settings|
    context = "#{city}/#{restaurant}"
    begin
      menus = UfprMenuParser.parse(UfprSource.get(settings['url']))
      menus.select! do |date, _payload|
        (Date.today - 7..Date.today + 14).cover?(Date.iso8601(date))
      end
      raise UfprMenuParser::Error, 'Nenhum cardápio recente publicado' if menus.empty?
      collected[city] ||= {}
      collected[city][restaurant] = menus
      menus.each do |date, payload|
        puts "[UFPR] #{context}/#{date}: coletado e validado"
        next if options[:dry_run]
        value = payload.merge('timestamp' => Time.now.to_i)
        path = "archive/menus/#{city}/rus/#{restaurant}/menus/#{date}"
        response = firebase.set(path, value)
        raise "Firebase HTTP #{response.code}" unless response.success?
        stored = firebase.get(path)
        raise 'Firebase releitura divergente' unless stored.success? && stored.body == value
        puts "[UFPR] #{context}/#{date}: gravado e verificado"
      end
    rescue StandardError => e
      warn "[UFPR ERROR] #{context}: #{e.class}: #{e.message}"
      failed_rus << { city: city, ru: restaurant, error: "#{e.class}: #{e.message}" }
    end
  end
end

File.write(options[:output], JSON.pretty_generate(collected)) if options[:output]
if ENV['GITHUB_OUTPUT']
  File.open(ENV['GITHUB_OUTPUT'], 'a') { |file| file.puts "has_failures=#{!failed_rus.empty?}" }
end
unless failed_rus.empty?
  report = "## UFPR — Falhas na coleta ou gravação\n\n"
  failed_rus.each { |failure| report += "- #{failure[:city]}/#{failure[:ru]}: #{failure[:error]}\n" }
  File.write('ufpr_failures.md', report)
end
puts "[UFPR] #{collected.values.sum(&:size)} unidades coletadas; #{failed_rus.size} falha(s)."
exit(failed_rus.empty? ? 0 : 1)

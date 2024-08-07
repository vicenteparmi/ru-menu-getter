# Initial version: 2023-03-07
# Currently supports: RU Central, RU Politécnico, RU Matinhos, RU Botânico, RU Agrárias, RU Palotina, RU Mirassol (CEM em fase de testes)
# Author: @vicenteparmi

require 'firebase'
require 'open-uri'
require 'nokogiri'

# Create the array with all the info
data = {
  "cwb" => {
    "rus" => {
      "ru-central" => {
        "url" => "https://pra.ufpr.br/ru/ru-central/"
      },
      "ru-politecnico" => {
        "url" => "https://pra.ufpr.br/ru/ru-centro-politecnico/"
      },
      "ru-botanico" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-jardim-botanico/"
      },
      "ru-agrarias" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-agrarias/"
      }
    },
  },
  "mat" => {
    "rus" => {
      "ru-mat" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-matinhos/"
      },
    },
  },
  "pal" => {
    "rus" => {
      "ru-pal" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-palotina/"
      },
    },
  },
  "pon" => {
    "rus" => {
      "ru-cem" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-cem/"
      },
      "ru-mir" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-mirassol/"
      }
    }
  }
}

# Function to scrape the menu
def scrape_menu(name, url, city)
  # Fetch the HTML content of the page

  puts "[GETTING DATA > #{city} > #{name}] Starting..."

  html_content = URI.open(url)

  # Parse the HTML content with Nokogiri
  doc = Nokogiri::HTML(html_content)

  # Initialize the arrays to store the scraped data
  menu = []

  # Format, replace <br> tags with \n and remove <a> tags.
  doc.search('br').each do |n|
    n.replace("\n")
  end

  doc.search('a').each do |n|
    n.replace("")
  end

  # Get the date of the meals inside the <p><strong> tag
  date = []
  weekday = []
  doc.search('p').each do |p_element|
    strong_elements = p_element.search('strong')
    
    begin
      # Combine text from all strong elements within the p tag
      combined_text = strong_elements.map(&:text).join
  
      # Split the combined text into an array of strings
      split_text = combined_text.split(/( – |: | )/)
  
      # Skip if the words "FERIADO", "RECESSO" or "alterações" are present
      if combined_text.include?("FERIADO") || combined_text.include?("RECESSO") || combined_text.include?("alterações")
        puts "[GETTING DATA > #{city} > #{name}] Skipping date (FERIAS/RECESSO) #{split_text[0]}..."
        next
      end
  
      # Check if the date is empty or doesn't contain "/"
      if split_text[2].nil? || split_text[2].empty? || !split_text[2].include?("/")
        puts "[GETTING DATA > #{city} > #{name}] Error parsing date: invalid format (#{combined_text}). Skipping..."
        next
      end
  
      # Separate the date from the day of the week
      date << split_text[2]
  
      # Remove ":" from the day of the week
      split_text[0].slice!(":")
      weekday << split_text[0]
  
    rescue => error
      puts "[GETTING DATA > #{city} > #{name}] Error parsing date: #{error.message}. Skipping..."
      next  # Skip this iteration if date parsing failed
    end
  end

  # Get the menu of the meals inside the <figure class="wp-block-table"> tag
  menut = []
  doc.search('figure.wp-block-table').each do |element|

    # Divide the meals by day and meal types ["CAFÉ DA MANHÃ", "ALMOÇO", "JANTAR"]
    cafe_da_manha = element.text.split("ALMOÇO")[0]

    # Check if the RU has dinner
    if element.text.split("ALMOÇO")[1].split("JANTAR")[1].nil?
      almoco = element.text.split("ALMOÇO")[1]
      jantar = ""
    else
      almoco = element.text.split("ALMOÇO")[1].split("JANTAR")[0]
      jantar = element.text.split("ALMOÇO")[1].split("JANTAR")[1]
    end

    # Remove the meal type from the strings
    begin
      cafe_da_manha.slice! "CAFÉ DA MANHÃ"
      almoco.slice! "ALMOÇO"

      # Check if the RU has dinner
      if element.text.split("ALMOÇO")[1].split("JANTAR")[1].nil?
        jantar = ""
      else
        jantar.slice! "JANTAR"
      end
    rescue NoMethodError => e
      puts "[GETTING DATA > #{city} > #{name}] Error parsing meal type: #{e.message} #{date}. Skipping..." # When the people at the RU do not add the meal...
      next  # Skip this iteration if meal type parsing failed
    end

    # Break the string into an array of strings
    cafe_da_manha = cafe_da_manha.split("\n")
    almoco = almoco.split("\n")

    # Check if the RU has dinner
    if element.text.split("ALMOÇO")[1].split("JANTAR")[1].nil?
      jantar = ""
    else
      jantar = jantar.split("\n")
    end

    # Replace '  ' with ' ' in the array, loop 3 times
    for i in 0..2
      cafe_da_manha.each do |element|
        element.gsub!('  ', ' ')
      end
      almoco.each do |element|
        element.gsub!('  ', ' ')
      end

      # Check if the RU has dinner
      if element.text.split("ALMOÇO")[1].split("JANTAR")[1].nil?
        jantar = ["Sem refeições disponíveis"]
      else
        jantar.each do |element|
          element.gsub!('  ', ' ')
        end
      end

      # Remove empty elements
      cafe_da_manha.delete("")
      almoco.delete("")
      jantar.delete("")
    end

    # Build the menu array item for this day
    element = [
      cafe_da_manha,
      almoco,
      jantar
    ]

    menut << element
  end

  for i in 0..menut.length-1
    element = [
      date[i],
      weekday[i],
      menut[i],
      Time.now.to_i
    ]
    menu[i] = element
  end

  # Send to firebase database
  # Initialize Firebase
  base_uri = ENV['BASE_URL']
  secret = ENV['FIREBASE_KEY']

  firebase = Firebase::Client.new(base_uri, secret)

  # Check if the menu already exists for each date, if not, push new menu
  menu.each do |element|

    # Parse element[0] to date format, first convert to timestamp, then to date
    # The date may be in the format 20/09/2021 or 20/09/21
    date_parts = element[0].split("/")

    if date_parts.length >= 3
      year = date_parts[2].length == 4 ? date_parts[2] : "20#{date_parts[2]}"
      month = date_parts[1].rjust(2, '0')
      day = date_parts[0].rjust(2, '0')
      date_str = "#{year}-#{month}-#{day}"
    else
      puts "[GETTING DATA > #{city} > #{name}] Error parsing date: invalid format (#{element[0]}). Skipping..."
      next  # Skip this iteration if date parsing failed
    end

    element[0] = date_str

    # Update the database
    response = firebase.set("menus/#{city}/rus/#{name}/menus/#{element[0]}", { :weekday => element[1], :menu => element[2], :timestamp => element[3] })

    # Return the response
    puts "[GETTING DATA > #{city} > #{name}] Response: #{response.code}. Finished for #{element[0]}."
  end
end

# Convert the data hash to an array
data_array = data.to_a

# Repeat for each city
data.each do |city|
  # Get the city name
  city_name = city[0]

  # Display the city name
  puts "[GETTING DATA > #{city_name}] Starting..."

  # Get the RU list
  rus = city[1]["rus"]

  # Check if the RU list is present
  if rus.nil?
    puts "[GETTING DATA > #{city_name}] No RUs found. Skipping..."
    next
  end

  # Repeat for each RU
  rus.each do |ru_name, ru_data|
    # Get the RU URL
    url = ru_data["url"]

    # Call the function to scrape the menu
    # Add delay to avoid being blocked
    sleep(10)
    begin
      scrape_menu(ru_name, url, city_name)
    rescue NoMethodError => e
      puts "Error on the scrape function: #{e.message}. Skipping..."
    end  
  end
end
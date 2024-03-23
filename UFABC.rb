# Initial version: 2024-03-22
# Currently supports: RU ABC
# Author: @vicenteparmi

require 'firebase'
require 'open-uri'
require 'nokogiri'

# Create the array with all the info
data = {
  "abc" => {
    "rus" => {
      "abc" => {
        "url" => "https://proap.ufabc.edu.br/nutricao-e-restaurantes-universitarios/cardapio-semanal"
      },
    },
  },
}

# Function to scrape the menu
def scrape_menu(name, url, city)
  # Fetch the HTML content of the page

  puts "[GETTING DATA > #{city} > #{name}] Starting..."

  html_content = URI.open(url)

  # Parse the HTML content with Nokogiri
  page_data = Nokogiri::HTML(html_content)

  # Filter doc content to get only the menu (inside the div with the class "cardapio-semanal")
  doc = page_data.css(".cardapio-semanal")

  # Initialize the arrays to store the scraped data
  menu = []

  # Get the date of all the menus. The date is in the format 18/03 (day/month) and is inside a css class called "span8", inside a table that can be fount as
  dates = doc.css(".span8").map { |date| date.text ? date.text.split.first : nil }.compact

  # Parse the date to the format YYYY-MM-DD
  dates = dates.map do |date|
    date_parts = date.split("/")
    year = Time.now.year
    month = date_parts[1].rjust(2, '0')
    day = date_parts[0].rjust(2, '0')
    "#{year}-#{month}-#{day}"
  end

  # Get the menu of all the meals. The menu is in the format:
  # Almoço:
  #  * item 1
  #  * item 2
  #  * ...
  #
  # Jantar:
  #  * item 1
  #  * item 2
  #  * ...
  #
  # Saladas:
  #  * item 1
  #  * item 2
  #  * ...
  #
  # Sobremesas:
  #  * item 1
  #  * item 2
  #  * ...
  # 
  # Inside a table row (tr) that doesnt have the class "bgCinza". The meal title (Almoço, Jantar, etc) is inside h3 tags. The content is inside a ul with class "listagem"

  almoco = doc.css("tr:not(.bgCinza) h3:contains('Almoço') + ul").map { |menu| menu.css("li").map { |item| item.text } }
  jantar = doc.css("tr:not(.bgCinza) h3:contains('Jantar') + ul").map { |menu| menu.css("li").map { |item| item.text } }

  # Append saladas and sobremesas to almoço and jantar
  almoco = almoco.map.with_index do |menu, index|
    if menu.nil?
      menu = ["Não disponível"]
    else
      saladas = doc.css("tr:not(.bgCinza) h3:contains('Saladas') + ul")[index].css("li").map { |item| item.text }
      sobremesas = doc.css("tr:not(.bgCinza) h3:contains('Sobremesas') + ul")[index].css("li").map { |item| item.text }
      menu += saladas
      menu += sobremesas
    end
    menu
  end

  jantar = jantar.map.with_index do |menu, index|
    if menu.nil? || menu.empty?
      menu = ["Não disponível"]
    else
      saladas = doc.css("tr:not(.bgCinza) h3:contains('Saladas') + ul")[index].css("li").map { |item| item.text }
      sobremesas = doc.css("tr:not(.bgCinza) h3:contains('Sobremesas') + ul")[index].css("li").map { |item| item.text }
      menu += saladas
      menu += sobremesas
    end
    menu
  end

  # Make a element for each date
  for i in 0..dates.length-1
    # Get the date and weekday
    date = dates[i]

    # Get the weekday in portuguese
    weekdays = {
      'Sunday' => 'Domingo',
      'Monday' => 'Segunda-feira',
      'Tuesday' => 'Terça-feira',
      'Wednesday' => 'Quarta-feira',
      'Thursday' => 'Quinta-feira',
      'Friday' => 'Sexta-feira',
      'Saturday' => 'Sábado'
    }

    weekday = weekdays[Time.parse(date).strftime("%A")]

    # Get the menu
    element = [
      date,
      weekday,
      [["Não disponível"], almoco[i], jantar[i]],
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
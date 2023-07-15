# Initial version: 2023-03-07
# Currently supports: RU Central, RU Politécnico, RU Matinhos
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
    },
  },
  "mat" => {
    "rus" => {
      "ru-mat" => {
        "url" => "https://pra.ufpr.br/ru/cardapio-ru-matinhos/"
      },
    },
  },
}

# Function to scrape the menu
def scrape_menu(name, url, city)
  # Fetch the HTML content of the page

  puts "Scraping #{name}..."
  puts "URL: #{url}"

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
  doc.search('p strong').each do |element|
    # Separate the date from the day of the week
    date << element.text.split(" ")[1]

    # Remove ":" from the day of the week
    element.text.split(" ")[0].slice! ":"
    weekday << element.text.split(" ")[0]
  end

  # Remove last two elements of the array
  # The last two elements are random strings, not dates
  date.pop(2)

  # Get the menu of the meals inside the <figure class="wp-block-table"> tag
  menut = []
  doc.search('figure.wp-block-table').each do |element|

    # Divide the meals by day and meal types ["CAFÉ DA MANHÃ", "ALMOÇO", "JANTAR"]
    cafe_da_manha = element.text.split("ALMOÇO")[0]
    almoco = element.text.split("ALMOÇO")[1].split("JANTAR")[0]
    jantar = element.text.split("ALMOÇO")[1].split("JANTAR")[1]

    # Remove the meal type from the strings
    cafe_da_manha.slice! "CAFÉ DA MANHÃ"
    almoco.slice! "ALMOÇO"
    jantar.slice! "JANTAR"

    # Break the string into an array of strings
    cafe_da_manha = cafe_da_manha.split("\n")
    almoco = almoco.split("\n")
    jantar = jantar.split("\n")

    # Build the menu array item for this day
    element = [
      cafe_da_manha,
      almoco,
      jantar
    ]

    menut << element
  end

  for i in 0..date.length-1
    element = [
      date[i],
      weekday[i],
      menut[i],
      Time.now.to_i
    ]
    menu[i] = element
  end

  # Send to firebase database
  base_uri = 'https://campusdine-menu-default-rtdb.firebaseio.com'
  secret = ENV['FIREBASE_KEY'] 
  firebase = Firebase::Client.new(base_uri, secret)

  # Check if the menu already exists for each date, if not, push new menu
  menu.each do |element|

    # Parse element[0] to date format, first convert to timestamp, then to date
    # The date may be in the format 20/09/2021 or 20/09/21
    date_parts = element[0].split("/")
    if date_parts[2]&.length == 4
      date_format = '%d/%m/%Y'  # Format for date with 4-digit year
    else
      date_format = '%d/%m/%y'  # Format for date with 2-digit year
    end

    begin
      date = Date.strptime(element[0], date_format)
    rescue Date::Error => e
      puts "Error parsing date: #{e.message}. Skipping..." # Sometimes it gets some random string instead of a date
      next  # Skip this iteration if date parsing failed
    end

    element[0] = date.strftime("%Y-%m-%d")


  
    # Check if the menu already exists
    response = firebase.get("menus/#{city}/rus/#{name}/menus/#{element[0]}")
    if response.body == nil
      # Push new menu
      response = firebase.update("menus/#{city}/rus/#{name}/menus/#{element[0]}", { :weekday => element[1], :menu => element[2], :timestamp => element[3] })
    end

    # Return the response
    puts "Response code: #{response.code}. Finished scraping #{name} for the date #{element[0]}."
  end
end

# Convert the data hash to an array
data_array = data.to_a

# Repeat for each city
data.each do |city|
  # Get the city name
  city_name = city[0]

  # Display the city name
  puts "City: #{city_name}"

  # Get the RU list
  rus = city[1]["rus"]

  # Check if the RU list is present
  if rus.nil?
    puts "No RUs found for #{city_name}. Skipping..."
    next
  end

  # Repeat for each RU
  rus.each do |ru_name, ru_data|
    # Display the RU name as key, not the name value
    puts "RU: #{ru_name}"

    # Get the RU URL
    url = ru_data["url"]

    # Call the function to scrape the menu
    # Add delay to avoid being blocked
    sleep(10)
    scrape_menu(ru_name, url, city_name)
  end
end

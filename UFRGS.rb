# Initial version: 2024-03-22
# Currently supports: RU ABC
# Author: @vicenteparmi

require 'firebase'
require 'open-uri'
require 'nokogiri'

# Create the array with all the info
data = {
  "poa" => {
    "rus" => {
      "ru01" => {},
      "ru02" => {},
      "ru03" => {},
      "ru04" => {},
      "ru05" => {},
      "ru06" => {},
    },
  },
}

url = "https://www.ufrgs.br/prae/cardapio-ru/"

# Function to extract the date range from a string
def extract_date_range(string)

  # String format: "Almoço 01/03 a 05/03" or "Jantar 1 a 05/03"
  # Split the string into words
  words = string.split(" ")

  # Extract the meal type (e.g., "Almoço" or "Jantar")
  meal_type = words.first

  # Extract the initial and final dates
  
  # Check if the date is in the format "dd/mm a dd/mm" or "d a dd/mm"
  if words[2].include?("/")
    initial_date = words[1]
    final_date = words[3]
  else
    initial_date = words[1] + "/" + words[3].split("/").last
    final_date = words[3]
  end

  # Convert to date format yyyy-mm-dd
  initial_date = Date.strptime(initial_date, "%d/%m").strftime("%Y-%m-%d")
  final_date = Date.strptime(final_date, "%d/%m").strftime("%Y-%m-%d")

  # Calculate the difference between the initial and final dates
  date_difference = (Date.parse(final_date) - Date.parse(initial_date)).to_i

  # Return the extracted data
  { meal_type: meal_type, initial_date: initial_date, final_date: final_date, date_difference: date_difference }
end

# Function to scrape the menu
def scrape_menu(name, page_data, city)
  # Fetch the HTML content of the page

  puts "[GETTING DATA > #{city} > #{name}] Starting..."

  # First, get the date of the menu, inside the ".elementor-toggle-title" div
  page_data.each do |element|

    # Get element from Nokogiri object
    dates_title = element.css('.elementor-toggle-title').text

    # Extract the date range
    title_content = extract_date_range(dates_title)

    # Calc the difference between the initial and final dates
    date_difference = title_content[:date_difference]

    dates = []
      
    # Create the list with the dates
    (0..date_difference).each do |i|
      # Get the weekday
      parsed_date = Date.parse(title_content[:initial_date]) + i
      weekday = parsed_date.strftime("%A")

      # Add the date to the list in the format "yyyy-mm-dd"
      dates.push([parsed_date.strftime("%Y-%m-%d"), weekday])
    end

    # Parse the menu data
    # The data is in a table divided by week day, with rows for each item of the meal
    # The first column is monday, the second is tuesday, and so on, until friday

    # Get the data for each day of the week
    # The data is inside a table inside the ".elementor-tab-content" div
    # The first row is the header, with the weekdays
    weekdays = Array.new(5)
    meals = Array.new(weekdays.length) { [] }

    element.css('.elementor-tab-content').css('tr').each_with_index do |row, index|
      # Store the weekdays
      if index == 0
        row.css('td').each_with_index do |weekday, i|
          weekdays[i] = weekday.text
        end
      else
        # Store the meals
        row.css('td').each_with_index do |item, i|
          meals[i].push(item.text)
        end
      end
    end

    # Create the element for each date and upload
    dates.each_with_index do |date, index|

      # Get the meal for the date
      meal = title_content[:meal_type]

      # Get the id for the meal
      id = 0
      if meal == "Jantar"
        id = 1
      end

      # Skip if the meal contains "FERIADO" or "RECESSO"
      if meals[index].include?("FERIADO") || meals[index].include?("RECESSO")
        next
      end

      # Remove empty items from the meals list
      meals[index].delete_if { |item| item.empty? }

      # Initialize Firebase
      base_uri = ENV['BASE_URL']
      secret = ENV['FIREBASE_KEY']

      firebase = Firebase::Client.new(base_uri, secret)

      # Retrieve the current menu from the database
      current_menu = firebase.get("menus/#{city}/rus/#{name}/menus/#{date[0]}").body["menu"] rescue nil

      # If the current menu doesn't exist, initialize it as an array of empty arrays
      current_menu = [["Não definido"],["Não definido"],["Não definido"]] if current_menu.nil?

      # Update the current menu with the new meals
      current_menu[id+1] = meals[index]

      # Update the database
      response = firebase.update("menus/#{city}/rus/#{name}/menus/#{date[0]}", { :weekday => weekdays[index], :menu => current_menu, :timestamp => Time.now.to_i })

      # Return the response
      puts "[GETTING DATA > #{city} > #{name}] Response: #{response.code}. Finished for #{date[0]}."
    end

  # # Send to firebase database
  # # Initialize Firebase
  # base_uri = ENV['BASE_URL']
  # secret = ENV['FIREBASE_KEY']

  # firebase = Firebase::Client.new(base_uri, secret)

  # # Check if the menu already exists for each date, if not, push new menu
  # menu.each do |element|
  #   # Update the database
  #   response = firebase.set("menus/#{city}/rus/#{name}/menus/#{element[0]}", { :weekday => element[1], :menu => element[2], :timestamp => element[3] })

  #   # Return the response
  #   puts "[GETTING DATA > #{city} > #{name}] Response: #{response.code}. Finished for #{element[0]}."
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

  # Open URL and get the HTML content
  html_content = URI.open(url)

  # Parse the HTML content with Nokogiri
  page_data = Nokogiri::HTML(html_content)

  # Get the data for each location, that is inside a ".elementor-widget-wrap" div
  # This data will be send to the scrape_menu function
  
  # Make a array with the data for the locations
  locations_data = []

  # Get the data for each location
  page_data.css('.elementor-column.elementor-col-50.elementor-top-column.elementor-element').each do |location|
    # Put the data in the array with the menu data that is inside ".elementor-widget-toggle" div
    # as a list of elements, one for each meal. Preserve the Nokogiri object. If the data is not present, skip.
    if location.css('.elementor-toggle-item').empty?
      next
    else
      toggles = []
      location.css('.elementor-toggle-item').each do |toggle|
        toggles.push(toggle)
      end
      locations_data.push(toggles)
    end
  end

  # Repeat for each RU, with index
  rus.each_with_index do |ru, index|

    # Get the RU name as the key
    ru_name = ru[0]

    # Get the menus for the 6 RUs
    # Call the function to scrape the menu
    # Add delay to avoid being blocked
    sleep(10)
    begin
      scrape_menu(ru_name, locations_data[index], city_name)
    rescue NoMethodError => e
      puts "Error on the scrape function: #{e.message}. Skipping..."
    end  
  end
end
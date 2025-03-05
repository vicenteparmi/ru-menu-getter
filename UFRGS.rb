# Initial version: 2024-03-22
# Updated version: 2025-03-05
# Currently supports: RU01, RU02, RU03, RU04, RU05, RU06
# Author: @vicenteparmi

# Not working! Feel free to contribute and fix it!

require 'firebase'
require 'open-uri'
require 'nokogiri'
require 'date'
require 'net/http'
require 'openssl'

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

# Function to fetch a URL with retry logic and improved SSL handling
def fetch_with_retry(url, max_retries=3, timeout=30)
  retries = 0
  
  begin
    uri = URI(url)
    response = nil
    
    # Configure Net::HTTP with more detailed SSL options
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')
    http.open_timeout = timeout
    http.read_timeout = timeout
    
    # Enhanced SSL configuration
    if http.use_ssl?
      http.verify_mode = OpenSSL::SSL::VERIFY_PEER
      http.ssl_version = :TLSv1_2  # Force TLS 1.2
      
      # Set a more permissive cipher list
      http.ciphers = 'DEFAULT:!aNULL:!eNULL:!LOW:!EXPORT:!SSLv2'
    end
    
    # Make the request
    request = Net::HTTP::Get.new(uri)
    request['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    request['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    request['Accept-Language'] = 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    request['Cache-Control'] = 'no-cache'
    request['Connection'] = 'keep-alive'
    
    response = http.request(request)
    
    if response.is_a?(Net::HTTPSuccess)
      return response.body
    else
      raise "HTTP request failed with code #{response.code}"
    end
    
  rescue Net::OpenTimeout, Net::ReadTimeout => e
    retries += 1
    if retries < max_retries
      puts "Connection timed out. Retrying (#{retries}/#{max_retries})..."
      sleep(5 * retries)  # Increased delay between retries
      retry
    else
      raise "Failed to connect to #{url} after #{max_retries} attempts: #{e.message}"
    end
  rescue => e
    retries += 1
    if retries < max_retries
      puts "Error: #{e.message}. Retrying (#{retries}/#{max_retries})..."
      sleep(5 * retries)
      retry
    else
      raise
    end
  end
end

# Fallback method using open-uri if Net::HTTP fails
def fetch_with_open_uri(url, max_retries=3)
  retries = 0
  
  begin
    URI.open(url, 
      'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      :read_timeout => 60,
      :ssl_verify_mode => OpenSSL::SSL::VERIFY_NONE
    ).read
  rescue => e
    retries += 1
    if retries < max_retries
      puts "Error with open-uri: #{e.message}. Retrying (#{retries}/#{max_retries})..."
      sleep(5 * retries)
      retry
    else
      raise
    end
  end
end

# Function to extract the date range from a string
def extract_date_range(string)
  begin
    # Split the string into words
    words = string.split(" ")
    # Extract the meal type (e.g., "Almoço" or "Jantar")
    meal_type = words.first

    # Get today's year
    current_year = Date.today.year

    if words.include?("de")
      # Handle format like "Almoço 17 a 21 de fevereiro"
      month_index = words.index("de")
      month_name = words[month_index + 1].downcase

      month = {
        "janeiro" => "01", "fevereiro" => "02", "março" => "03", "abril" => "04",
        "maio" => "05", "junho" => "06", "julho" => "07", "agosto" => "08",
        "setembro" => "09", "outubro" => "10", "novembro" => "11", "dezembro" => "12"
      }[month_name]

      start_day = words[words.index("a") - 1]
      end_day = words[words.index("a") + 1]

      initial_date = "#{start_day}/#{month}/#{current_year}"
      final_date = "#{end_day}/#{month}/#{current_year}"
    elsif words.length > 3 && words[3].include?("/")
      # Handle format like "Almoço 01/03 a 05/03"
      initial_date = words[1]
      final_date = words[3]

      # Add year if not present
      if initial_date.split('/').length < 3
        initial_date = "#{initial_date}/#{current_year}"
      end
      if final_date.split('/').length < 3
        final_date = "#{final_date}/#{current_year}"
      end
    elsif words.length > 3 && words[1].match(/^\d+$/) && words[3].include?("/")
      # Handle format like "Jantar 1 a 05/03"
      month_day = words[3].split("/")
      initial_date = "#{words[1]}/#{month_day.last}/#{current_year}"
      final_date = words[3] + "/#{current_year}"
    else
      # Try to handle other formats or fallback to today's date
      puts "Warning: Unrecognized date format in '#{string}'"
      today = Date.today
      initial_date = today.strftime("%d/%m/%Y")
      final_date = today.strftime("%d/%m/%Y")
    end

    # Convert dates to format yyyy-mm-dd
    initial_date_parsed = Date.parse(initial_date.gsub('/', '-'))
    final_date_parsed = Date.parse(final_date.gsub('/', '-'))

    # Format dates as yyyy-mm-dd
    initial_date_formatted = initial_date_parsed.strftime("%Y-%m-%d")
    final_date_formatted = final_date_parsed.strftime("%Y-%m-%d")
    
    # Calculate the difference between the initial and final dates
    date_difference = (final_date_parsed - initial_date_parsed).to_i

    { meal_type: meal_type, initial_date: initial_date_formatted, final_date: final_date_formatted, date_difference: date_difference }
  rescue => e
    puts "Error extracting date range from '#{string}': #{e.message}"
    # Return a fallback with today's date
    today = Date.today
    { 
      meal_type: string.split(" ").first || "Desconhecido", 
      initial_date: today.strftime("%Y-%m-%d"), 
      final_date: today.strftime("%Y-%m-%d"), 
      date_difference: 0 
    }
  end
end

# Function to clean text content by removing extra whitespaces
def clean_text(text)
  text.to_s.strip.gsub(/\s+/, ' ')
end

# Function to scrape the menu
def scrape_menu(ru_name, toggle_items, city)
  puts "[GETTING DATA > #{city} > #{ru_name}] Starting..."

  # Process each menu toggle (meal type - lunch/dinner)
  toggle_items.each do |toggle_item|
    begin
      # Extract the toggle title (contains date range info)
      toggle_title = toggle_item.css('.elementor-toggle-title').text.strip
      
      # Skip if menu is marked as CLOSED
      if toggle_item.css('.elementor-tab-content').text.strip == "FECHADO"
        puts "[GETTING DATA > #{city} > #{ru_name}] #{toggle_title} is closed. Skipping..."
        next
      end
      
      # Extract date information
      title_content = extract_date_range(toggle_title)
      puts "[GETTING DATA > #{city} > #{ru_name}] Processing #{title_content[:meal_type]} menu from #{title_content[:initial_date]} to #{title_content[:final_date]}"
      
      # Calculate the difference between dates to get all the days in the range
      date_difference = title_content[:date_difference]
      
      # Calculate all dates in the range
      dates = []
      (0..date_difference).each do |i|
        parsed_date = Date.parse(title_content[:initial_date]) + i
        weekday = parsed_date.strftime("%A")
        dates.push([parsed_date.strftime("%Y-%m-%d"), weekday])
      end

      # Get the menu table
      menu_table = toggle_item.css('.elementor-tab-content table')
      
      # Skip if no table is found
      if menu_table.empty?
        puts "[GETTING DATA > #{city} > #{ru_name}] No menu table found for #{toggle_title}. Skipping..."
        next
      end

      # Extract weekday headers from the first row
      weekday_headers = []
      menu_table.css('tr:first-child td').each do |td|
        weekday_headers << clean_text(td.text)
      end
      # Initialize meals for each weekday
      meals = Array.new(weekday_headers.length) { [] }breakfast, 1 for lunch, 2 for dinner)

      # Process each row in the table except for the header rownt[:meal_type].downcase.include?("jantar")
      menu_table.css('tr:not(:first-child)').each do |row|
        row.css('td').each_with_index do |cell, index|ontent[:meal_type].downcase.include?("café") || title_content[:meal_type].downcase.include?("cafe")
          # Skip if index is out of range for the meals arrayeal_id = 0
          next if index >= meals.length      end
          
          cell_text = clean_text(cell.text)
          meals[index] << cell_text unless cell_text.empty?|date_info, index|
        end]
      endweekday = date_info[1]

      # Get the meal type ID (0 for breakfast, 1 for lunch, 2 for dinner)
      meal_id = 1 # Default to lunche?("RECESSO") })
      if title_content[:meal_type].downcase.include?("jantar") "[GETTING DATA > #{city} > #{ru_name}] #{weekday} (#{date_str}) is closed. Skipping..."
        meal_id = 2 ext
      elsif title_content[:meal_type].downcase.include?("café") || title_content[:meal_type].downcase.include?("cafe")end
        meal_id = 0
      endrray bounds)

      # Process each date and update the database "[GETTING DATA > #{city} > #{ru_name}] No meals found for #{weekday} (#{date_str}). Skipping..."
      dates.each_with_index do |date_info, index|ext
        date_str = date_info[0]        end
        weekday = date_info[1]
        
        # Skip if this weekday's meals contains "FECHADO" or "RECESSO"
        if index < meals.length && (meals[index].any? { |item| item.include?("FECHADO") || item.include?("RECESSO") })
          puts "[GETTING DATA > #{city} > #{ru_name}] #{weekday} (#{date_str}) is closed. Skipping..."          secret = ENV['FIREBASE_KEY']
          next
        end
        aise "Firebase credentials missing. Check BASE_URL and FIREBASE_KEY environment variables."
        # Skip if this date has no meals (outside the array bounds)          end
        if index >= meals.length || meals[index].empty?
          puts "[GETTING DATA > #{city} > #{ru_name}] No meals found for #{weekday} (#{date_str}). Skipping..."          firebase = Firebase::Client.new(base_uri, secret)
          next
        end
          current_menu = firebase.get("menus/#{city}/rus/#{ru_name}/menus/#{date_str}").body["menu"] rescue nil
        begin
          # Initialize Firebase
          base_uri = ENV['BASE_URL']          current_menu = [["Sem refeições disponíveis"],["Sem refeições disponíveis"],["Sem refeições disponíveis"]] if current_menu.nil?
          secret = ENV['FIREBASE_KEY']
ew meals
          if base_uri.nil? || secret.nil?          current_menu[meal_id] = meals[index]
            raise "Firebase credentials missing. Check BASE_URL and FIREBASE_KEY environment variables."
          end
ty}/rus/#{ru_name}/menus/#{date_str}", { 
          firebase = Firebase::Client.new(base_uri, secret)ders[index], 

          # Retrieve the current menu from the database:timestamp => Time.now.to_i 
          current_menu = firebase.get("menus/#{city}/rus/#{ru_name}/menus/#{date_str}").body["menu"] rescue nil          })

          # If the current menu doesn't exist, initialize it as an array of empty arrays
          current_menu = [["Sem refeições disponíveis"],["Sem refeições disponíveis"],["Sem refeições disponíveis"]] if current_menu.nil?TTING DATA > #{city} > #{ru_name}] Response: #{response.code}. Finished for #{date_str}."

          # Update the current menu with the new mealsuts "[GETTING DATA > #{city} > #{ru_name}] Error updating database for #{date_str}: #{e.message}"
          current_menu[meal_id] = meals[index]nd

          # Update the database
          response = firebase.update("menus/#{city}/rus/#{ru_name}/menus/#{date_str}", {  Error processing menu: #{e.message}"
            :weekday => weekday_headers[index], uts e.backtrace.join("\n") if ENV['DEBUG']
            :menu => current_menu, nd
            :timestamp => Time.now.to_i nd
          })end

          # Log the responsen execution block
          puts "[GETTING DATA > #{city} > #{ru_name}] Response: #{response.code}. Finished for #{date_str}."
        rescue => e  puts "Starting UFRGS menu data collection..."

  # Repeat for each city
  data.each do |city_name, city_data|
    puts "[GETTING DATA > #{city_name}] Starting..."

    # Get the RU list
    rus = city_data["rus"]

    # Check if the RU list is present
    if rus.nil? || rus.empty?
      puts "[GETTING DATA > #{city_name}] No RUs found. Skipping..."
      next
    end

    begin
      # Use the new fetch_with_retry function to get HTML content
      puts "[GETTING DATA > #{city_name}] Fetching URL: #{url}"
      html_content = fetch_with_retry(url, 5, 45)  # 5 attempts with 45 second timeout
      
      # Parse the HTML content with Nokogiri
      page_data = Nokogiri::HTML(html_content)

      # Find all restaurant sections - these contain both restaurant info and menus
      restaurant_sections = page_data.css('section.elementor-section').select do |section|
        section.css('.elementor-image-box-title').text.strip.match(/^RU\d+\s*-/)
      end

      # Collect data for each restaurant
      restaurant_data = []
      
      restaurant_sections.each do |section|
        # Get restaurant name from heading
        ru_title = section.css('.elementor-image-box-title').text.strip
        ru_number = ru_title.match(/^RU(\d+)/)[1] rescue nil
        
        next if ru_number.nil?
        
        # Find all toggle items (menus) in this section
        toggle_items = section.css('.elementor-toggle-item')
        
        restaurant_data << {
          ru_number: ru_number.to_i,
          ru_key: "ru#{ru_number.rjust(2, '0')}",
          toggle_items: toggle_items
        }
      end

      # Process each restaurant
      rus.each do |ru_key, _|
        # Find the corresponding restaurant data
        ru_data = restaurant_data.find { |data| data[:ru_key] == ru_key }
        
        if ru_data
          # Add some delay to avoid being blocked
          sleep(2)
          begin
            scrape_menu(ru_key, ru_data[:toggle_items], city_name)
          rescue => e
            puts "[GETTING DATA > #{city_name} > #{ru_key}] Error in scrape_menu: #{e.message}"
          end
        else
          puts "[GETTING DATA > #{city_name} > #{ru_key}] No data found for this restaurant. Skipping..."
        end
      end
      
    rescue => e
      puts "[GETTING DATA > #{city_name}] Error fetching or processing data: #{e.message}"
      puts e.backtrace.join("\n") if ENV['DEBUG']
    end
  end

  puts "UFRGS menu data collection completed!"
rescue => e
  puts "Fatal error: #{e.message}"
  puts e.backtrace.join("\n") if ENV['DEBUG']
end
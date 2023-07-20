# Initial version: 2023-03-19
# Author: @vicenteparmi

require 'firebase'

def moveData()
    # Initialize Firebase
    base_uri = ENV['BASE_URL']
    secret = ENV['FIREBASE_KEY']
    firebase = Firebase::Client.new(base_uri, secret)
  
    # Get the references to the old and new data
    old_ref = firebase.get("menus")
    new_ref = firebase.get("archive/menus")
  
    # Get the data from the database for each city, then each RU, and copy all days to the archive
    old_ref.body.each do |city, city_data|
      city_data["rus"].each do |ru, ru_data|
        begin
          ru_data["menus"].each do |date, date_data|
            # Copy the data to the archive
            response = firebase.get("menus/#{city}/rus/#{ru}/menus/#{date}")
            response = firebase.set("archive/menus/#{city}/rus/#{ru}/menus/#{date}", response.body)
            # Remove the data from the old database
            response = firebase.delete("menus/#{city}/rus/#{ru}/menus/#{date}")
  
            # Return the response
            puts "[ARCHIVING] Finished #{ru} for #{date}."
  
            # Add delay to avoid being blocked
            sleep(1)
          end
        rescue NoMethodError => e
          puts "[ARCHIVING] No menus found for #{ru}. Skipping..."
          next
        end
      end
    end
  
    # Return the response
    puts "[ARCHIVING] Finished moving data."
  end
  
  # Call the function to move the data
  moveData()
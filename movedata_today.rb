# Initial version: 2023-03-19
# Author: @vicenteparmi

require 'firebase'
require "google/cloud/firestore"

def moveData()
    # Initialize Firebase
    base_uri = ENV['BASE_URL']
    secret = ENV['FIREBASE_KEY']
    service_account_json = ENV['GCLOUD_ADMIN']
    firebase = Firebase::Client.new(base_uri, secret)
    firestore = Google::Cloud::Firestore.new project_id: ENV['GCLOUD_PROJECT_ID']
  
    # Get the references to the old and new data
    old_ref = firebase.get("menus")
    new_ref = firebase.get("archive/menus")
  
    # Get the data from the database for each city, then each RU, and copy all days to the archive
    old_ref.body.each do |city, city_data|
      city_data["rus"].each do |ru, ru_data|
        begin
          ru_data["menus"].each do |date, date_data|
            # Copy the data to the archive on Firebase Realtime Database
            response = firebase.get("menus/#{city}/rus/#{ru}/menus/#{date}")
            firebase.set("archive/menus/#{city}/rus/#{ru}/menus/#{date}", response.body)

            # Copy the data to the archive on Firebase Firestore
            response_body = JSON.parse(response.body)
            map_response_body = {}
            response_body.each do |element|
              map_response_body[element.id] = element
            end
            firestore.doc("menus/#{city}/rus/#{ru}/menus/#{date}").set(map_response_body)

            # Return the response
            puts "[ADDING FOR TODAY] Finished #{ru} for #{date}."
  
            # Add delay to avoid being blocked
            sleep(1)
          end
        rescue NoMethodError => e
          puts "[ADDING FOR TODAY] No menus found for #{ru}. Skipping..."
          next
        end
      end
    end
  
    # Return the response
    puts "[ARCHIVING] Finished moving data."
  end
  
  # Call the function to move the data
  moveData()
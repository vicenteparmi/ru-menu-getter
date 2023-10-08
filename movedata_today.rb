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
            # Define the path in Firebase Realtime Database
            path = "menus/#{city}/rus/#{ru}/menus/#{date}"

            # Get the data from Firebase
            data = response.body

            # Convert inner arrays to strings
            # The data is in the format:
            #   menu = {
            #     0: ['item1', 'item2', 'item3'],
            #     1: ['item1', 'item2', 'item3'],
            #     2: ['item1', 'item2', 'item3'],
            #   }
            #
            # The data should be in the format:
            #   menu = {
            #     'breakfast': 'item1, item2 e item3',
            #     'lubch': 'item1, item2 e item3',
            #     'dinner': 'item1, item2 e item3',
            #   }
            # The last element of each array is joined with an 'e' instead of a comma
            result = {}
            names = ['breakfast', 'lunch', 'dinner']
            data["menu"].each do |key, value|
              # Print state
              puts "[ADDING FOR TODAY] Converting #{ru} for #{date}..."
              puts "[ADDING FOR TODAY] #{key}: #{value}"

              # Check if is the last element
              joiner = key.to_i == data["menu"].length - 1 ? ' e ' : ', '
              result[names[key]] += joiner + value.to_s
            end
            data["menu"] = result

            #Make everything lowercase
            data["menu"].each do |key, value|
              data["menu"][key] = value.downcase
            end

            # Define the path in Firestore
            doc_ref = firestore.doc("menus/#{city}/rus/#{ru}/menus/#{date}")

            # Write the data to Firestore
            doc_ref.set({ 'menus' => data })         

            # Return the response
            puts "[ADDING FOR TODAY] Finished #{ru} for #{date}."
  
            # Add delay to avoid being blocked
            sleep(1)
          end
        rescue NoMethodError => e
          puts "[ADDING FOR TODAY] No menus found for #{ru}. (#{e.message}). Skipping..."
          next
        end
      end
    end
  
    # Return the response
    puts "[ARCHIVING] Finished moving data."
  end
  
  # Call the function to move the data
  moveData()
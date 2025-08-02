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
  
    # Get the references to the archive data
    archive_ref = firebase.get("archive/menus")
  
    # Get the data from the database for each city, then each RU, and copy all days to Firestore
    archive_ref.body.each do |city, city_data|
      city_data["rus"].each do |ru, ru_data|
        begin
          ru_data["menus"].each do |date, date_data|
            # Get the data from archive path for Firestore
            response = firebase.get("archive/menus/#{city}/rus/#{ru}/menus/#{date}")

            # Copy the data to Firebase Firestore
            # Define the path in Firebase Realtime Database
            path = "archive/menus/#{city}/rus/#{ru}/menus/#{date}"

            # Get the data from Firebase
            data = response.body

            # Convert inner arrays to strings
            # The data is in the format:
            #   menu = [
            #     0: ['item1', 'item2', 'item3'],
            #     1: ['item1', 'item2', 'item3'],
            #     2: ['item1', 'item2', 'item3'],
            #   ]
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
            data['menu'].each_with_index do |element, index|
              result[names[index]] = element.join(', ').gsub(/, ([^,]*)$/, ' e \1')
            end
            data['menu'] = result

            # Define the path in Firestore (using standard path structure)
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
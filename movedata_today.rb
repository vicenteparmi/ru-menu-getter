# Initial version: 2023-03-19
# Author: @vicenteparmi

require 'firebase'
require "google/cloud/firestore"

def moveData()
    # Initialize Firebase
    base_uri = ENV['BASE_URL']
    secret = ENV['FIREBASE_KEY']
    firebase = Firebase::Client.new(base_uri, secret)
    firestore = Google::Cloud::Firestore.new(base_uri, secret)
  
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

            # Copy the data to the archive on Firebase Firestore, divided in 'coffee', 'lunch' and 'dinner'
            archive = firestore.collection("archive").doc("menus").collection(city).doc("rus").collection(ru).doc("menus").collection(date)
            archive.doc("coffee").set(response.body[0])
            archive.doc("lunch").set(response.body[1])
            archive.doc("dinner").set(response.body[2])

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
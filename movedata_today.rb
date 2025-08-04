# Initial version: 2023-03-19
# Author: @vicenteparmi

require 'firebase'
require "google/cloud/firestore"

def moveData()
    # Validate environment variables
    required_vars = ['BASE_URL', 'FIREBASE_KEY', 'GCLOUD_PROJECT_ID']
    missing_vars = required_vars.select { |var| ENV[var].nil? || ENV[var].empty? }
    
    unless missing_vars.empty?
      puts "ERROR: Missing required environment variables: #{missing_vars.join(', ')}"
      return false
    end

    begin
      # Initialize Firebase
      base_uri = ENV['BASE_URL']
      secret = ENV['FIREBASE_KEY']
      service_account_json = ENV['GCLOUD_ADMIN']
      firebase = Firebase::Client.new(base_uri, secret)
      firestore = Google::Cloud::Firestore.new project_id: ENV['GCLOUD_PROJECT_ID']
      
      puts "Successfully initialized Firebase and Firestore clients"
    rescue => e
      puts "ERROR: Failed to initialize Firebase/Firestore: #{e.message}"
      return false
    end
  
    begin
      # Get the references to the archive data
      archive_ref = firebase.get("archive/menus")
      # Get the references to the archive data
      archive_ref = firebase.get("archive/menus")
      
      # Validate that we got valid data
      unless archive_ref&.body&.is_a?(Hash)
        puts "ERROR: Invalid or empty archive data received"
        return false
      end
      
      total_processed = 0
      total_errors = 0
    rescue => e
      puts "ERROR: Failed to fetch archive data: #{e.message}"
      return false
    end
  
    # Get the data from the database for each city, then each RU, and copy all days to Firestore
    archive_ref.body.each do |city, city_data|
      next unless city_data.is_a?(Hash) && city_data["rus"].is_a?(Hash)
      
      puts "Processing city: #{city}"
      city_data["rus"].each do |ru, ru_data|
        next unless ru_data.is_a?(Hash) && ru_data["menus"].is_a?(Hash)
        
        puts "  Processing RU: #{ru}"
        begin
          ru_data["menus"].each do |date, date_data|
            begin
              # Get the data from archive path for Firestore
              response = firebase.get("archive/menus/#{city}/rus/#{ru}/menus/#{date}")

              # Validate response
              unless response&.body.is_a?(Hash)
                puts "    WARNING: Invalid data for #{ru} on #{date}. Skipping..."
                next
              end

              # Get the data from Firebase
              data = response.body.dup # Create a copy to avoid modifying original

              # Validate menu data exists and is an array
              unless data['menu'].is_a?(Array)
                puts "    WARNING: No valid menu data for #{ru} on #{date}. Skipping..."
                next
              end

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
              #     'lunch': 'item1, item2 e item3',
              #     'dinner': 'item1, item2 e item3',
              #   }
              # The last element of each array is joined with an 'e' instead of a comma
              result = {}
              names = ['breakfast', 'lunch', 'dinner']
              
              data['menu'].each_with_index do |element, index|
                next unless element.is_a?(Array) && index < names.length
                
                # Filter out nil or empty elements
                clean_elements = element.compact.reject(&:empty?)
                next if clean_elements.empty?
                
                result[names[index]] = clean_elements.join(', ').gsub(/, ([^,]*)$/, ' e \1')
              end
              
              # Only proceed if we have at least one meal
              if result.empty?
                puts "    WARNING: No valid meals found for #{ru} on #{date}. Skipping..."
                next
              end
              
              data['menu'] = result

              # Define the path in Firestore (using standard path structure)
              doc_ref = firestore.doc("menus/#{city}/rus/#{ru}/menus/#{date}")

              # Write the data to Firestore with retry logic
              max_retries = 3
              retries = 0
              
              begin
                doc_ref.set({ 'menus' => data })
                total_processed += 1
                puts "    [SUCCESS] Finished #{ru} for #{date}."
              rescue => firestore_error
                retries += 1
                if retries < max_retries
                  puts "    [RETRY #{retries}] Firestore error for #{ru} on #{date}: #{firestore_error.message}"
                  sleep(2 ** retries) # Exponential backoff
                  retry
                else
                  puts "    [ERROR] Failed to save #{ru} for #{date} after #{max_retries} retries: #{firestore_error.message}"
                  total_errors += 1
                end
              end
  
              # Add delay to avoid being blocked
              sleep(1)
              
            rescue => processing_error
              puts "    [ERROR] Failed to process #{ru} for #{date}: #{processing_error.message}"
              total_errors += 1
              next
            end
          end
        rescue NoMethodError => e
          puts "  [WARNING] No menus found for #{ru}. (#{e.message}). Skipping..."
          next
        rescue => e
          puts "  [ERROR] Failed to process RU #{ru}: #{e.message}"
          total_errors += 1
          next
        end
    end
  
    # Return the response
    puts "[ARCHIVING] Finished moving data. Processed: #{total_processed}, Errors: #{total_errors}"
    return total_errors == 0
end
  
# Call the function to move the data
begin
  success = moveData()
  exit(success ? 0 : 1)
rescue => e
  puts "FATAL ERROR: #{e.message}"
  puts e.backtrace.first(10) if e.backtrace
  exit(1)
end
import json
from collections import Counter
import pyrebase
import os

location_unit_list = [
    ("cwb", "ru-politecnico"),
    ("cwb", "ru-botanico"),
    ("cwb", "ru-central"),
    ("cwb", "ru-agrarias"),
    ("mat", "ru-mat"),
    ("pal", "ru-pal"),
    ("pon", "ru-cem"),
    ("pon", "ru-mir"),
]

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# def complete_list(data):
#     common_meals = []

#     # location > "rus" > unit > "menus" > day > "menu" > item
#     menu_list_coffee = []
#     menu_list_lunch = []
#     menu_list_dinner = []

#     for location, location_data in data.items():
#         for rus, rus_data in location_data.items():
#             for unit, unit_data in rus_data.items():
#                 for menus, menus_data in unit_data.items():
#                     for date, date_data in menus_data.items():
#                         for menu, menu_items in date_data.items():
#                             if menu == "menu":
#                                 for index, menu_item in enumerate(menu_items):
#                                 # Clean up menu item
#                                     replace_list = ["\n", "\t", "\r", "  ", "vegano: ", "saladas: ", "fehado", "sem refeições disponíveis"]
#                                     for i in range(len(menu_item)):
#                                         for replace in replace_list:
#                                             menu_item[i] = menu_item[i].replace(replace, "")

#                                         # Remove spaces at the beginning and end of the string
#                                             menu_item[i] = menu_item[i].strip()

#                                         # Set all to lowercase
#                                             menu_item[i] = menu_item[i].lower()

#                                 # Remove empty items or items with only whitespace
#                                     menu_item = list(filter(None, menu_item))
#                                     menu_item = list(filter(lambda x: x.strip(), menu_item))

#                                 # Add to the correct list
#                                     if index == 0:
#                                         menu_list_coffee.extend(menu_item)
#                                     elif index == 1:
#                                         menu_list_lunch.extend(menu_item)
#                                     elif index == 2:
#                                         menu_list_dinner.extend(menu_item)


#     # Create a list of the most common meals for coffee, lunch, and dinner
#     common_meals_coffee = Counter(menu_list_coffee).most_common(50)
#     common_meals_lunch = Counter(menu_list_lunch).most_common(50)
#     common_meals_dinner = Counter(menu_list_dinner).most_common(50)

#     # Show the most common meals as a table
#     for meal_type, common_meals in [("Coffee", common_meals_coffee), ("Lunch", common_meals_lunch), ("Dinner", common_meals_dinner)]:
#         print(f"\nMost common meals for {meal_type}:")
#         print("{:<30} {:<10}".format('Meal', 'Count'))
#         for meal, count in common_meals:
#             print("{:<30} {:<10}".format(meal, count))


def get_common_items_by_location_and_unit(data):
    common_items = {}

    for location, location_data in data.items():
        common_items[location] = {}

        for rus, rus_data in location_data.items():
            for unit, unit_data in rus_data.items():
                common_items[location][unit] = {"coffee": [], "lunch": [], "dinner": []}

                for menus, menus_data in unit_data.items():
                    for date, date_data in menus_data.items():
                        for menu, menu_items in date_data.items():
                            if menu == "menu":
                                for index, menu_item in enumerate(menu_items):
                                    # Clean up menu item
                                    replace_list = [
                                        "\n",
                                        "\t",
                                        "\r",
                                        "  ",
                                        "vegano: ",
                                        "saladas: ",
                                        "fehado",
                                        "sem refeições disponíveis",
                                    ]
                                    for i in range(len(menu_item)):
                                        for replace in replace_list:
                                            menu_item[i] = menu_item[i].replace(
                                                replace, ""
                                            )

                                            # Remove spaces at the beginning and end of the string
                                            menu_item[i] = menu_item[i].strip()

                                            # Set all to lowercase
                                            menu_item[i] = menu_item[i].lower()

                                    # Remove empty items or items with only whitespace
                                    menu_item = list(filter(None, menu_item))
                                    menu_item = list(
                                        filter(lambda x: x.strip(), menu_item)
                                    )

                                    # Add to the correct list
                                    if index == 0:
                                        common_items[location][unit]["coffee"].extend(
                                            menu_item
                                        )
                                    elif index == 1:
                                        common_items[location][unit]["lunch"].extend(
                                            menu_item
                                        )
                                    elif index == 2:
                                        common_items[location][unit]["dinner"].extend(
                                            menu_item
                                        )

    return common_items


def common_items_filter(data, meal_type, location, unit):
    common_items = get_common_items_by_location_and_unit(data)

    common_items = Counter(common_items[location][unit][meal_type])

    # print(f"\n{location} {unit}")
    # print(f"\nMost common meals for {meal_type}:")
    # print("{:<30} {:<10}".format('Meal', 'Count'))
    # for meal, count in common_items:
    #     print("{:<30} {:<10}".format(meal, count))

    return common_items


def upload_data(content):
    # Initialize Firebase
    config = {
        "apiKey": "AIzaSyB0FHWnqGc3EfBaZy8VYiQO8lf6XiI5PsY",
        "authDomain": "campusdine-menu.firebaseapp.com",
        "databaseURL": "https://campusdine-menu-default-rtdb.firebaseio.com",
        "projectId": "campusdine-menu",
        "storageBucket": "campusdine-menu.appspot.com",
        "messagingSenderId": "1081471577742",
        "appId": "1:1081471577742:web:1ff5a12cdd56696fba63df",
        "measurementId": "G-3MEJC2S8WT",
        "serviceAccount": os.environ["SERVICE_ACCOUNT_CREDENTIALS"],
    }

    firebase = pyrebase.initialize_app(config)

    # Get a reference to the database service
    db = firebase.database()

    # Upload data
    db.child("analysis").set(content)

    # Print result
    print("Data uploaded to Firebase")


def __main__():
    # Get the most common meals for coffee, lunch, and dinner for each location and unit
    # using the filter function and store them in a dictionary
    common_items = {}

    # Divide by location, unit and meal type
    for location, unit in location_unit_list:
        common_items[location] = {}
        common_items[location][unit] = {}
        for meal_type in ["coffee", "lunch", "dinner"]:
            common_items[location][unit][meal_type] = common_items_filter(
                data, meal_type, location, unit
            )

    # Print results as a full table
    print("\n\n")
    print(common_items)


__main__()

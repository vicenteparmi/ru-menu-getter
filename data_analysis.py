import json
import firebase_admin
from firebase_admin import db
from collections import Counter
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

def init_firebase():
    # Initialize Firebase
    cred = firebase_admin.credentials.Certificate(json.loads(os.environ['SERVICE_ACCOUNT_CREDENTIALS']))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://campusdine-menu-default-rtdb.firebaseio.com'
    })

def get_data():
    # Load firebase data
    data = db.reference("archive/menus").get()

    # Convert to JSON
    data = json.loads(json.dumps(data))

    return data

# Initialize Firebase
init_firebase()
data = get_data()

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

    return common_items


def upload_data(content):
    # Upload data
    db.reference("analysis").set(content)

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

    # Upload data
    upload_data(common_items)


__main__()

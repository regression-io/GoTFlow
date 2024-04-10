import json
import os


def read_json_from_file(file_path):
    import json

    # Read the JSON object from the file
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    return json_data

def save_json_objects(json_file_path, output_folder):
    json_list = read_json_from_file(json_file_path)

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through the list of JSON objects
    for i, json_obj in enumerate(json_list, start=1):
        # Define the filename as a combination of a prefix and a unique number
        filename = os.path.join(output_folder, f"action_item_{i}.json")

        # Write the JSON object to a file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=4)


# Assuming the function is called with a valid JSON list and an output folder
# Note: In this environment, files will be saved to a temporary location
json_file_path = "D:\\source\\github\\GoTFlow\\data\\workflows\\Contracts\\input\\action_items.json"
output_folder = "D:\\source\\github\\GoTFlow\\data\\workflows\\Contracts\\input\\parameters"
save_json_objects(json_file_path, output_folder)

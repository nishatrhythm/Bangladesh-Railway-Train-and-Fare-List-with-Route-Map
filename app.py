from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json, os, re, ujson


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key for production
app.config['SESSION_TYPE'] = 'filesystem'

# Load stations from the JSON file
with open('stations_en.json', 'r', encoding='utf-8') as file:
    stations_data = json.load(file)
stations_list = stations_data['stations']

# Directory containing processed JSON files
processed_directory = 'processed_stations'
processed_train_directory = 'processed_trains'

# Define the order for seat types
seat_order = [
    "AC_B", "AC_S", "SNIGDHA", "F_BERTH", "F_SEAT", "F_CHAIR",
    "S_CHAIR", "SHOVAN", "SHULOV", "AC_CHAIR"
]

def load_json_file(file_path):
    with open(file_path, 'rb') as file:
        return ujson.loads(file.read())

# Global variable to cache train data
train_data_cache = []

# Preload train data from the processed_train_directory into memory
def preload_train_data(directory):
    global train_data_cache
    if not train_data_cache:  # Load data only if it's not already in memory
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                file_path = os.path.join(directory, filename)
                train_data = load_json_file(file_path)  # Use the new function
                train_data_cache.append(train_data)

# Call this function when the app starts to preload the data
preload_train_data(processed_train_directory)

# Function to format time by removing leading zeros
def format_time(time_str):
    if time_str == 'N/A':
        return time_str
    return re.sub(r'\b0(\d):', r'\1:', time_str)

# Function to create an index of JSON files by origin and destination
def create_index(directory):
    index = {}
    for entry in os.scandir(directory):
        if entry.is_file() and entry.name.endswith('.json'):
            file_path = entry.path
            data = load_json_file(file_path)  # Use the new function
            if 'origin_city_name' in data and 'destination_city_name' in data:
                key = (data['origin_city_name'].lower(), data['destination_city_name'].lower())
                index[key] = file_path
    return index

# Create index at the start for quick lookup
index = create_index(processed_directory)

# Function to find the off days from the given days of operation
def get_off_days(days):
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    full_days_short_map = {
        "Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday",
        "Sun": "Sunday"
    }
    
    # Convert short day codes to full day names
    operating_days_full = [full_days_short_map[day] for day in days]

    # Get the off days by finding the difference
    off_days = [day for day in all_days if day not in operating_days_full]

    if len(off_days) == 0:
        return "Runs everyday"
    return ', '.join(off_days)

# Function to find trains that run between the selected origin and destination
def find_trains_between_stations(origin, destination):
    matching_trains = []
    for train_data in train_data_cache:  # Use cached train data
        routes = train_data['data']['routes']
        departure_time = None
        arrival_time = None
        origin_found = False

        for route in routes:
            # Set the departure time at the origin station
            if route['city'].lower() == origin.lower() and not origin_found:
                # Handle IST and BST in time strings
                departure_time_raw = (route.get('departure_time') or 'N/A').replace(' BST', '')
                departure_time = format_time(departure_time_raw.replace(' IST', ''))
                if 'IST' in departure_time_raw:
                    departure_time += ' IST'  # Retain 'IST' for display

                origin_found = True

            # Set the arrival time at the destination station
            if origin_found and route['city'].lower() == destination.lower():
                arrival_time_raw = (route.get('arrival_time') or 'N/A').replace(' BST', '')
                arrival_time = format_time(arrival_time_raw.replace(' IST', ''))
                if 'IST' in arrival_time_raw:
                    arrival_time += ' IST'  # Retain 'IST' for display

                off_days = get_off_days(train_data['data']['days'])
                matching_trains.append({
                    'train_name': train_data['data']['train_name'],
                    'off_days': off_days,
                    'departure_time': departure_time,
                    'arrival_time': arrival_time
                })
                break  # Stop once the destination is found

    # Sort the list by formatted departure time (ignoring 'N/A' times)
    matching_trains.sort(key=lambda x: datetime.strptime(x['departure_time'].replace(' IST', ''), '%I:%M %p') if x['departure_time'] != 'N/A' else datetime.max)

    return matching_trains

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' https://raw.githubusercontent.com/nishatrhythm/Bangladesh-Railway-Train-and-Fare-List/main/images/bangladesh-railway.png;"
        "img-src 'self' https://raw.githubusercontent.com/nishatrhythm/Bangladesh-Railway-Train-and-Fare-List/main/images/link_share_image.png;"
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://kit.fontawesome.com; "
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'  # Enforces HTTPS
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Set a flag to indicate that a search has been performed
        session['search_performed'] = True

        # Preserve the original input casing
        origin = request.form['origin'].strip()
        destination = request.form['destination'].strip()

        # Convert to lowercase for searching in the index
        origin_lower = origin.lower()
        destination_lower = destination.lower()

        # Check if origin and destination are the same
        if origin_lower == destination_lower:
            session['error'] = "Origin and destination stations cannot be the same."
            session['selected_origin'] = origin  # Keep original casing
            session['selected_destination'] = destination  # Keep original casing
            session.modified = True  # Ensure session data persists
            return redirect(url_for('home'))

        # Proceed with the search if origin and destination are different
        search_key = (origin_lower, destination_lower)

        fare_data_found = search_key in index
        if fare_data_found:
            file_path = index[search_key]
            data = load_json_file(file_path)  # Use the new function

            # Sort the 'info' array based on the predefined seat order
            data['info'].sort(key=lambda x: seat_order.index(x['type']) if x['type'] in seat_order else len(seat_order))

            session['results'] = {
                'data': data,
                'origin': origin,  # Keep original casing for display
                'destination': destination  # Keep original casing for display
            }

        # Find matching trains regardless of fare data presence
        matching_trains = find_trains_between_stations(origin, destination)
        if matching_trains:
            session['trains'] = matching_trains
            session['selected_origin'] = origin  # Keep original casing
            session['selected_destination'] = destination  # Keep original casing
            session.modified = True  # Ensure session data persists

        # If train data exists but fare data does not, set a specific message
        if not fare_data_found and matching_trains:
            session['fare_error'] = "The fare list between these two stations is unavailable, as trains do pass through this route but may not offer seat reservations, or they might be temporarily out of service."
            session['results'] = None  # Ensure no fare data is shown, only train data
            session['selected_origin'] = origin  # Keep original casing
            session['selected_destination'] = destination  # Keep original casing
            session.modified = True  # Ensure session data persists
        elif not fare_data_found and not matching_trains:
            # General error when neither fare data nor train data is available
            session['error'] = "No data found for the selected route."
            session['selected_origin'] = origin  # Keep original casing
            session['selected_destination'] = destination  # Keep original casing
            session.modified = True  # Ensure session data persists

        # Redirect to the home route to avoid form resubmission
        return redirect(url_for('home'))

    # Handle GET request: retrieve results and selected values from session if available
    results = session.pop('results', None)
    error = session.pop('error', False)
    fare_error = session.pop('fare_error', None)  # Retrieve fare-specific error message
    search_performed = session.pop('search_performed', False)

    # Retrieve selected origin and destination if a search was performed, else reset
    selected_origin = session.get('selected_origin') if search_performed else None
    selected_destination = session.get('selected_destination') if search_performed else None
    trains = session.pop('trains', None)

    return render_template('index.html', stations=stations_list, results=results, error=error, fare_error=fare_error, selected_origin=selected_origin, selected_destination=selected_destination, trains=trains, search_performed=search_performed)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
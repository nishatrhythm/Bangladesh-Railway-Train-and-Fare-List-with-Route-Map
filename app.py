from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json, os, re, ujson


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'

geojson_directory = 'static/geojson'

with open('stations_en.json', 'r', encoding='utf-8') as file:
    stations_data = json.load(file)
stations_list = stations_data['stations']

processed_directory = 'processed_stations'
processed_train_directory = 'processed_trains'

seat_order = [
    "AC_B", "AC_S", "SNIGDHA", "F_BERTH", "F_SEAT", "F_CHAIR",
    "S_CHAIR", "SHOVAN", "SHULOV", "AC_CHAIR"
]

def find_geojson_file(origin, destination):
    for filename in os.listdir(geojson_directory):
        if filename.endswith('.geojson'):
            file_path = os.path.join(geojson_directory, filename)
            with open(file_path, 'r', encoding='utf-8') as geojson_file:
                geojson_data = json.load(geojson_file)
                if (geojson_data.get("origin_city_name") == origin.lower() and
                        geojson_data.get("destination_city_name") == destination.lower()):
                    return filename
    return None

def load_json_file(file_path):
    with open(file_path, 'rb') as file:
        return ujson.loads(file.read())

train_data_cache = []

def preload_train_data(directory):
    global train_data_cache
    if not train_data_cache:
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                file_path = os.path.join(directory, filename)
                train_data = load_json_file(file_path)
                train_data_cache.append(train_data)

preload_train_data(processed_train_directory)

def format_time(time_str):
    if time_str == 'N/A':
        return time_str
    return re.sub(r'\b0(\d):', r'\1:', time_str)

def create_index(directory):
    index = {}
    for entry in os.scandir(directory):
        if entry.is_file() and entry.name.endswith('.json'):
            file_path = entry.path
            data = load_json_file(file_path)
            if 'origin_city_name' in data and 'destination_city_name' in data:
                key = (data['origin_city_name'].lower(), data['destination_city_name'].lower())
                index[key] = file_path
    return index

index = create_index(processed_directory)

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
    
    operating_days_full = [full_days_short_map[day] for day in days]

    off_days = [day for day in all_days if day not in operating_days_full]

    if len(off_days) == 0:
        return "Runs everyday"
    return ', '.join(off_days)

def find_trains_between_stations(origin, destination):
    matching_trains = []
    for train_data in train_data_cache:
        routes = train_data['data']['routes']
        departure_time = None
        arrival_time = None
        origin_found = False

        for route in routes:
            if route['city'].lower() == origin.lower() and not origin_found:
                departure_time_raw = (route.get('departure_time') or 'N/A').replace(' BST', '')
                departure_time = format_time(departure_time_raw.replace(' IST', ''))
                if 'IST' in departure_time_raw:
                    departure_time += ' IST'

                origin_found = True

            if origin_found and route['city'].lower() == destination.lower():
                arrival_time_raw = (route.get('arrival_time') or 'N/A').replace(' BST', '')
                arrival_time = format_time(arrival_time_raw.replace(' IST', ''))
                if 'IST' in arrival_time_raw:
                    arrival_time += ' IST'

                off_days = get_off_days(train_data['data']['days'])
                matching_trains.append({
                    'train_name': train_data['data']['train_name'],
                    'off_days': off_days,
                    'departure_time': departure_time,
                    'arrival_time': arrival_time
                })
                break

    matching_trains.sort(key=lambda x: datetime.strptime(x['departure_time'].replace(' IST', ''), '%I:%M %p') if x['departure_time'] != 'N/A' else datetime.max)

    return matching_trains

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' https://raw.githubusercontent.com/nishatrhythm/Bangladesh-Railway-Train-and-Fare-List-with-Route-Map/main/images/bangladesh-railway.png "
        "https://raw.githubusercontent.com/nishatrhythm/Bangladesh-Railway-Train-and-Fare-List-with-Route-Map/main/images/link_share_image.png "
        "https://a.tile.openstreetmap.org https://b.tile.openstreetmap.org https://c.tile.openstreetmap.org; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://unpkg.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://kit.fontawesome.com https://unpkg.com; "
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.route('/', methods=['GET', 'POST'])
def home():
    geojson_filename = None
    
    if request.method == 'POST':
        session['search_performed'] = True

        origin = request.form['origin'].strip()
        destination = request.form['destination'].strip()

        origin_lower = origin.lower()
        destination_lower = destination.lower()

        if origin_lower == destination_lower:
            session['error'] = "Origin and destination stations cannot be the same."
            session['selected_origin'] = origin
            session['selected_destination'] = destination
            session.modified = True
            return redirect(url_for('home'))
        
        geojson_filename = find_geojson_file(origin_lower, destination_lower)
        if not geojson_filename:
            geojson_filename = find_geojson_file(destination_lower, origin_lower)
        if geojson_filename:
            session['geojson_filename'] = geojson_filename

        search_key = (origin_lower, destination_lower)
        reverse_key = (destination_lower, origin_lower)

        fare_data_found = search_key in index or reverse_key in index
        if fare_data_found:
            file_path = index.get(search_key) or index.get(reverse_key)
            data = load_json_file(file_path)

            data['info'].sort(key=lambda x: seat_order.index(x['type']) if x['type'] in seat_order else len(seat_order))

            session['results'] = {
                'data': data,
                'origin': origin,
                'destination': destination
            }

        matching_trains = find_trains_between_stations(origin, destination)
        if matching_trains:
            session['trains'] = matching_trains
            session['selected_origin'] = origin
            session['selected_destination'] = destination
            session.modified = True

        if not fare_data_found and matching_trains:
            session['fare_error'] = "The fare list between these two stations is unavailable, as trains do pass through this route but may not offer seat reservations, or they might be temporarily out of service."
            session['results'] = None
            session['selected_origin'] = origin
            session['selected_destination'] = destination
            session.modified = True
        elif not fare_data_found and not matching_trains:
            session['error'] = "No data found for the selected route."
            session['selected_origin'] = origin
            session['selected_destination'] = destination
            session.modified = True

        return redirect(url_for('home'))

    results = session.pop('results', None)
    error = session.pop('error', False)
    fare_error = session.pop('fare_error', None)
    search_performed = session.pop('search_performed', False)

    selected_origin = session.get('selected_origin') if search_performed else None
    selected_destination = session.get('selected_destination') if search_performed else None
    trains = session.pop('trains', None)
    geojson_filename = session.pop('geojson_filename', None)

    return render_template('index.html', stations=stations_list, results=results, error=error, fare_error=fare_error, selected_origin=selected_origin, selected_destination=selected_destination, trains=trains, search_performed=search_performed, geojson_filename=geojson_filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5002)))
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong secret key for production
app.config['SESSION_TYPE'] = 'filesystem'

# Load stations from the JSON file
with open('stations_en.json', 'r', encoding='utf-8') as file:
    stations_data = json.load(file)
stations_list = stations_data['stations']

# Directory containing processed JSON files
processed_directory = 'processed'

# Define the order for seat types
seat_order = [
    "AC_B", "AC_S", "SNIGDHA", "F_BERTH", "F_SEAT", "F_CHAIR",
    "S_CHAIR", "SHOVAN", "SHULOV", "AC_CHAIR"
]

# Function to create an index of JSON files by origin and destination
def create_index(directory):
    index = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if 'origin_city_name' in data and 'destination_city_name' in data:
                    key = (data['origin_city_name'].lower(), data['destination_city_name'].lower())
                    index[key] = file_path
    return index

# Create index at the start for quick lookup
index = create_index(processed_directory)

@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' https://eticket.railway.gov.bd; "
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
            return redirect(url_for('home'))

        # Proceed with the search if origin and destination are different
        search_key = (origin_lower, destination_lower)
        if search_key in index:
            file_path = index[search_key]
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

                # Sort the 'info' array based on the predefined seat order
                data['info'].sort(key=lambda x: seat_order.index(x['type']) if x['type'] in seat_order else len(seat_order))

                session['results'] = {
                    'data': data,
                    'origin': origin,  # Keep original casing for display
                    'destination': destination  # Keep original casing for display
                }
                session['selected_origin'] = origin  # Keep original casing
                session['selected_destination'] = destination  # Keep original casing
        else:
            session['error'] = "No data found for the selected route or the stations may not have a central server connection for online ticket management."
            session['selected_origin'] = origin  # Keep original casing
            session['selected_destination'] = destination  # Keep original casing

        # Redirect to the home route to avoid form resubmission
        return redirect(url_for('home'))

    # Handle GET request: retrieve results and selected values from session if available
    results = session.pop('results', None)
    error = session.pop('error', False)
    selected_origin = session.pop('selected_origin', None)
    selected_destination = session.pop('selected_destination', None)

    return render_template('index.html', stations=stations_list, results=results, error=error, selected_origin=selected_origin, selected_destination=selected_destination)

if __name__ == "__main__":
    # Ensure the app runs in production mode without debug
    app.run(host='0.0.0.0', port=5000, debug=False)
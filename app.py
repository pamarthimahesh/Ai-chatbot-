from flask import Flask, render_template, request
import requests
import os

# Create a Flask application instance
app = Flask(__name__)

# --- In-Memory "Cache" ---
# In a real-world scenario, you might use a more robust caching system
# like Redis or Memcached to avoid repeatedly calling the API for the same IP.
# For this example, a simple dictionary will suffice.
IP_CACHE = {}

def get_ip_address():
    """
    Gets the public IP address of the user.
    It checks for the 'X-Forwarded-For' header (common for proxies)
    and falls back to the remote address.
    """
    # If the app is behind a proxy, the real IP will be in this header.
    if request.headers.getlist("X-Forwarded-For"):
        ip_address = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        # Otherwise, use the direct remote address.
        ip_address = request.remote_addr
        
    # Handle the case where the app is running locally (127.0.0.1)
    # by fetching the public IP from an external service.
    if ip_address == '127.0.0.1':
        try:
            response = requests.get('https://api64.ipify.org?format=json')
            response.raise_for_status() # Raise an exception for bad status codes
            ip_address = response.json()['ip']
        except requests.exceptions.RequestException as e:
            print(f"Could not fetch public IP: {e}")
            return "Unable to fetch public IP"
            
    return ip_address


def get_geolocation_data(ip_address):
    """
    Fetches geolocation data for a given IP address from the ip-api.com service.
    Includes basic error handling and uses the in-memory cache.
    """
    # Check if the data is already in our cache
    if ip_address in IP_CACHE:
        return IP_CACHE[ip_address]
        
    # If not in cache, call the API
    # Using http since we don't need an API key for this service
    api_url = f"http://ip-api.com/json/{ip_address}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        
        # If the API call is successful, store the result in the cache
        if data.get('status') == 'success':
            IP_CACHE[ip_address] = data
            return data
        else:
            # The API returned a "fail" status (e.g., for a private IP)
            return {"error": True, "message": data.get('message', 'Failed to get geolocation data.')}
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return {"error": True, "message": "Service unavailable or invalid IP."}
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
        return {"error": True, "message": "Network error while fetching geolocation data."}
    except ValueError: # Catches JSON decoding errors
        return {"error": True, "message": "Error processing geolocation data."}


@app.route('/')
def index():
    """
    The main route for the web application.
    It gets the IP, fetches geolocation, and renders the HTML template.
    """
    user_ip = get_ip_address()
    
    # Handle case where IP could not be determined
    if "Unable" in user_ip:
        location_data = {"error": True, "message": "Could not determine your IP address."}
    else:
        location_data = get_geolocation_data(user_ip)

    # Render the 'index.html' template, passing the IP and location data to it.
    return render_template('index.html', ip_address=user_ip, location=location_data)

# --- Template File Setup ---
# This part of the script will dynamically create the necessary HTML and CSS files
# if they don't already exist. This makes the Flask app self-contained and
# easier to run without manual setup.

def create_template_files():
    """Creates the templates and static folders and the necessary files."""
    # Create 'templates' and 'static' directories if they don't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    # HTML content for the index.html file
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IP Address & Geolocation</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">
    <div class="container bg-gray-800 p-8 rounded-2xl shadow-2xl w-full max-w-2xl text-center border border-gray-700">
        <h1 class="text-4xl font-bold mb-4 text-cyan-400">Your IP & Geolocation</h1>
        <p class="text-lg mb-8 text-gray-400">Details about your current internet connection.</p>
        
        <div class="info-card bg-gray-700 p-6 rounded-lg shadow-inner">
            <h2 class="text-2xl font-semibold mb-4 text-white">IP Address</h2>
            <p class="text-3xl font-mono bg-gray-900 py-2 px-4 rounded-md inline-block text-green-400">{{ ip_address }}</p>
        </div>

        {% if location and not location.error %}
            <div class="location-grid mt-8">
                <h2 class="text-2xl font-semibold mb-4 text-white col-span-2">Geolocation Details</h2>
                <div class="grid-item"><span class="font-bold text-cyan-400">Country:</span> {{ location.country }}</div>
                <div class="grid-item"><span class="font-bold text-cyan-400">Region:</span> {{ location.regionName }}</div>
                <div class="grid-item"><span class="font-bold text-cyan-400">City:</span> {{ location.city }}</div>
                <div class="grid-item"><span class="font-bold text-cyan-400">ZIP Code:</span> {{ location.zip }}</div>
                <div class="grid-item"><span class="font-bold text-cyan-400">Latitude:</span> {{ location.lat }}</div>
                <div class="grid-item"><span class="font-bold text-cyan-400">Longitude:</span> {{ location.lon }}</div>
                <div class="grid-item col-span-2"><span class="font-bold text-cyan-400">ISP:</span> {{ location.isp }}</div>
            </div>
        {% elif location.error %}
             <div class="info-card bg-red-900 bg-opacity-50 p-6 rounded-lg shadow-inner mt-8 border border-red-700">
                <h2 class="text-2xl font-semibold mb-4 text-red-400">Error</h2>
                <p class="text-xl text-red-300">{{ location.message }}</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

    # CSS content for the style.css file
    css_content = """
@import url('https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css');

body {
    font-family: 'Inter', sans-serif;
}

.container {
    animation: fadeIn 1s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

.info-card, .location-grid {
    animation: slideIn 1s ease-in-out forwards;
    opacity: 0;
    animation-delay: 0.5s;
}

@keyframes slideIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.location-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    text-align: left;
    margin-top: 2rem;
}

.grid-item {
    background-color: #4a5568; /* gray-700 */
    padding: 1rem;
    border-radius: 0.5rem;
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

.grid-item:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
}

.col-span-2 {
    grid-column: span 2 / span 2;
}

/* Responsive design for smaller screens */
@media (max-width: 640px) {
    .location-grid {
        grid-template-columns: 1fr;
    }
    .col-span-2 {
        grid-column: span 1 / span 1;
    }
     h1 {
        font-size: 2.5rem;
    }
}
"""
    # Write the content to the files
    with open('templates/index.html', 'w') as f:
        f.write(html_content)
    with open('static/style.css', 'w') as f:
        f.write(css_content)

# The entry point of the script
if __name__ == '__main__':
    # Create the necessary files before starting the app
    create_template_files()
    # Run the Flask app in debug mode
    app.run(debug=True)

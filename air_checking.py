import requests
import gradio as gr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from PIL import Image  # Import PIL for image handling

# Set your OpenWeatherMap API key and base URL
API_KEY = 'bfd62a913eee6486de309fef3a34a725'
BASE_URL = 'http://api.openweathermap.org/data/2.5/air_pollution?'

def get_coordinates(city):
    """Fetch coordinates for the specified city."""
    geocode_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    response = requests.get(geocode_url)
    if response.status_code != 200:
        return f"Error fetching data for city '{city}': {response.json().get('message', 'Unknown error')}"
    data = response.json()
    return data['coord']['lat'], data['coord']['lon']

def get_air_quality(lat, lon):
    """Fetch air quality data using latitude and longitude."""
    air_quality_url = f"{BASE_URL}lat={lat}&lon={lon}&appid={API_KEY}"
    response = requests.get(air_quality_url)
    if response.status_code != 200:
        return "Error fetching air quality data: " + response.json().get('message', 'Unknown error')
    return response.json()

def assess_air_quality(aqi):
    """Determine AQI category."""
    categories = ["Good (0-50)", "Fair (51-100)", "Moderate (101-150)", "Poor (151-200)", "Very Poor (201+)"]
    return categories[aqi - 1] if 1 <= aqi <= 5 else "Unknown"

def send_email_notification(email, message):
    """Send an email notification to the user."""
    sender_email = "your_email@gmail.com"  # Replace with your email
    sender_password = "your_app_password"    # Use your app password or regular password if allowed
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Air Quality Alert"
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        print(f"Notification sent to {email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def plot_pollutants(pollutants):
    """Create a bar chart of pollutant concentrations."""
    names = list(pollutants.keys())
    values = list(pollutants.values())
    
    fig, ax = plt.subplots()
    ax.barh(names, values, color='skyblue')
    ax.set_xlabel('Concentration (µg/m³)')
    ax.set_title('Pollutant Concentrations')

    # Save the figure to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)  # Close the figure to free memory

    # Convert BytesIO to a PIL Image
    image = Image.open(buf)
    return image

def plot_aqi_gauge(aqi):
    """Create a meter board-style gauge for AQI."""
    fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(polar=True))
    
    # Define angle for the gauge
    theta = np.linspace(0, np.pi, 100)

    # Define the gauge's colors based on AQI level
    if aqi == 1:  # Good
        color = 'green'
    elif aqi == 2:  # Fair
        color = 'yellow'
    elif aqi == 3:  # Moderate
        color = 'orange'
    elif aqi == 4:  # Poor
        color = 'red'
    else:  # Very Poor
        color = 'darkred'
    
    # Create the background of the gauge
    ax.fill(theta, np.ones_like(theta), color='lightgrey', alpha=0.5)
    
    # Draw the actual gauge
    ax.fill(theta, np.minimum(aqi/5 * np.ones_like(theta), 1), color=color, alpha=0.6)

    # Set the ticks
    ticks = ['0', '50', '100', '150', '200', '300']
    ax.set_xticks(np.linspace(0, np.pi, len(ticks)))
    ax.set_xticklabels(ticks)

    # Set the radius limit
    ax.set_ylim(0, 1)

    # Add a label at the center
    ax.text(0, 0.5, f'AQI: {aqi}', horizontalalignment='center', verticalalignment='center', fontsize=20)

    # Save the figure to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)  # Close the figure to free memory

    # Convert BytesIO to a PIL Image
    image = Image.open(buf)
    return image

def display_air_quality(city=None, lat=None, lon=None, email=None):
    """Main function to display air quality and send notifications."""
    if city:
        coordinates = get_coordinates(city)
        if isinstance(coordinates, str):
            return coordinates, None, None
        lat, lon = coordinates
    elif lat is None or lon is None:
        return "Please provide a city or coordinates.", None, None
    
    air_quality_data = get_air_quality(lat, lon)
    if isinstance(air_quality_data, str):
        return air_quality_data, None, None

    aqi = air_quality_data['list'][0]['main']['aqi']
    pollutants = air_quality_data['list'][0]['components']
    aqi_category = assess_air_quality(aqi)
    
    output = f"Air Quality Index (AQI): {aqi} ({aqi_category})\n"
    output += "Pollutant concentrations (µg/m³):\n"
    
    for pollutant, value in pollutants.items():
        output += f"{pollutant}: {value}\n"

    if aqi >= 3:  # AQI 3 and above considered moderate to hazardous
        warning_message = "\nWarning: The air quality is considered bad.\nRecommended actions:\n"
        warning_message += "- Limit outdoor activities.\n"
        warning_message += "- Use air purifiers indoors.\n"
        warning_message += "- Wear masks if going outside.\n"
        warning_message += "- Keep windows closed."
        output += warning_message

        if email:
            send_email_notification(email, f"The air quality is currently bad with an AQI of {aqi}.\n" + warning_message)
            output += f"\nNotification sent to {email}."
    else:
        output += "\nThe air quality is good. Keep the environment the same to maintain it!"
    
    # Plot pollutants and return the images
    pollutant_image = plot_pollutants(pollutants)
    aqi_image = plot_aqi_gauge(aqi)
    return output, pollutant_image, aqi_image

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("## Air Quality Checker with Notifications")
    city_input = gr.Textbox(label="City (optional)")
    lat_input = gr.Textbox(label="Latitude", interactive=False)
    lon_input = gr.Textbox(label="Longitude", interactive=False)
    email_input = gr.Textbox(label="Email for Notifications (optional)")
    output = gr.Textbox(label="Air Quality Info", interactive=False)
    pollutant_plot = gr.Image(label="Pollutant Concentrations", type="pil")
    aqi_plot = gr.Image(label="AQI Status", type="pil")

    gr.HTML("""
    <button onclick="navigator.geolocation.getCurrentPosition(
        (position) => {
            document.getElementById('lat').value = position.coords.latitude.toFixed(5);
            document.getElementById('lon').value = position.coords.longitude.toFixed(5);
        },
        (error) => { alert('Error fetching location: ' + error.message); }
    );">Use My Location</button>
    <script>
        document.querySelector('button').addEventListener('click', () => {
            const latField = document.querySelector('input[placeholder="Latitude"]');
            latField.setAttribute('id', 'lat');
            const lonField = document.querySelector('input[placeholder="Longitude"]');
            lonField.setAttribute('id', 'lon');
        });
    </script>
    """)

    submit_button = gr.Button("Check Air Quality")

    def check_air_quality(city, lat, lon, email):
        return display_air_quality(city=city, lat=lat, lon=lon, email=email)

    submit_button.click(
        check_air_quality, 
        inputs=[city_input, lat_input, lon_input, email_input], 
        outputs=[output, pollutant_plot, aqi_plot]
    )

# Launch the Gradio app
demo.launch()

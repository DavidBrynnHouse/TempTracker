import requests
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import os
import matplotlib.dates as mdates
from dotenv import load_dotenv
from flask import Flask, render_template, request
import pandas

load_dotenv()

class SensorData:
    def __init__(self, api_key, api_secret, url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = url

    def get_sensor_data(self, start_date, end_date, sensor_id):
        headers = {
            "APIKeyID": self.api_key,
            "APISecretKey": self.api_secret
        }
        
        num_calls = 5
        
        delta = (end_date - start_date) / num_calls

        # Make the API calls and combine the data into a single dictionary
        data = {}
        i = 0
        for j in range(num_calls):
            call_start = start_date + j * delta
            call_end = call_start + delta
            call_from_date = call_start.strftime("%Y-%m-%d %H:%M:%S")
            call_to_date = call_end.strftime("%Y-%m-%d %H:%M:%S")

            params = {
                "sensorID": sensor_id,
                "fromDate": call_from_date,
                "toDate": call_to_date
            }
            
            try:
                response = requests.post(self.url, headers=headers, data=params)
                response_dict = response.json()
            except requests.exceptions.RequestException as e:
                print(f"An error occurred while making the API call: {e}")
                return {}
            if "Result" not in response_dict:
                print(f"Unexpected response format: {response_dict}")
                return {}
            for item in response_dict['Result']:
                try:
                    timestamp = int(item['Date'][6:-2]) / 1000  # Extract timestamp value and convert to seconds
                    date = datetime.fromtimestamp(timestamp)

                    # format the datetime object as a string in the desired format
                    formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")

                    data[i] = {formatted_date: item['Value']}
                    i += 1
                except Exception as e:
                    print(f"Error processing response item: {e}")

        return data


class ChartGenerator:
    def __init__(self):
        pass

    def generate_chart(self, x_data, y_data, start_date, end_date):
        fig, ax = plt.subplots()
        fig.subplots_adjust(bottom=0.33)
    
        # Convert x_data to datetime objects
        x_data = [datetime.strptime(date, "%Y-%m-%d %H:%M:%S") for date in x_data]

        # Plot the data
        ax.plot(x_data, y_data)

        # Set the x-axis limits to the given start and end dates
        ax.set_xlim(start_date, end_date)

        # Set the x-axis tick formatter to display dates in the desired format
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
        
        ax.tick_params(axis='x', labelrotation=45)
        
        ax.set_title("Temperatures Over Time")
        ax.set_xlabel("Date and Time")
        ax.set_ylabel("Temperature (F)")

        # Encode the chart image as base64 and embed it in the HTML response
        chart = io.BytesIO()
        fig.tight_layout()
        fig.savefig(chart, format='png')
        chart.seek(0)
        chart_b64 = base64.b64encode(chart.getvalue()).decode('utf-8')
        chart_html = '<img src="data:image/png;base64,{}">'.format(chart_b64)

        return chart_html
            

app = Flask(__name__, static_folder='static')
api_key = os.environ.get('API_KEY')
api_secret = os.environ.get('API_SECRET')
url = "https://www.imonnit.com/json/SensorChartMessages"

sensor_data = SensorData(api_key, api_secret, url)
chart_generator = ChartGenerator()



@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        sensor_id = request.form['sensor']

        # Calculate the time range for each API call
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d")
        
        data = sensor_data.get_sensor_data(start_date, end_date, sensor_id)

        x_data = []
        y_data = []

        for x in data:
            if len(data[x]) > 0: 
                date = list(data[x].keys())[0]
                x_data.append(date)
                y_data.append(data[x].get(date))
        
        x_data, y_data = zip(*sorted(zip(x_data, y_data)))
        chart_html = chart_generator.generate_chart(x_data, y_data, start_date, end_date)

        # Render the HTML template with the chart image embedded
        return render_template('index.html', chart_html=chart_html)

    # Render the initial HTML template with no chart image
    return render_template('index.html', chart_html='')

@app.route('/select_date')
def select_date():
    return render_template('select_date.html')

if __name__ == '__main__':
    app.run()

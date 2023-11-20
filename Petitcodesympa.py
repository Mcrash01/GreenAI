import requests
import json
import pandas as pd
data = requests.get("https://data.ffvl.fr/api/?base=terrains&mode=json&key=00000000000000000000000000000000").text
weather_data = json.loads(data)
global villedata
geo_data = pd.read_csv("data/cities.csv")
print(geo_data)
def get_department_region(city_name, geo_data):
    # Normalize the city names to lowercase for matching
    geo_data['label'] = geo_data['label'].str.lower()
    city_name = city_name.lower()
    
    # Find the row where the city name matches
    matching_row = geo_data[geo_data['label'] == city_name]
    
    # If there's a match, return the department and region
    if not matching_row.empty:
        return {
            'department_name': matching_row.iloc[0]['department_name'],
            'department_number': matching_row.iloc[0]['department_number'],
            'region_name': matching_row.iloc[0]['region_name']
        }
    else:
        # If there's no match, return None or an empty dictionary
        return None
SOLAR_LATITUDE_THRESHOLD = 45.0  # Arbitrary value for illustration
WIND_SPEED_THRESHOLD = 5  # Assuming wind orientations contain a numeric speed indicator, this is arbitrary



def score_for_wind_energy(weather):
    # Assume that more wind orientations and higher altitude are better for wind energy
    wind_score = 0
    wind_ok = weather.get('wind_orientations_ok')
    if wind_ok:
        wind_conditions = wind_ok.split(';')[:-1]  # Remove the empty string due to trailing ;
        wind_score = len(wind_conditions)  # More orientations mean better wind potential
    altitude = int(weather.get('altitude', 0))
    wind_score += altitude / 100  # Higher altitude might be better for wind energy
    return wind_score

def score_for_solar_energy(weather):
    # Assume regions with lower latitudes have better solar potential due to higher solar irradiance.
    latitude = float(weather.get('latitude', 0))
    
    # A simple linear scoring based on latitude, where the score decreases as latitude increases.
    # For example, we can assume the maximum score for latitude 0 and decrease linearly until the SOLAR_LATITUDE_THRESHOLD.
    max_solar_score = 10  # Maximum score at the equator (latitude 0)
    score_per_degree = max_solar_score / SOLAR_LATITUDE_THRESHOLD  # Score decrease per degree of latitude
    
    # Calculate the solar score based on latitude, with higher latitudes receiving lower scores.
    solar_score = max(0, max_solar_score - (latitude * score_per_degree))
    
    return solar_score


# Apply the scoring functions to each region and create a list of dictionaries for DataFrame
energy_data_list = []
for region in weather_data:
    # Get department and region info
    dept_region_info = get_department_region(region['city'], geo_data)
    
    # Update region with department and region info
    region.update(dept_region_info if dept_region_info else {'department_name': "", 'department_number': "", 'region_name': ""})
    
    # Calculate energy scores
    region['wind_energy_score'] = score_for_wind_energy(region)
    region['solar_energy_score'] = score_for_solar_energy(region)
    
    # Determine best green energy
    region['best_green_energy'] = 'wind' if region['wind_energy_score'] > (region['solar_energy_score'] * 100) else 'solar'
    
    # Append the data to the list
    energy_data_list.append(region)

# Create a DataFrame and remove duplicates
energy_scores_df = pd.DataFrame(energy_data_list).drop_duplicates(subset=['city'])

# Display the DataFrame (optional)
print(energy_scores_df)
energy_scores_df.to_excel("results/Test.xlsx")


import csv
import random
import math

# Base coordinates for the centers of the requested cities, plus land-angle constraints to avoid the sea
# Standard angles: 0=E, 90=N, 180=W, -90/270=S
CITIES = {
    "Casablanca": {"lat": 33.5731, "lon": -7.5898, "points": 800, "trucks": 40, "angles": (-135, 45)},   # Sea is NW
    "Rabat":      {"lat": 34.0209, "lon": -6.8416, "points": 500, "trucks": 25, "angles": (-135, 45)},   # Sea is NW
    "Marrakech":  {"lat": 31.6295, "lon": -7.9811, "points": 600, "trucks": 30, "angles": (0, 360)},     # Inland
    "Agadir":     {"lat": 30.4278, "lon": -9.5981, "points": 400, "trucks": 20, "angles": (-90, 80)},    # Sea is W
    "Fes":        {"lat": 34.0331, "lon": -5.0003, "points": 450, "trucks": 25, "angles": (0, 360)},     # Inland
    "Tangier":    {"lat": 35.7595, "lon": -5.8340, "points": 350, "trucks": 20, "angles": (-90, 0)},     # Sea is N and W
    "Laayoune":   {"lat": 27.1253, "lon": -13.1625,"points": 150, "trucks": 10, "angles": (-90, 90)},    # Sea is W
}

POINT_TYPES = ["trash_bin", "hospital", "hotel", "restaurant", "residential", "pharmacy", "factory"]
TRUCK_TYPES = ["standard", "heavy", "medical", "recycling"]

POINTS_CSV_FILE = "points_morocco.csv"
TRUCKS_CSV_FILE = "trucks_morocco.csv"

def generate_random_coordinate(base_lat, base_lon, radius_km, angles=(0, 360)):
    min_a, max_a = angles
    angle_deg = random.uniform(min_a, max_a)
    angle_rad = math.radians(angle_deg)
    
    # Sqrt for uniform spread in real geographic distance
    r = math.sqrt(random.uniform(0, 1)) * radius_km
    
    lat_offset = (r * math.sin(angle_rad)) / 111.0
    lon_offset = (r * math.cos(angle_rad)) / (111.0 * math.cos(math.radians(base_lat)))
    
    return round(base_lat + lat_offset, 6), round(base_lon + lon_offset, 6)

def generate_data():
    points_data = []
    trucks_data = []
    
    point_id_counter = 1
    truck_id_counter = 1
    
    for city, info in CITIES.items():
        base_lat, base_lon = info["lat"], info["lon"]
        
        # Generate Points for this city
        for i in range(info["points"]):
            pt_type = random.choices(POINT_TYPES, weights=[60, 5, 10, 15, 8, 2, 0])[0]
            lat, lon = generate_random_coordinate(base_lat, base_lon, radius_km=18.0, angles=info["angles"])
            
            volume = random.randint(200, 1000)
            if pt_type in ["hotel", "hospital"]:
                volume = random.randint(1500, 5000)
                
            points_data.append({
                "id": point_id_counter,
                "lat": lat,
                "lon": lon,
                "name": f"{city}_{pt_type.title()}_{point_id_counter}",
                "type": pt_type,
                "volume_l": volume,
                "_city": city  # Internal tag to verify distribution
            })
            point_id_counter += 1
            
        # Generate Trucks for this city (they spawn near the center/depot)
        for i in range(info["trucks"]):
            t_type = random.choices(TRUCK_TYPES, weights=[70, 20, 5, 5])[0]
            lat, lon = generate_random_coordinate(base_lat, base_lon, radius_km=3.0, angles=info["angles"])
            
            cap = 5000 if t_type == "standard" else 12000
            speed = 40 if t_type == "heavy" else 60
            
            trucks_data.append({
                "id": truck_id_counter,
                "lat": lat,
                "lon": lon,
                "capacity_l": cap,
                "name": f"Flotte_{city}_{t_type.capitalize()}_{truck_id_counter}",
                "type": t_type,
                "speed_kmh": speed,
                "_city": city
            })
            truck_id_counter += 1

    # Write Points CSV
    with open(POINTS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "lat", "lon", "name", "type", "volume_l", "city"])
        for p in points_data:
            writer.writerow([p["id"], p["lat"], p["lon"], p["name"], p["type"], p["volume_l"], p["_city"]])
            
    # Write Trucks CSV
    with open(TRUCKS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "lat", "lon", "capacity_l", "name", "type", "speed_kmh", "city"])
        for t in trucks_data:
            writer.writerow([t["id"], t["lat"], t["lon"], t["capacity_l"], t["name"], t["type"], t["speed_kmh"], t["_city"]])

    print(f"✅ Generated {len(points_data)} points in {POINTS_CSV_FILE}")
    print(f"✅ Generated {len(trucks_data)} trucks in {TRUCKS_CSV_FILE}")

if __name__ == "__main__":
    generate_data()

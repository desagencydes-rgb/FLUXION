import requests

points_file = "points_morocco.csv"
trucks_file = "trucks_morocco.csv"

# 1. Upload Points
print("Uploading Points...")
with open(points_file, "rb") as f:
    resp = requests.post("http://localhost:8000/api/import/points", files={"file": (points_file, f)})
print(resp.status_code)
print(resp.json())

# 2. Upload Trucks
print("Uploading Trucks...")
with open(trucks_file, "rb") as f:
    resp = requests.post("http://localhost:8000/api/import/trucks", files={"file": (trucks_file, f)})
print(resp.status_code)
print(resp.json())

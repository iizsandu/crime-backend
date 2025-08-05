from fastapi import APIRouter, Query
from models import CommuteRequest # To get input in correct format
from app.utils.route_planner import get_route_with_crimes
from app.utils.database import crime_collection
import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point
from geopy.geocoders import Nominatim
import geopandas as gpd
import time

router = APIRouter()

@router.post("/commute")
def get_safe_route(data: CommuteRequest):
    
    #Load the base map of Delhi
    G = ox.io.load_graphml(filepath="delhi.graphml")

    # Get Geocode for both origin and destination
    geolocator = Nominatim(user_agent="commute_mapper")

    origin_location = geolocator.geocode(data.location_origin)
    destination_location = geolocator.geocode(data.location_destination)

    origin_coords = (origin_location.latitude, origin_location.longitude)
    time.sleep(1)
    destination_coords = (destination_location.latitude, destination_location.longitude)

    # Find Nearest Nodes in the graph
    origin_node = ox.distance.nearest_nodes(G, X=origin_coords[1], Y=origin_coords[0])
    destination_node = ox.distance.nearest_nodes(G, X=destination_coords[1], Y=destination_coords[0])

    # Get the shortest path
    route = nx.shortest_path(G, origin_node, destination_node, weight='length')
    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

    route_line = LineString([(lon, lat) for lat, lon in route_coords])

    # get nearby crime locations from MongoDB atlas
    crime_docs = list(crime_collection.find({}))
    crime_points = []

    for doc in crime_docs:
        lon, lat = doc['coordinates']['coordinates']
        point = Point(lon, lat)
        crime_points.append({
            "location": doc['location'],
            "crime_type": doc['crime_type'],
            "coordinates": (lat, lon),
            "point_geom": point

        })

    # Filter crimes near the route (within 200 meters)
    crime_gdf = gpd.GeoDataFrame(crime_points, geometry=[p['point_geom'] for p in crime_points], crs="EPSG:4326")
    route_gdf = gpd.GeoDataFrame(geometry=[route_line], crs="EPSG:4326")

    # Projecting both for accurate buffering
    crime_gdf = crime_gdf.to_crs(epsg=32643)
    route_gdf = route_gdf.to_crs(epsg=32643)    
    buffered_route = route_gdf.buffer(200).iloc[0]

    nearby_crimes = crime_gdf[crime_gdf.geometry.within(buffered_route)]

    crime_hotspots = [
        {
            "location": row['location'],
            "crime_type": row['crime_type'],
            "coordinates": row['coordinates']
        }
        for _,row in nearby_crimes.iterrows()
    ]

    return {"route": route_coords, "crime_hotspots": crime_hotspots}


@router.get("/commute/route")
def get_commute_route(
    origin_lat: float = Query(...),
    origin_lon: float = Query(...),
    dest_lat: float = Query(...),
    dest_lon: float = Query(...)
):
    docs = crime_collection.find({})
    crime_points = [(doc['coordinates']['coordinates'][1], doc['coordinates']['coordinates'][0]) for doc in docs]

    result = get_route_with_crimes(
        origin=(origin_lat, origin_lon),
        destination=(dest_lat, dest_lon),
        crime_points=crime_points
    )

    return {
        "route_node_ids": result["route"],
        "crime_near_route": result["crimes_near_route"]
    }




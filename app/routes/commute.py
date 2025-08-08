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
    G = ox.io.load_graphml(filepath="graph/delhi.graphml")

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


# @router.get("/commute/route")
# def get_commute_route(
#     origin_lat: float = Query(...),
#     origin_lon: float = Query(...),
#     dest_lat: float = Query(...),
#     dest_lon: float = Query(...)
# ):
#     docs = crime_collection.find({})
#     crime_points = [(doc['coordinates']['coordinates'][1], doc['coordinates']['coordinates'][0]) for doc in docs]

#     result = get_route_with_crimes(
#         origin=(origin_lat, origin_lon),
#         destination=(dest_lat, dest_lon),
#         crime_points=crime_points
#     )

#     return {
#         "route_node_ids": result["route"],
#         "crime_near_route": result["crimes_near_route"]
#     }



@router.get("/commute/route")
def get_route_from_coords(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float
):

    G = ox.io.load_graphml(filepath="graph/delhi.graphml")

    origin_node = ox.distance.nearest_nodes(G, X=origin_lon, Y=origin_lat)
    destination_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)

    # Get the shortest path
    route = nx.shortest_path(G, origin_node, destination_node, weight='length')
    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

    route_line = LineString([(lon, lat) for lat, lon in route_coords])

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

    return {"route_coords": route_coords, "crime_hotspots": crime_hotspots}


@router.get("/commute/safe_route")
def get_safe_route_from_coords(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float
):
    """
    Returns a route where all edges are >200m away from any crime location.
    If no such route exists, returns an error message.
    """

    # Load street graph
    G = ox.io.load_graphml(filepath="graph/delhi.graphml")

    # Find nearest network nodes for origin & destination
    origin_node = ox.distance.nearest_nodes(G, X=origin_lon, Y=origin_lat)
    destination_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)

    # Fetch all crime points from MongoDB
    crime_docs = list(crime_collection.find({}))
    crime_points = [Point(doc['coordinates']['coordinates']) for doc in crime_docs]

    # Convert crime points to GeoDataFrame
    crime_gdf = gpd.GeoDataFrame(geometry=crime_points, crs="EPSG:4326").to_crs(epsg=32643)

    # Get all edges as GeoDataFrame
    edges = ox.convert.graph_to_gdfs(G, nodes=False, edges=True)
    edges = edges.to_crs(epsg=32643)

    # Create 200m buffer around crime points
    crime_buffer = crime_gdf.buffer(200)
    crime_union = gpd.GeoSeries(crime_buffer.unary_union, crs=crime_gdf.crs)

    # Find edges within crime buffer
    unsafe_edges = edges[edges.intersects(crime_union.iloc[0])]

    # Remove unsafe edges from graph
    G_safe = G.copy()
    G_safe.remove_edges_from(unsafe_edges.index)

    # Try computing safe route
    try:
        route = nx.shortest_path(G_safe, origin_node, destination_node, weight='length')
    except nx.NetworkXNoPath:
        return {"error": "No safe route found beyond 200m from any crime location."}

    # Extract coordinates for the route
    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

    return {
        "route_coords": route_coords,
        "crime_hotspots": []  # No nearby crimes because we avoided them
    }

import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point

def get_route_with_crimes(origin, destination, crime_points):
    # Load walking network 
    G = ox.graph_from_place("Delhi, India", network_type='walk')

    # Get nearest nodes to origin and destination
    origin_node = ox.distance.nearest_nodes(G, origin[1], origin[0])  # (lon, lat)
    dest_node = ox.distance.nearest_nodes(G, destination[1], destination[0])

    # Compute the shortest path
    route = nx.shortest_path(G, origin_node, dest_node, weight='length')

    # Convert route to LineString and GeoDataFrame
    # route_geom = ox.utils_graph.route_to_linestring(G, route)
    # route_gdf = gpd.GeoDataFrame(geometry=[route_geom], crs="EPSG:4326")

    route_gdf = ox.routing.route_to_gdf(G, route, weight='length')

    # Create GeoDataFrame for crime points
    crime_gdf = gpd.GeoDataFrame(geometry=[Point(pt[1], pt[0]) for pt in crime_points], crs="EPSG:4326")

    # Project both to UTM for distance buffering
    crime_gdf = crime_gdf.to_crs(epsg=32643)     # EPSG for Delhi UTM zone
    route_gdf = route_gdf.to_crs(epsg=32643)

    # Create a buffer around the route (e.g., 200m)
    buffered_route = route_gdf.buffer(200).iloc[0]

    # Filter crimes within the buffer
    crimes_near_route = crime_gdf[crime_gdf.geometry.within(buffered_route)]

    return {
        "route": route,
        "crimes_near_route": crimes_near_route.to_crs("EPSG:4326").geometry.apply(lambda p: (p.y, p.x)).tolist()
    }

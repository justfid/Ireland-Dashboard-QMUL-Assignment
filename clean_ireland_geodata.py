import geopandas as gpd

#loads ITM (EPSG:2157) geojson
gdf = gpd.read_file("data/geojson/ireland.geojson")
#forces crs if missing
gdf = gdf.set_crs(epsg=2157)
#converts to WGS84 - right format
gdf_4326 = gdf.to_crs(epsg=4326)

#saves output
gdf_4326.to_file("data/geojson/ireland_wgs84.geojson", driver="GeoJSON")

#NOTE this script only has to be run once
print("Converted → ireland_wgs84.geojson")


#TODO move to utils maybe or data?
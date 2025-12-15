import geopandas as gpd

#loads ITM (EPSG:2157) geojson
gdf = gpd.read_file("data/raw/geojson/ie.json")
#forces crs if missing


gdf = gdf.set_crs(epsg=2157, allow_override=True) 
#converts to WGS84 - right format
gdf_4326 = gdf.to_crs(epsg=4326)

#saves output
gdf_4326.to_file("data/cleaned/geojson/cleaned_ROI.geojson", driver="GeoJSON")

#NOTE this script only has to be run once
print("Converted -> cleaned_ROI.geojson")


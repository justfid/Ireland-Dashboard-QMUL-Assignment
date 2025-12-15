import folium
import json
import streamlit as st
from streamlit.components.v1 import html

def render_ireland_map(ireland_path: str, ni_path: str, county_view: bool) -> str:
    """
    Renders an OpenStreetMap map with:
    - Republic of Ireland highlighted green (as ONE layer)
    - Northern Ireland highlighted blue

    Returns:
        str: HTML representation of the map to be embedded with `html(...)`.
    """

    #creates base map
    open_street_map = folium.Map(
        location=[53.5, -7.5],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    #loads ROI + NI GeoJSON
    with open(ireland_path, "r") as file:
        ireland_geo = json.load(file)

    with open(ni_path, "r") as file:
        ni_geo = json.load(file)

    #ROI
    folium.GeoJson(
        ireland_geo,            
        name="Republic of Ireland",
        style_function=lambda feat: {
            "fillColor": "#33aa33",
            "color": "#228822",
            "weight": 1,
            "fillOpacity": 0.25,
        },
    ).add_to(open_street_map)

    #NI
    folium.GeoJson(
        ni_geo,
        name="Northern Ireland",
        style_function=lambda feat: {
            "fillColor": "#3355ff",
            "color": "#2233aa",
            "weight": 2,
            "fillOpacity": 0.30,
        },
    ).add_to(open_street_map)

    #layer control
    folium.LayerControl().add_to(open_street_map)

    #return HTML string for the map (cache-friendly)
    return open_street_map._repr_html_()



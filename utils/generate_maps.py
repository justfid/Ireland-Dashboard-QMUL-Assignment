import folium
import json
import streamlit as st
from streamlit.components.v1 import html

def render_ireland_map(ireland_path: str, ni_path: str, county_view: bool) -> str:
    """
    Renders an OpenStreetMap map with:
    - Republic of Ireland highlighted green (as ONE layer)
    - Northern Ireland highlighted blue
    - Tooltips which show county names when county_view=True,
      or static nation labels when county_view=False.

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

    #creates common "display_name"
    [feat.setdefault("properties", {}).update(
        {"display_name": feat["properties"].get("name", "").title()}
    ) for feat in ireland_geo.get("features", [])]

    [feat.setdefault("properties", {}).update(
        {"display_name": feat["properties"].get("CountyName", "").title()}
    ) for feat in ni_geo.get("features", [])]

    #tooltip config: county -> show feature 'name'; nation -> static label
    if county_view:
        common_tooltip = dict(
            fields=["display_name"],
            aliases=["County:"],
            localize=True,
            sticky=True,
            labels=True,
            style=("background-color: white; color: #222; border: 1px solid #ccc;")
        )
        roi_tooltip = folium.features.GeoJsonTooltip(**common_tooltip)
        ni_tooltip  = folium.features.GeoJsonTooltip(**common_tooltip)
    else:
        roi_tooltip = folium.Tooltip("Republic of Ireland")
        ni_tooltip  = folium.Tooltip("Northern Ireland")

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
        highlight_function=lambda feat: {"weight": 3, "color": "#000000", "fillOpacity": 0.35},
        tooltip=roi_tooltip
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
        highlight_function=lambda feat: {"weight": 3, "color": "#000000", "fillOpacity": 0.45},
        tooltip=ni_tooltip
    ).add_to(open_street_map)

    #layer control
    folium.LayerControl().add_to(open_street_map)

    #return HTML string for the map (cache-friendly)
    return open_street_map._repr_html_()



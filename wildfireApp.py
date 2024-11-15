import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap
from arcgis.gis import GIS
from arcgis.features import GeoAccessor, GeoSeriesAccessor
gis = GIS()

# Set up 
st.set_page_config(page_title='Dashboard', layout='wide')
st.title('Canadian Wildfire Dashboard')
st.sidebar.title('About')
st.sidebar.info('Explore Active Wildfire in Canada')


# Dictionary to map agency codes to province names
agency_to_province = {
    'ak': 'Alaska',
    'ab': 'Alberta',
    'bc': 'British Columbia',
    'mb': 'Manitoba',
    'nb': 'New Brunswick',
    'nl': 'Newfoundland and Labrador',
    'ns': 'Nova Scotia',
    'on': 'Ontario',
    'pe': 'Prince Edward Island',
    'nt': 'Northwest Territories',
    'qc': 'Quebec',
    'sk': 'Saskatchewan',
    'yt': 'Yukon'
}

@st.cache_data
def read_fl(item_id):
    living_atlas_item = gis.content.get(item_id)
    feature_layer = living_atlas_item.layers[0]
    wf_sdf = feature_layer.query(where="1=1", out_sr=4326).sdf
    return wf_sdf

# Retrieve Wildfire layer and create SDF
item_id = "21638fcd54d14a25b6f1affdef812146"
wildfire_sdf = read_fl(item_id)
st.write(wildfire_sdf)
# Filter and create Province column
conus_fires = wildfire_sdf[wildfire_sdf['Agency'] == 'conus']
canada_wildfire_sdf = wildfire_sdf[wildfire_sdf['Agency'] != 'conus']
canada_wildfire_sdf['Province'] = wildfire_sdf['Agency'].map(agency_to_province)
canada_wildfire_sdf = canada_wildfire_sdf.drop(columns=['Agency'])

# # # Create chart in side bar # # #

# Create dropdown for provinces
provinces = canada_wildfire_sdf['Province'].unique()
province = st.sidebar.selectbox('Select a district', provinces)
basemap_selection = st.sidebar.selectbox('Select a basemap', ['CartoDB.DarkMatter', 'CartoDB.Positron', 'openstreetmap','ESRI'])

# Create check box and sdf for US fires
conus_fires = wildfire_sdf[wildfire_sdf['Agency'] == 'conus']
overlay_us_fires = st.sidebar.toggle('Overlay US Fires')
if overlay_us_fires:
    st.sidebar.write("US Fires Layer Activated!")


# Map different stages of control
stage_of_control_mapping = {
    'BH': 'Being Held',
    'OC': 'Out of Control',
    'UC': 'Under Control',
    'Pre': 'Prescribed'
}
canada_wildfire_sdf['Stage_of_Control'] = canada_wildfire_sdf['Stage_of_Control'].replace(stage_of_control_mapping)


# Filter for fires in specific provinces
filtered_fires = canada_wildfire_sdf[canada_wildfire_sdf['Province'] == province] 

unit = st.sidebar.radio(
    "Select a Unit",
    ['Hectares', 'Acres']
)

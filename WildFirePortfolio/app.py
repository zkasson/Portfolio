import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap
from arcgis.gis import GIS
from arcgis import GeoAccessor
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
    sdf = GeoAccessor.from_layer(feature_layer)
    return sdf

# Retrieve Wildfire layer and create SDF
item_id = "21638fcd54d14a25b6f1affdef812146"
wildfire_sdf = read_fl(item_id)

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
overlay_us_fires = st.sidebar.checkbox('Overlay US Fires')


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

conversion_factor = 2.47105
def correct_unit(filtered_df,unit_df):
    if unit_df == 'Hectares':  
        df_final = filtered_df 
        return df_final
    elif unit_df == 'Acres':
        df_final = filtered_df
        df_final['NH'] = filtered_df['NH'] * conversion_factor
        df_final['SH'] = filtered_df['SH'] * conversion_factor
        return df_final
df_final = correct_unit(filtered_fires,unit)

# Calculate the upper limit for the y-axis
max_sh = df_final['SH'].max()  # Find the max value in the SH column
upper_limit = max_sh + 250  
rounded_upper_limit = round(upper_limit / 100) * 100 

# Create plot
fig, ax = plt.subplots(1, 1)

df_final.plot(kind='bar', ax=ax,
    ylabel=unit, xlabel='Province')
ax.set_title('Hectares of Fire')
ax.set_ylim(0, rounded_upper_limit)
ax.set_xticklabels([])
stats = st.sidebar.pyplot(fig)



## Create the map

map = leafmap.Map(
    layers_control=True,
    draw_control=False,
    measure_control=False,
    fullscreen_control=False)

map.add_basemap(basemap_selection)
map.add_gdf(
    gdf=filtered_fires,
    zoom_to_layer=False,
    layer_name='districts',
    info_mode='on_click',
    style={'color': '#B2BEB5', 'fillOpacity': 0.3, 'weight': 0.5},
    )




map_streamlit = map.to_streamlit(800, 600)
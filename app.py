import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap

# Set up 
st.set_page_config(page_title='Dashboard', layout='wide')
st.title('Highway Dashboard')
st.sidebar.title('About')
st.sidebar.info('Explore Highway Statistics')


data_url = 'https://github.com/spatialthoughts/python-dataviz-web/releases/download/osm/'
        
gpkg_file = 'karnataka.gpkg'
csv_file = 'highway_lengths_by_district.csv'

@st.cache_data
def read_gdf(url, layer):
    gdf = gpd.read_file(url, layer=layer)
    return gdf

@st.cache_data
def read_csv(url):
    df = pd.read_csv(url)
    return df

gpkg_url = data_url + gpkg_file
csv_url = data_url + csv_file
districts_gdf = read_gdf(gpkg_url, 'karnataka_districts')
roads_gdf = read_gdf(gpkg_url, 'karnataka_highways')
lengths_df = read_csv(csv_url)

# # # Create chart in side bar # # #

districts = lengths_df['DISTRICT'].values
district = st.sidebar.selectbox('Select a district', districts)
basemap_selection = st.sidebar.selectbox('Select a basemap', ['CartoDB.DarkMatter', 'CartoDB.Positron', 'openstreetmap','ESRI'])
overlay = st.sidebar.checkbox('Overlay roads')
filtered = lengths_df[lengths_df['DISTRICT'] == district] 

col1, col2, col3 = st.sidebar.columns(3)

nh_color = col1.color_picker('Pick NH Color', '#2e6f40', key='nh')
sh_color = col2.color_picker('Pick SH Color', '#609C9E', key='sh')
unit = col3.radio(
    "Select a Unit",
    ['km', 'mi']
)

conversion_factor = 0.621371
def correct_unit(filtered_df,unit_df):
    if unit_df == 'km':  
        df_final = filtered_df 
        return df_final
    elif unit_df == 'mi':
        df_final = filtered_df
        df_final['NH'] = filtered_df['NH'] * conversion_factor
        df_final['SH'] = filtered_df['SH'] * conversion_factor
        return df_final
df_final = correct_unit(filtered,unit)

# Calculate the upper limit for the y-axis
max_sh = df_final['SH'].max()  # Find the max value in the SH column
upper_limit = max_sh + 250  
rounded_upper_limit = round(upper_limit / 100) * 100 

# Create plot
fig, ax = plt.subplots(1, 1)

df_final.plot(kind='bar', ax=ax, color=[nh_color, sh_color],
    ylabel=unit, xlabel='Category')
ax.set_title('Length of Highways')
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
    gdf=districts_gdf,
    zoom_to_layer=False,
    layer_name='districts',
    info_mode='on_click',
    style={'color': '#B2BEB5', 'fillOpacity': 0.3, 'weight': 0.5},
    )

# Filter to both road types and add to map if overlay is checked
sh_gdf = roads_gdf[roads_gdf['ref'].str.startswith('SH')]
nh_gdf = roads_gdf[roads_gdf['ref'].str.startswith('NH')]
if overlay:
    map.add_gdf(
        gdf=nh_gdf,
        zoom_to_layer=False,
        layer_name='highways',
        info_mode=None,
        style={'color': nh_color, 'weight': 3},
    )
    map.add_gdf(
        gdf=sh_gdf,
        zoom_to_layer=False,
        layer_name='highways',
        info_mode=None,
        style={'color': sh_color, 'weight': 2},
    )
    
selected_gdf = districts_gdf[districts_gdf['DISTRICT'] == district]

map.add_gdf(
    gdf=selected_gdf,
    layer_name='selected',
    zoom_to_layer=True,
    info_mode=None,
    style={'color': 'black', 'fill': None, 'weight': 2.5}
 )


map_streamlit = map.to_streamlit(800, 600)
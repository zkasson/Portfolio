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
    sdf = feature_layer.query(where="1=1", out_sr=4326).sdf
    return sdf
@st.cache_data
def read_json(url):
    prov_gdf = gpd.read_file(url)
    # Clean the 'prov_name_en' column to remove brackets and rename it
    # prov_gdf['prov_name_en'] = prov_gdf['prov_name_en'].apply(lambda x: x[0] if isinstance(x, list) else x)
    # prov_gdf.rename(columns={'prov_name_en': 'Province'}, inplace=True)
    return prov_gdf



# Retrieve Wildfire layer and create SDF & Retrieve territories layer and create SDF
item_id = "21638fcd54d14a25b6f1affdef812146"
json_file = 'https://raw.githubusercontent.com/zkasson/Portfolio/refs/heads/main/canada-province.geojson'
wildfire_sdf = read_fl(item_id)
prov_gdf = read_json(json_file)
st.write(prov_gdf)

# Filter and create Province column, Map from agency to province
conus_fires = wildfire_sdf[wildfire_sdf['Agency'] == 'conus']
canada_wildfire_sdf = wildfire_sdf[wildfire_sdf['Agency'] != 'conus']
canada_wildfire_sdf['Province'] = wildfire_sdf['Agency'].map(agency_to_province)
canada_wildfire_sdf = canada_wildfire_sdf.drop(columns=['Agency'])


# Create dropdown for provinces
provinces = canada_wildfire_sdf['Province'].unique()
province = st.sidebar.selectbox('Select a district', provinces)
st.sidebar.write(province)
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
bh_color = '#ffff00'
oc_color = '#ff0000'
uc_color = '#008000'
pre_color = "#ffffff"

# Group by Province and Stage_of_Control, then sum Hectares__Ha_
area_sdf = canada_wildfire_sdf.groupby(['Province', 'Stage_of_Control'])['Hectares__Ha_'].sum().reset_index()
area_sdf = area_sdf.pivot(index='Province', columns='Stage_of_Control', values='Hectares__Ha_').fillna(0)
area_sdf.columns.name = None


unit = st.sidebar.radio(
    "Select a Unit",
    ['Hectares', 'Acres']
)

conversion_factor = 2.47105
def correct_unit(area_sdf,unit_df):
    if unit_df == 'Hectares':  
        area_final = area_sdf 
        return area_final
    elif unit_df == 'Acres':
        area_final = area_sdf
        area_final['Prescribed'] = area_sdf['Prescribed'] * conversion_factor
        area_final['Being Held'] = area_sdf['Being Held'] * conversion_factor
        area_final['Out of Control'] = area_sdf['Out of Control'] * conversion_factor
        area_final['Under Control'] = area_sdf['Under Control'] * conversion_factor
        return area_final
area_final = correct_unit(area_sdf,unit)

area_final = area_final.reset_index().melt(id_vars=['Province'], 
                                                  value_vars=['Being Held', 'Out of Control', 'Prescribed', 'Under Control'],
                                                  var_name='Stage_of_Control', 
                                                  value_name='Area')

# Filter data for the selected province (if required)
area_final = area_final[area_final['Province'] == province]

# Calculate the upper limit for the y-axis
max_sh = area_final['Area'].max()  # Find the max value in the SH column
upper_limit = max_sh + 5000  
rounded_upper_limit = round(upper_limit / 100) * 100 

area_final = area_final[area_final['Province'] == province]

# Create plot
fig, ax = plt.subplots(1, 1)

area_final.plot(kind='bar', ax=ax,#color=[pre_color,bh_color, oc_color, uc_color],
    ylabel=unit, xlabel='Control')
ax.set_title(f'{unit} of Fire')
ax.set_ylim(0, rounded_upper_limit)
ax.set_xticklabels([])
stats = st.sidebar.pyplot(fig)


# Filter for fires in specific provinces -- This is for Spatial use 
filtered_fires = canada_wildfire_sdf[canada_wildfire_sdf['Province'] == province] 

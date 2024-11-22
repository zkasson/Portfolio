import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap
import folium
from folium import CircleMarker
from arcgis.gis import GIS
from arcgis import GeoAccessor, GeoSeriesAccessor
gis = GIS()

# Set up 
st.set_page_config(page_title='Dashboard', layout='wide')
area_option = ["Canadian Wildfires","US Wildfires"]
area_selection = st.sidebar.segmented_control(
    "**Area Selction**", area_option, selection_mode="single"
)
if area_selection == 'Canadian Wildfires':
    st.title('Canadian Wildfire Dashboard')
    st.sidebar.title('About')
    st.sidebar.info('Explore Active Wildfire in Canada')

        # Dictionary to map agency codes to province names
    agency_to_province = {
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
        provs_gdf = gpd.read_file(url)
        return provs_gdf


    # Retrieve Wildfire layer and create SDF & Retrieve territories layer and create SDF
    item_id = "21638fcd54d14a25b6f1affdef812146"
    json_file = 'https://raw.githubusercontent.com/zkasson/Portfolio/refs/heads/main/CanadaProvinces.geojson'
    wildfire_sdf = read_fl(item_id)
    provs_gdf = read_json(json_file)

    # Filter and create Province column, Map from agency to province
    canada_wildfire_sdf = wildfire_sdf[(wildfire_sdf['Agency'] != 'conus') & (wildfire_sdf['Agency'] != 'ak')]
    canada_wildfire_sdf['Province'] = wildfire_sdf['Agency'].map(agency_to_province)
    canada_wildfire_sdf = canada_wildfire_sdf.drop(columns=['Agency'])


    # Create dropdown for provinces
    provinces = provs_gdf['Province'].unique()
    province = st.sidebar.selectbox('Select a Province', provinces)
    basemap_selection = st.sidebar.selectbox('Select a basemap', ['CartoDB.Positron', 'CartoDB.DarkMatter', 'openstreetmap'])


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

    # Create unit variable and engineer data to use correct unit
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
            columns_to_convert = ['Prescribed', 'Being Held', 'Out of Control', 'Under Control']
            for col in columns_to_convert:
                if col in area_final.columns:
                    area_final[col] = area_final[col] * conversion_factor
            return area_final
        else:
            # Handle unexpected unit cases
            raise ValueError(f"Unsupported unit: {unit_df}")
    area_final = correct_unit(area_sdf,unit)


    # Dynamically select only the columns present in the DataFrame
    available_columns = [col for col in ['Being Held', 'Out of Control', 'Prescribed', 'Under Control'] if col in area_final.columns]
    area_final = area_final.reset_index().melt(id_vars=['Province'], 
                                                    value_vars=available_columns,
                                                    var_name='Stage_of_Control', 
                                                    value_name='Area')

    # Filter data for the selected province
    area_final = area_final[area_final['Province'] == province]

    no_fires_bool = area_final['Area'].dropna().empty
    if no_fires_bool:
        rounded_upper_limit =5000
    else:
        # Calculate the upper limit for the y-axis
        max_sh = area_final['Area'].max()  # Find the max value in the area column
        upper_limit = max_sh + (max_sh/10) 
        rounded_upper_limit = round(upper_limit / 100) * 100 if upper_limit > 99 else 100


    if no_fires_bool:
        st.sidebar.write(f'**There are no ongoing fires in {province}**')
    else:
        # # # Create Chart # # # 
        colors = {
            "Being Held": "orange",
            "Out of Control": "red",
            "Under Control": "green",
            "Prescribed": "yellow"  
        }
        area_final["Color"] = area_final["Stage_of_Control"].map(colors)

        # Create the plot
        fig, ax = plt.subplots(1, 1,dpi=100)
        bars = ax.bar(
            area_final["Stage_of_Control"],
            area_final["Area"],
            color=area_final["Color"]
        )

        # Customize the plot
        ax.set_ylabel(f'Area ({unit})')
        ax.set_xlabel('Control Stage')
        ax.set_title(f'{unit} of fire within {province}')
        ax.set_ylim(0, rounded_upper_limit)

        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))

        for bar, area in zip(bars, area_final["Area"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,  # x-coordinate
                bar.get_height() + rounded_upper_limit * 0.02,  # y-coordinate
                f'{area:,.0f} {unit}', 
                ha='center',  
                va='bottom',  
                fontsize=10  
            )
        # Display the plot
        plt.tight_layout()
        stats = st.sidebar.pyplot(fig, use_container_width=True)


    # # # M A P # # #
    # # # Create the map # # #
    canada_wildfire_gdf = gpd.GeoDataFrame(canada_wildfire_sdf, geometry='SHAPE')
    canada_wildfire_gdf['Start_Date'] = canada_wildfire_gdf['Start_Date'].dt.strftime('%Y-%m-%d')

    selected_prov_gdf = provs_gdf[provs_gdf['Province'] == province]
   
    def get_marker_size(Hectares):
        if Hectares < 1000:
            return 6
        elif Hectares < 10000:
            return 9
        elif Hectares < 50000:
            return 14
        elif Hectares < 300000:
            return 19
        else:
            return 24
    canada_wildfire_gdf['Hectares__Ha_'] = canada_wildfire_gdf['Hectares__Ha_'].fillna(0)
    canada_wildfire_gdf['marker_size'] = canada_wildfire_gdf['Hectares__Ha_'].apply(get_marker_size)


    # Ensure geometries are Point types
    canada_wildfire_gdf['latitude'] = canada_wildfire_gdf.geometry.y
    canada_wildfire_gdf['longitude'] = canada_wildfire_gdf.geometry.x

    # Create Map
    # zoom = 4.7
    # if province == '':
    #     zoom = 4 
    # elif province == '':
    #     zoom = 4
    centroid = selected_prov_gdf.geometry.centroid.iloc[0]
    map = folium.Map(location=[centroid.y, centroid.x], zoom_start=4.7)
    folium.TileLayer(f'{basemap_selection}').add_to(map)
    # Add the state GeoDataFrame
    folium.GeoJson(
        provs_gdf,
        name="Province",  
        style_function=lambda x: {
            'color': '#B2BEB5',  
            'fillColor': '#B2BEB5', 
            'fillOpacity': 0.3,
            'weight': 1
        },
        tooltip=folium.GeoJsonTooltip(fields=["State"], aliases=["State:"]),
    ).add_to(map)
    folium.GeoJson(
    selected_prov_gdf,
    name="Selected Province",
    style_function=lambda x: {
        'color': 'black',  
        'fillColor': '#B2BEB5', 
        'fillOpacity': 0.2,
        'weight': 2.5
    },
    tooltip=folium.GeoJsonTooltip(fields=["State"], aliases=["State:"]),
    ).add_to(map) 

    
    # Path to your fire icon image
    fire_icon_path = "https://github.com/zkasson/Portfolio/blob/main/Fire2.png?raw=true"

    # Add Wildfires
    for _, row in canada_wildfire_gdf.iterrows():
        # Dynamically set the icon size based on marker_size
        fire_icon = folium.CustomIcon(
            fire_icon_path,
            icon_size=(row['marker_size'] * 2, row['marker_size'] * 2)  # Scale size dynamically
        )

        folium.Marker(
            location=(row['latitude'], row['longitude']),
            icon=fire_icon,  # Custom fire icon with dynamic size
            tooltip=f"Acres: {row['DailyAcres']}"
        ).add_to(map)
    # Render the map in Streamlit
    st.components.v1.html(map._repr_html_(), height=600)
    # map = leafmap.Map(
    #     layers_control=True,
    #     draw_control=False,
    #     measure_control=False,
    #     fullscreen_control=False)

    # map.add_basemap(basemap_selection)
    # map.add_gdf(
    #     gdf=canada_wildfire_gdf,
    #     zoom_to_layer=False,
    #     layer_name='Fires',
    #     info_mode='on_click',
    #     )
    # map.add_gdf(
    #     gdf=provs_gdf,
    #     zoom_to_layer=False,
    #     layer_name='Provinces',
    #     info_mode='on_click',
    #     style={'color': '#B2BEB5', 'fillOpacity': 0.3, 'weight': 0.5},
    #     )

    # selected_prov_gdf = provs_gdf[provs_gdf['Province'] == province]

    # map.add_gdf(
    #     gdf=selected_prov_gdf,
    #     layer_name='Selected Province',
    #     zoom_to_layer=True,
    #     info_mode=None,
    #     style={'color': 'black', 'fill': None, 'weight': 2.5}
    # )



    # map_streamlit = map.to_streamlit(800, 600)


else:
    st.title('US Wildfire Dashboard')
    st.sidebar.title('About')
    st.sidebar.info('Explore Active Wildfire in the US')

    # Dictionary to map orgin codes to state names, desired columns, Map fire types
    origin_to_state = {
        'US-AL': 'Alabama','US-AK': 'Alaska','US-AZ': 'Arizona','US-AR': 'Arkansas','US-CA': 'California','US-CO': 'Colorado','US-CT': 'Connecticut',
        'US-DE': 'Delaware', 'US-FL': 'Florida', 'US-GA': 'Georgia','US-HI': 'Hawaii','US-ID': 'Idaho','US-IL': 'Illinois','US-IN': 'Indiana',
        'US-IA': 'Iowa','US-KS': 'Kansas','US-KY': 'Kentucky','US-LA': 'Louisiana','US-ME': 'Maine','US-MD': 'Maryland','US-MA': 'Massachusetts','US-MI': 'Michigan','US-MN': 'Minnesota',
        'US-MS': 'Mississippi','US-MO': 'Missouri','US-MT': 'Montana','US-NE': 'Nebraska','US-NV': 'Nevada','US-NH': 'New Hampshire','US-NJ': 'New Jersey','US-NM': 'New Mexico',
        'US-NY': 'New York','US-NC': 'North Carolina','US-ND': 'North Dakota','US-OH': 'Ohio','US-OK': 'Oklahoma','US-OR': 'Oregon','US-PA': 'Pennsylvania',
        'US-RI': 'Rhode Island','US-SC': 'South Carolina','US-SD': 'South Dakota','US-TN': 'Tennessee','US-TX': 'Texas','US-UT': 'Utah','US-VT': 'Vermont',
        'US-VA': 'Virginia','US-WA': 'Washington','US-WV': 'West Virginia','US-WI': 'Wisconsin','US-WY': 'Wyoming','US-DC': 'District of Columbia','US-PR': 'Puerto Rico'
    }
    desired_columns = [
        "OBJECTID","IncidentName","IncidentTypeCategory","DailyAcres","PercentContained","FireDiscoveryDateTime","DiscoveryAcres",
        "POOCounty","POOState","FireCause","TotalIncidentPersonnel","ResidencesDestroyed","OtherStructuresDestroyed","Injuries","SHAPE"
    ]
    fire_type = {
        'WF': 'Contained',
        'RX': 'Prescribed'
        }

    json_file = r'https://raw.githubusercontent.com/zkasson/Portfolio/refs/heads/main/US_States.json'
    item_id = "d957997ccee7408287a963600a77f61f"

    def read_json(url):
        prov_gdf = gpd.read_file(url)
        return prov_gdf
    def read_fl(item_id):
        living_atlas_item = gis.content.get(item_id)
        feature_layer = living_atlas_item.layers[0]
        sdf = feature_layer.query(where="1=1", out_sr=4326).sdf
        return sdf

    # Read in data
    state_gdf = read_json(json_file)
    wildfire_sdf = read_fl(item_id)

    # Create dropdown for States and basemap
    states = state_gdf['State'].unique()
    state = st.sidebar.selectbox('Select a State', states)
    basemap_selection = st.sidebar.selectbox('Select a basemap', ['CartoDB.Positron', 'CartoDB.DarkMatter', 'openstreetmap'])

    # Data Engineering of wild fires
    wildfire_sdf = wildfire_sdf[desired_columns]
    wildfire_sdf['State'] = wildfire_sdf['POOState'].map(origin_to_state)
    wildfire_sdf = wildfire_sdf.drop(columns=['POOState'])
    wildfire_sdf['Type'] = wildfire_sdf['IncidentTypeCategory'].map(fire_type)
    wildfire_sdf = wildfire_sdf.drop(columns=['IncidentTypeCategory'])

    def update_type(row):
        if row['Type'] == 'Prescribed':
            return 'Prescribed'
        elif pd.isna(row['PercentContained']):
            return 'Unknown Containment'
        elif 0 < row['PercentContained'] < 100:
            return 'Actively Containing'
        elif row['PercentContained'] == 0:
            return 'Uncontained'
        else:
            return row['Type']
    wildfire_sdf['Type'] = wildfire_sdf.apply(update_type, axis=1)

    # Group by State and Type, then sum Acres
    area_sdf = wildfire_sdf.groupby(['State', 'Type'])['DailyAcres'].sum().reset_index()
    area_sdf = area_sdf.pivot(index='State', columns='Type', values='DailyAcres').fillna(0)
    area_sdf.columns.name = None

    # Create unit variable and engineer data to use correct unit
    unit = st.sidebar.radio(
        "Select a Unit",
        ['Acres', 'Hectares']
    )
    conversion_factor = 2.47105
    def correct_unit(area_sdf,unit_df):
        if unit_df == 'Acres':  
            area_final = area_sdf 
            return area_final
        elif unit_df == 'Hectares':
            area_final = area_sdf
            columns_to_convert = ['Actively Containing', 'Contained', 'Uncontained', 'Unknown Containment','Prescribed']
            for col in columns_to_convert:
                if col in area_final.columns:
                    area_final[col] = area_final[col] / conversion_factor
            return area_final
        else:
            # Handle unexpected unit cases
            raise ValueError(f"Unsupported unit: {unit_df}")
    area_final = correct_unit(area_sdf,unit)

    # Dynamically select only the columns present in the DataFrame
    available_columns = [col for col in ['Contained', 'Actively Containing', 'Prescribed', 'Uncontained','Unknown Containment'] if col in area_final.columns]
    area_final = area_final.reset_index().melt(id_vars=['State'], 
                                                    value_vars=available_columns,
                                                    var_name='Type', 
                                                    value_name='Area')
    
    # Filter data for the selected state
    area_final = area_final[area_final['State'] == state]
    no_fires_bool = area_final['Area'].dropna().empty

    if area_final['Area'].dropna().empty:
        rounded_upper_limit =5000
    else:
        # Calculate the upper limit for the y-axis
        max_sh = area_final['Area'].max()  # Find the max value in the area column
        upper_limit = max_sh + (max_sh / 10) if max_sh > 0 else 1000
        rounded_upper_limit = round(upper_limit / 100) * 100 if upper_limit > 99 else 100

    # # # Create Chart # # #
    if no_fires_bool:
        st.sidebar.write(f'**There are no ongoing fires in {state}**')
    else:
        colors = {
            "Actively Containing": "orange",
            "Uncontained": "red",
            "Contained": "green",
            "Prescribed": "#CCCC00",
            "Unknown Containment": "gray"  
        }
        area_final["Color"] = area_final["Type"].map(colors)

        # Create the plot
        fig, ax = plt.subplots(1, 1)
        bars = ax.bar(
            area_final["Type"],
            area_final["Area"],
            color=area_final["Color"]
        )
        # Customize the plot
        plt.xticks(rotation=15, ha='right') 
        ax.set_ylabel(f'Area ({unit})', fontsize=14, fontweight='bold') 
        ax.set_xlabel('Control Stage', fontsize=14, fontweight='bold')
        ax.set_title(f'{unit} of fire within {state} by control stage')
        ax.set_ylim(0, rounded_upper_limit)

        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))

        for bar, area in zip(bars, area_final["Area"]):
            # Calculate y position for the annotation text
            text_y = bar.get_height() + 0.02 * rounded_upper_limit  
            text_y = min(text_y, rounded_upper_limit)  
            ax.text(
                bar.get_x() + bar.get_width() / 2, # x-position 
                text_y, # y-position 
                f'{area:,.0f} {unit}',  
                ha='center',  
                va='bottom',  
                fontsize=10  
            )
        # Display the plot
        plt.tight_layout()
        stats = st.sidebar.pyplot(fig, use_container_width=True)


    # # # M A P # # #
    # # # Finish layers for Map # # #
    wildfire_gdf = gpd.GeoDataFrame(wildfire_sdf, geometry='SHAPE')
    wildfire_gdf['Start_Date'] = wildfire_gdf['FireDiscoveryDateTime'].dt.strftime('%Y-%m-%d')
    wildfire_gdf = wildfire_gdf.drop(columns=['FireDiscoveryDateTime'])
    selected_state_gdf = state_gdf[state_gdf['State'] == state]
   
    def get_marker_size(daily_acres):
        if daily_acres < 1000:
            return 6
        elif daily_acres < 10000:
            return 9
        elif daily_acres < 50000:
            return 14
        elif daily_acres < 300000:
            return 19
        else:
            return 24
    wildfire_gdf['DailyAcres'] = wildfire_gdf['DailyAcres'].fillna(0)
    wildfire_gdf['marker_size'] = wildfire_gdf['DailyAcres'].apply(get_marker_size)


    # Ensure geometries are Point types
    wildfire_gdf['latitude'] = wildfire_gdf.geometry.y
    wildfire_gdf['longitude'] = wildfire_gdf.geometry.x

    # Create Map
    zoom = 6
    if state == 'Alaska':
        zoom = 4 
    elif state == 'Texas':
        zoom = 4.7
    centroid = selected_state_gdf.geometry.centroid.iloc[0]
    map = folium.Map(location=[centroid.y, centroid.x], zoom_start=zoom)
    folium.TileLayer(f'{basemap_selection}').add_to(map)
    # Add the state GeoDataFrame
    folium.GeoJson(
        state_gdf,
        name="State",  # Layer name for toggle
        style_function=lambda x: {
            'color': '#B2BEB5',  # Border color
            'fillColor': '#B2BEB5',  # Fill color
            'fillOpacity': 0.3,
            'weight': 0.5
        },
        tooltip=folium.GeoJsonTooltip(fields=["State"], aliases=["State:"]),
    ).add_to(map)
    folium.GeoJson(
    selected_state_gdf,
    name="Selected State",
    style_function=lambda x: {
        'color': 'black',  # Border color
        'fillColor': '#B2BEB5',  # Fill color for selected state
        'fillOpacity': 0.2,
        'weight': 2.5
    },
    tooltip=folium.GeoJsonTooltip(fields=["State"], aliases=["State:"]),
    ).add_to(map) 

    
    # Path to your fire icon image
    fire_icon_path = "https://github.com/zkasson/Portfolio/blob/main/Fire2.png?raw=true"

    # Add Wildfires
    for _, row in wildfire_gdf.iterrows():
        # Dynamically set the icon size based on marker_size
        fire_icon = folium.CustomIcon(
            fire_icon_path,
            icon_size=(row['marker_size'] * 2, row['marker_size'] * 2)  # Scale size dynamically
        )

        folium.Marker(
            location=(row['latitude'], row['longitude']),
            icon=fire_icon,  # Custom fire icon with dynamic size
            tooltip=f"Acres: {row['DailyAcres']}"
        ).add_to(map)
    # Render the map in Streamlit
    st.components.v1.html(map._repr_html_(), height=600)








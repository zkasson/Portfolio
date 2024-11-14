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



import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import leafmap.foliumap as leafmap
import arcgis
import gssapi
gis = GIS()

# Set up 
st.set_page_config(page_title='Dashboard', layout='wide')
st.title('Canadian Wildfire Dashboard')
st.sidebar.title('About')
st.sidebar.info('Explore Active Wildfire in Canada')





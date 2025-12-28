# основной макет courtesy to opus 4.5
# с кучей ручных доработок логики вызова и хранения всякого

import streamlit as st
import pandas as pd
import numpy as np
import time
from typing import Optional
from streamlit_plotly_events import plotly_events

from utils.data_processing import augment_df, get_city_season_stats
from utils.weather_api import (
    set_api_key,
    validate_api_key, 
    ensure_city_coordinates,
    get_current_temp_and_season,
    is_temp_outlier_for_city_season,
    is_temp_outlier_for_city_season_with_stats
)
from utils.plotting import create_city_plot, create_season_comparison_chart, create_city_map, create_city_map_mapbox

# ═══════════════════════════════════════════════════════
# Page Configuration
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="Weather Analysis App",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════
# Session State Initialization
# ═══════════════════════════════════════════════════════
if 'df' not in st.session_state:
    st.session_state.df = None
if 'df_augmented' not in st.session_state:
    st.session_state.df_augmented = None
if 'api_key_valid' not in st.session_state:
    st.session_state.api_key_valid = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

if 'city_coordinates' not in st.session_state:
    st.session_state.city_coordinates = {}
if 'selected_city' not in st.session_state:
    st.session_state.selected_city = None
if 'geocoding_complete' not in st.session_state:
    st.session_state.geocoding_complete = False

# ═══════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════
def load_file(uploaded_file) -> Optional[pd.DataFrame]:
    """Load uploaded file into DataFrame"""
    try:
        file_name = uploaded_file.name.lower()
        
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        elif file_name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV, JSON, or XLSX.")
            return None
        
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """Validate that DataFrame has required columns"""
    required_columns = ['city', 'temperature', 'season']
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        return False, f"Missing required columns: {', '.join(missing)}"
    
    # Check for date column (either 'date' or 'timestamp')
    if 'date' not in df.columns and 'timestamp' not in df.columns:
        return False, "Missing date column ('date' or 'timestamp')"
    
    return True, "Valid"

def geocode_all_cities(cities, api_key):
    """Geocode all cities, with progress indicator"""
    
    cities_found_in_cache = []
    cities_that_need_api = []
    cities_to_coords = ensure_city_coordinates(cities)
    for city, coord in cities_to_coords.items():
        if coord is None:
            cities_that_need_api.append(city)
        else:
            cities_found_in_cache.append(city)

    if len(cities_that_need_api) > 0:
        st.warning(
            f"⚠️ {len(cities_that_need_api)}{len(cities)} cities need geocoding but couldn't be filled with API. "
            f"Using cached coordinates: {len(cities_found_in_cache)}/{len(cities)} cities found in cache. "
        )

    return cities_to_coords

def handle_map_click(selected_points: list, cities_in_order: list) -> Optional[str]:
    """Extract city name from plotly click event"""
    if not selected_points:
        return None
    
    point = selected_points[0]
    
    st.write("Click event data:", point)

    # Try different ways to get the city name
    # if 'text' in point:
    #     return point['text']
    # elif 'customdata' in point:
    #     return point['customdata']
    # elif 'pointIndex' in point and point['pointIndex'] < len(cities):
    #     return cities[point['pointIndex']]
    
    point_idx = point.get('pointNumber', point.get('pointIndex'))
    
    if point_idx is not None and 0 <= point_idx < len(cities_in_order):
        return cities_in_order[point_idx]
    
    return None

# ═══════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════
def main():
    st.title("🌡️ Weather Temperature Analysis")
    st.markdown("---")
    
    # ───────────────────────────────────────────────────
    # Sidebar - File Upload & Configuration
    # ───────────────────────────────────────────────────
    with st.sidebar:
        st.header("📁 Data Upload")
        
        uploaded_file = st.file_uploader(
            "Upload temperature data",
            type=['csv', 'json', 'xlsx', 'xls'],
            help="Upload a file with columns: city, date, temperature, season"
        )
        
        if uploaded_file is not None:
            start_time = time.time()
            
            with st.spinner("Loading data..."):
                df = load_file(uploaded_file)
            
            if df is not None:
                # Validate
                is_valid, message = validate_dataframe(df)
                
                if not is_valid:
                    st.error(f"❌ {message}")
                else:
                    # Augment data
                    with st.spinner("Processing data..."):
                        df_augmented = augment_df(df)
                    
                    elapsed_time = time.time() - start_time
                    
                    # Store in session state
                    st.session_state.df = df
                    st.session_state.df_augmented = df_augmented
                    
                    # Success message
                    n_rows = len(df)
                    n_cities = df['city'].nunique()
                    n_seasons = df['season'].nunique()
                    
                    st.success(
                        f"✅ Loaded **{n_rows:,}** records with "
                        f"**{n_cities}** cities and **{n_seasons}** seasons "
                        f"in **{elapsed_time:.2f}** seconds"
                    )
        
        st.markdown("---")
        
        # API Key Input
        st.header("🔑 API Configuration")
        
        api_key = st.text_input(
            "OpenWeatherMap API Key",
            type="password",
            value=st.session_state.api_key,
            help="Get your API key from https://openweathermap.org/api"
        )
        
        if api_key:
            if api_key != st.session_state.api_key:
                # New key entered, validate it
                with st.spinner("Validating API key..."):
                    is_valid, message = validate_api_key(api_key)
                
                st.session_state.api_key = api_key
                st.session_state.api_key_valid = is_valid
                set_api_key(api_key)
                
                if is_valid:
                    st.success("✅ API key is valid")
                    # Trigger re-geocoding if needed
                    st.session_state.geocoding_complete = False
                else:
                    st.error(f"❌ {message}")
                
            else:
                # Same key, show cached status
                if st.session_state.api_key_valid:
                    st.success("✅ API key is valid")
                else:
                    st.error("❌ Invalid API key.")
            
    
    # ───────────────────────────────────────────────────
    # Main Content
    # ───────────────────────────────────────────────────
    if st.session_state.df_augmented is None:
        # No data loaded yet
        st.info("👈 Please upload a temperature data file to get started.")
        
        # Show expected format
        with st.expander("📋 Expected Data Format"):
            st.markdown("""
            Your file should contain the following columns:
            
            | Column | Type | Description |
            |--------|------|-------------|
            | `city` | string | City name |
            | `timestamp` | string/datetime | Date |
            | `temperature` | float | Temperature value |
            | `season` | string | Season (winter, spring, summer, autumn) |
            
            **Example:**
            ```
            city,date,temperature,season
            London,2023-01-15,5.2,winter
            London,2023-01-16,4.8,winter
            Paris,2023-01-15,6.1,winter
            ```
            """)
        return
    
    # Data is loaded
    df = st.session_state.df_augmented
    cities = sorted(df['city'].unique())
    
    if not st.session_state.geocoding_complete:
        with st.spinner("🌍 Getting city coordinates..."):
            api_key = st.session_state.api_key if st.session_state.api_key_valid else None
            city_coords = geocode_all_cities(cities, api_key)
            st.session_state.city_coordinates = city_coords
            st.session_state.geocoding_complete = True
            
            # Count successful geocodes
            successful = sum(1 for v in city_coords.values() if v is not None)
            if successful < len(cities):
                st.warning(f"⚠️ Could only geocode {successful}/{len(cities)} cities")

    # City selector
    st.header("🏙️ City Analysis")
    
    if st.session_state.selected_city is None or st.session_state.selected_city not in cities:
        st.session_state.selected_city = cities[0]

    cities_in_plot_order = [
        city for city, coords in st.session_state.city_coordinates.items()
        if coords is not None
    ]

    control_col, map_col = st.columns([2, 3])

    with control_col:
        st.subheader("📍 Select City")
        
        # Selectbox for city selection
        selected_city = st.selectbox(
            "Choose from list",
            options=cities,
            index=cities.index(st.session_state.selected_city) if st.session_state.selected_city in cities else 0,
            key="city_selectbox"
        )
        
        # Update session state if selectbox changed
        if selected_city != st.session_state.selected_city:
            st.session_state.selected_city = selected_city
            st.rerun()
        
        # Show city coordinates
        if st.session_state.city_coordinates.get(selected_city):
            coords = st.session_state.city_coordinates[selected_city]
            st.caption(f"📍 Lat: {coords['lat']:.4f}, Lon: {coords['lon']:.4f}")
        
        n_geocoded = len(cities_in_plot_order)
        n_total = len(cities)
        if n_geocoded < n_total:
            st.warning(f"⚠️ {n_total - n_geocoded} cities could not be geocoded")
    
    with map_col:
        # Create the map
        map_fig = create_city_map(
            st.session_state.city_coordinates, 
            st.session_state.selected_city
        )

        st.plotly_chart(map_fig, use_container_width=True, key="city_map_static")

        # Handle click events
        # Use streamlit-plotly-events for click handling
        # selected_points = plotly_events(
        #     map_fig,
        #     click_event=True,
        #     hover_event=False,
        #     select_event=False,
        #     override_height=450,
        #     key="city_map_events"
        # )

        # if selected_points:
        #     st.write("🔍 Debug - Click event:", selected_points)
        #     st.write("🔍 Debug - Cities order:", cities_in_plot_order)
        
        # if selected_points:
        #     clicked_city = handle_map_click(selected_points, cities_in_plot_order)
        #     st.write("🔍 Debug - Detected city:", clicked_city)

        #     if clicked_city and clicked_city != st.session_state.selected_city:
        #         st.session_state.selected_city = clicked_city
        #         st.rerun()
    
    selected_city = st.session_state.selected_city

    st.markdown("---")

    # ───────────────────────────────────────────────────
    # Current Weather Section
    # ───────────────────────────────────────────────────
    if st.session_state.api_key_valid:
        st.subheader("📡 Current Weather")
        
        col1, col2, col3 = st.columns(3)
        
        with st.spinner(f"Fetching current weather for {selected_city}..."):
            try:
                temp, season = get_current_temp_and_season(
                    selected_city, 
                    st.session_state.api_key
                )
            except:    
                st.warning(f"⚠️ Could not fetch current weather: {error}")

        if temp is not None:
            # Check if outlier
            is_outlier, stats = is_temp_outlier_for_city_season_with_stats(df, temp, selected_city, season)
            
            with col1:
                st.metric(
                    label="Current Temperature",
                    value=f"{temp:.1f}°C",
                    delta=f"{temp - stats.get('mean', temp):.1f}°C vs mean" if stats else None
                )
            
            with col2:
                st.metric(
                    label="Current Season",
                    value=season.capitalize() if season else "Unknown"
                )
            
            with col3:
                if is_outlier:
                    st.error("⚠️ **OUTLIER DETECTED**")
                    st.caption(
                        f"Outside normal range: "
                        f"{stats['lower_bound']:.1f}°C - {stats['upper_bound']:.1f}°C"
                    )
                else:
                    st.success("✅ **Normal**")
                    st.caption(
                        f"Within range: "
                        f"{stats['lower_bound']:.1f}°C - {stats['upper_bound']:.1f}°C"
                    )
    else:
        st.info("🔑 Enter a valid API key in the sidebar to see current weather data.")
    
    st.markdown("---")
    
    # ───────────────────────────────────────────────────
    # Season Statistics
    # ───────────────────────────────────────────────────
    st.subheader("📊 Season-wise Statistics")
    
    season_stats = get_city_season_stats(df, selected_city)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Stats table
        st.dataframe(
            season_stats.style.format({
                'mean_temp': '{:.1f}°C',
                'std_temp': '{:.2f}°C',
                'min_temp': '{:.1f}°C',
                'max_temp': '{:.1f}°C',
                'count': '{:,.0f}'
            }),
            use_container_width=True
        )
    
    with col2:
        # Box plot
        season_fig = create_season_comparison_chart(df, selected_city)
        st.plotly_chart(season_fig, use_container_width=True)
    
    st.markdown("---")
    
    # ───────────────────────────────────────────────────
    # Historical Data Plot
    # ───────────────────────────────────────────────────
    st.subheader("📈 Historical Temperature Data")
    
    # Plot options
    with st.expander("⚙️ Plot Options", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            show_temps = st.checkbox("Show raw temperatures", value=True)
        with col2:
            show_ma = st.checkbox("Show moving averages", value=True)
        with col3:
            show_outliers = st.checkbox("Show outliers", value=True)
        with col4:
            show_ribbon = st.checkbox("Show outlier ribbon", value=True)
    
    # Create and display plot
    fig = create_city_plot(df, selected_city)
    
    # Toggle traces based on options
    for trace in fig.data:
        if 'Actual' in trace.name and not show_temps:
            trace.visible = False
        if 'SMA' in trace.name and not show_ma:
            trace.visible = False
        if 'EMA' in trace.name and not show_ma:
            trace.visible = False
        if 'Outlier' in trace.name and not show_outliers:
            trace.visible = False
        if 'Range' in trace.name and not show_ribbon:
            trace.visible = False
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ───────────────────────────────────────────────────
    # Data Preview
    # ───────────────────────────────────────────────────
    with st.expander("🔍 View Raw Data"):
        city_data = df[df['city'] == selected_city]
        st.dataframe(city_data, use_container_width=True, height=300)
        
        # Download button
        csv = city_data.to_csv(index=False)
        st.download_button(
            label="📥 Download City Data as CSV",
            data=csv,
            file_name=f"{selected_city}_weather_data.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
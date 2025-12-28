# assisted by opus 4.5
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def create_city_plot(df, city):
    city_data = df[df['city'] == city].copy()
    
    # На всякий случай так
    x_col = 'date' if 'date' in city_data.columns else 'timestamp'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=city_data[x_col],
        y=city_data['temperature'],
        mode='lines',
        name='Actual Temperature',
        line=dict(color='lightblue', width=1),
        opacity=0.6,
        hovertemplate='%{x}<br>Temp: %{y:.1f}°C<extra></extra>'
    ))
    
    if 'city_season_temp_mean' in city_data.columns and 'city_season_temp_std' in city_data.columns:
        upper = city_data['city_season_temp_mean'] + 2 * city_data['city_season_temp_std']
        lower = city_data['city_season_temp_mean'] - 2 * city_data['city_season_temp_std']
        
        fig.add_trace(go.Scatter(
            x=city_data[x_col],
            y=upper,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            name='±2σ Range (upper)',
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=city_data[x_col],
            y=lower,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(0, 176, 80, 0.1)',
            name='±2σ Range (lower)',
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=city_data[x_col],
            y=city_data['city_season_temp_mean'],
            mode='lines',
            name='Season Mean',
            line=dict(color='green', width=2),
            hovertemplate='%{x}<br>Season Mean: %{y:.1f}°C<extra></extra>'
        ))
    
    if 'temperature_SMA' in city_data.columns:
        fig.add_trace(go.Scatter(
            x=city_data[x_col],
            y=city_data['temperature_SMA'],
            mode='lines',
            name='SMA (30)',
            line=dict(color='orange', width=1.5),
            hovertemplate='%{x}<br>SMA: %{y:.1f}°C<extra></extra>'
        ))
    
    if 'temperature_EMA' in city_data.columns:
        fig.add_trace(go.Scatter(
            x=city_data[x_col],
            y=city_data['temperature_EMA'],
            mode='lines',
            name='EMA (30)',
            line=dict(color='purple', width=1.5),
            hovertemplate='%{x}<br>EMA: %{y:.1f}°C<extra></extra>'
        ))
    
    if 'is_outlier_by_season' in city_data.columns:
        outliers = city_data[city_data['is_outlier_by_season']]
        fig.add_trace(go.Scatter(
            x=outliers[x_col],
            y=outliers['temperature'],
            mode='markers',
            name='Outliers (Season)',
            marker=dict(color='red', size=6, symbol='circle'),
            hovertemplate='%{x}<br>Temp: %{y:.1f}°C<br>OUTLIER (Season)<extra></extra>'
        ))
    
    if 'is_outlier_by_sma' in city_data.columns:
        outliers_sma = city_data[city_data['is_outlier_by_sma'] & ~city_data.get('is_outlier_by_season', False)]
        if len(outliers_sma) > 0:
            fig.add_trace(go.Scatter(
                x=outliers_sma[x_col],
                y=outliers_sma['temperature'],
                mode='markers',
                name='Outliers (SMA)',
                marker=dict(color='brown', size=4, symbol='diamond', opacity=0.4),
                hovertemplate='%{x}<br>Temp: %{y:.1f}°C<br>OUTLIER (SMA)<extra></extra>'
            ))
    
    if 'is_outlier_by_ema' in city_data.columns:
        outliers_ema = city_data[
            city_data['is_outlier_by_ema'] & 
            ~city_data.get('is_outlier_by_season', False) & 
            ~city_data.get('is_outlier_by_sma', False)
        ]
        if len(outliers_ema) > 0:
            fig.add_trace(go.Scatter(
                x=outliers_ema[x_col],
                y=outliers_ema['temperature'],
                mode='markers',
                name='Outliers (EMA)',
                marker=dict(color='purple', size=4, symbol='square', opacity=0.4),
                hovertemplate='%{x}<br>Temp: %{y:.1f}°C<br>OUTLIER (EMA)<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'Temperature Analysis: {city}',
        xaxis_title='Date',
        yaxis_title='Temperature (°C)',
        hovermode='x unified',
        # legend=dict(
        #     yanchor="top",
        #     y=0.99,
        #     xanchor="left",
        #     x=0.01,
        #     bgcolor='rgba(255, 255, 255, 0.8)'
        # ),
        template='plotly_white',
        height=500
    )
    
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ])
        )
    )
    
    return fig

# статистика по сезонам в выбранном городе
def create_season_comparison_chart(df, city):
    city_data = df[df['city'] == city]
    
    season_order = ['winter', 'spring', 'summer', 'autumn']
    colors = {'winter': '#636EFA', 'spring': '#00CC96', 'summer': '#FFA15A', 'autumn': '#AB63FA'}
    
    fig = go.Figure()
    
    for season in season_order:
        season_data = city_data[city_data['season'] == season]['temperature']
        if len(season_data) > 0:
            fig.add_trace(go.Box(
                y=season_data,
                name=season.capitalize(),
                marker_color=colors.get(season, 'gray'),
                boxmean=True
            ))
    
    fig.update_layout(
        title=f'Temperature Distribution by Season: {city}',
        yaxis_title='Temperature (°C)',
        template='plotly_white',
        height=400,
        showlegend=False
    )
    
    return fig

def create_city_map(city_coordinates: dict, selected_city: str = None):
    """
    Create an interactive world map with city markers.
    
    Args:
        city_coordinates: Dict mapping city names to {'lat': float, 'lon': float}
        selected_city: Currently selected city (highlighted differently)
    
    Returns:
        plotly.graph_objects.Figure
    """
    # Filter cities with valid coordinates
    valid_cities = [
        (city, coords) 
        for city, coords in city_coordinates.items() 
        if coords is not None
    ]
    
    if not valid_cities:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No cities with valid coordinates found",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=400)
        return fig
    
    cities = [c[0] for c in valid_cities]
    lats = [c[1]['lat'] for c in valid_cities]
    lons = [c[1]['lon'] for c in valid_cities]
    
    # Styling based on selection
    colors = []
    sizes = []
    for city in cities:
        if city == selected_city:
            colors.append('#FF4B4B')  # Streamlit red for selected
            sizes.append(18)
        else:
            colors.append('#1f77b4')  # Default blue
            sizes.append(12)
    
    fig = go.Figure()
    
    # Add city markers
    fig.add_trace(go.Scattergeo(
        lon=lons,
        lat=lats,
        text=cities,
        mode='markers+text',
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color='white'),
            symbol='circle',
            opacity=0.9
        ),
        textposition='top center',
        textfont=dict(
            size=11,
            color='#333333',
            family='Arial'
        ),
        customdata=cities,  # Store city names for click handling
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Latitude: %{lat:.2f}°<br>'
            'Longitude: %{lon:.2f}°<br>'
            '<extra></extra>'
        )
    ))
    
    # Layout configuration
    fig.update_layout(
        # title=dict(
        #     text='🌍 Click a City to Select',
        #     x=0.5,
        #     xanchor='center',
        #     font=dict(size=16)
        # ),
        geo=dict(
            showland=True,
            showcountries=True,
            showocean=True,
            showlakes=True,
            showrivers=False,
            countrywidth=0.5,
            landcolor='rgb(243, 243, 243)',
            oceancolor='rgb(204, 229, 255)',
            lakecolor='rgb(204, 229, 255)',
            countrycolor='rgb(180, 180, 180)',
            coastlinecolor='rgb(150, 150, 150)',
            projection_type='natural earth',
            showframe=False,
            bgcolor='rgba(0,0,0,0)'
        ),
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # Auto-zoom to fit all cities with some padding
    if len(lats) > 1:
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        # Only set center and scope if cities are somewhat clustered
        if lat_range < 90 and lon_range < 180:
            fig.update_geos(
                center=dict(
                    lat=sum(lats) / len(lats),
                    lon=sum(lons) / len(lons)
                ),
                projection_scale=1.5
            )
    
    return fig

def create_city_map_mapbox(city_coordinates: dict, selected_city: str = None, mapbox_style: str = "open-street-map"):
    """
    Alternative map using Mapbox/OpenStreetMap tiles (more detailed).
    No API key needed for open-street-map style.
    
    Args:
        city_coordinates: Dict mapping city names to {'lat': float, 'lon': float}
        selected_city: Currently selected city
        mapbox_style: Map style ('open-street-map', 'carto-positron', 'carto-darkmatter')
    """
    valid_cities = [
        (city, coords) 
        for city, coords in city_coordinates.items() 
        if coords is not None
    ]
    
    if not valid_cities:
        fig = go.Figure()
        fig.add_annotation(
            text="No cities with valid coordinates found",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False
        )
        return fig
    
    cities = [c[0] for c in valid_cities]
    lats = [c[1]['lat'] for c in valid_cities]
    lons = [c[1]['lon'] for c in valid_cities]
    
    colors = ['#FF4B4B' if city == selected_city else '#1f77b4' for city in cities]
    sizes = [20 if city == selected_city else 14 for city in cities]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scattermapbox(
        lon=lons,
        lat=lats,
        text=cities,
        mode='markers+text',
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.9
        ),
        textposition='top center',
        textfont=dict(size=11, color='#333'),
        customdata=cities,
        hovertemplate=(
            '<b>%{text}</b><br>'
            'Lat: %{lat:.2f}° | Lon: %{lon:.2f}°'
            '<extra></extra>'
        )
    ))
    
    # Calculate center and zoom
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    fig.update_layout(
        # title=dict(
        #     text='🌍 Click a City to Select',
        #     x=0.5,
        #     xanchor='center'
        # ),
        mapbox=dict(
            style=mapbox_style,
            center=dict(lat=center_lat, lon=center_lon),
            zoom=1.5 if len(cities) > 5 else 3
        ),
        height=450,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig
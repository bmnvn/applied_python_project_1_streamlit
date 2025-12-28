import pandas as pd
import numpy as np

SMA_WINDOW = 30
EMA_SPAN = 30

def augment_df(df):
    df = df.copy()
    
    # Скользящие средние
    df['temperature_SMA'] = (
        df.groupby('city')['temperature']
        .transform(lambda x: x.rolling(window=SMA_WINDOW, min_periods=1).mean())
    )
    df['temperature_EMA'] = (
        df.groupby('city')['temperature']
        .transform(lambda x: x.ewm(span=EMA_SPAN, adjust=False, min_periods=1).mean())
    )

    # Средняя температура и стандартное отклонение по городу+сезону
    df['city_season_temp_mean'] = df.groupby(['city', 'season'])['temperature'].transform('mean')
    df['city_season_temp_std'] = df.groupby(['city', 'season'])['temperature'].transform('std')

    # Аномалии
    df['is_outlier_by_season'] = (
        (df['temperature'] - df['city_season_temp_mean']).abs() > 2 * df['city_season_temp_std']
    )
    df['is_outlier_by_sma'] = (
        (df['temperature'] - df['temperature_SMA']).abs() > 2 * df['city_season_temp_std']
    )
    df['is_outlier_by_ema'] = (
        (df['temperature'] - df['temperature_EMA']).abs() > 2 * df['city_season_temp_std']
    )

    return df

def get_city_season_mean_and_std(df, city, season):
    filtered = df.loc[
        (df['city'] == city) & (df['season'] == season),
        ['city_season_temp_mean', 'city_season_temp_std']
    ]
    if len(filtered) > 0:
        return filtered.iloc[0]
    return None

def get_city_season_stats(df, city):
    city_data = df[df['city'] == city]
    
    stats = city_data.groupby('season').agg(
        mean_temp=('temperature', 'mean'),
        std_temp=('temperature', 'std'),
        min_temp=('temperature', 'min'),
        max_temp=('temperature', 'max'),
        count=('temperature', 'count')
    ).round(2)
    
    # Reorder seasons
    season_order = ['winter', 'spring', 'summer', 'autumn']
    stats = stats.reindex([s for s in season_order if s in stats.index])
    
    return stats
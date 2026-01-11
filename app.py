import streamlit as st
import pandas as pd
import numpy as np
import requests
import httpx
import asyncio
import plotly.graph_objects as go
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor


# Реальные средние температуры (примерные данные) для городов по сезонам
seasonal_temperatures = {
    "New York": {"winter": 0, "spring": 10, "summer": 25, "autumn": 15},
    "London": {"winter": 5, "spring": 11, "summer": 18, "autumn": 12},
    "Paris": {"winter": 4, "spring": 12, "summer": 20, "autumn": 13},
    "Tokyo": {"winter": 6, "spring": 15, "summer": 27, "autumn": 18},
    "Moscow": {"winter": -10, "spring": 5, "summer": 18, "autumn": 8},
    "Sydney": {"winter": 12, "spring": 18, "summer": 25, "autumn": 20},
    "Berlin": {"winter": 0, "spring": 10, "summer": 20, "autumn": 11},
    "Beijing": {"winter": -2, "spring": 13, "summer": 27, "autumn": 16},
    "Rio de Janeiro": {"winter": 20, "spring": 25, "summer": 30, "autumn": 25},
    "Dubai": {"winter": 20, "spring": 30, "summer": 40, "autumn": 30},
    "Los Angeles": {"winter": 15, "spring": 18, "summer": 25, "autumn": 20},
    "Singapore": {"winter": 27, "spring": 28, "summer": 28, "autumn": 27},
    "Mumbai": {"winter": 25, "spring": 30, "summer": 35, "autumn": 30},
    "Cairo": {"winter": 15, "spring": 25, "summer": 35, "autumn": 25},
    "Mexico City": {"winter": 12, "spring": 18, "summer": 20, "autumn": 15},
}

# Сопоставление месяцев с сезонами
month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

# SMA расчет
def calculate_moving_average(time_series, window_size = 30) -> pd.Series:
    elements_in_window = time_series.rolling(window_size)
    return elements_in_window.mean()

st.header("Анализ температурных данных и мониторинг текущей температуры через OpenWeatherMap API")
uploaded_file = st.file_uploader("Реальные средние температуры (примерные данные) для городов по сезонам", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.write("Превью данных")
    st.dataframe(data)
else:
    st.write("Введите данные .csv")


if uploaded_file is not None:

    st.write("Выберите город для анализа")
    selected_city = st.selectbox("Выберите город", [city for city in list(data['city'].unique())])

marker = uploaded_file is not None 
# Ввод API_KEY
if marker :
    API_KEY = st.text_input(
    	label="# :red[Введите свой API_KEY]:",
    	value="",
    	placeholder="Ваш API_KEY...",
    	help="Здесь можно ввести любое значение"
    )



    url = f"http://api.openweathermap.org/data/2.5/weather?q={selected_city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    
    if len(API_KEY) != 0:
        st.success("API_KEY введен!")
        if response.status_code == 200:
            weather_data = response.json()
            st.write(f"#### Погода в {selected_city} :umbrella: : {weather_data['main']['temp']}°C")
        else:
            error_data = response.json()  
            st.error(f"Ошибка {error_data['cod']}: {error_data['message']}")
    else:
        st.warning("Пожалуйста, введите API_KEY")
    marker = marker & (len(API_KEY) != 0) 
    marker = marker & (response.status_code == 200)

if marker:
    st.write("## Анализ временного ряда температуры для выбранного города")

#Запрос температуры для многопоточного выполнения 
def get_temperature_by_city(city, api_key = API_KEY):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}
    

def get_season():
    now = datetime.now()
    month = now.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:  # 9, 10, 11
        return "autumn"

# Определение выхода текущей температуры за пределы допустимых границ
if marker:
    data['mean_for_season'] = data.groupby(['city', 'season'])['temperature'].transform('mean')
    data['std_for_season'] = data.groupby(['city', 'season'])['temperature'].transform('std')
    data['is_anomal'] = (data['temperature'] > data['mean_for_season'] + 2*data['std_for_season']) | (data['temperature'] < data['mean_for_season'] - 2*data['std_for_season'])
    current_season = get_season()
    st.write(f" #### Текущее время года: :blue-background[{current_season}]")
    std_city_value = data[(data['city'] == selected_city) & (data['season'] == current_season)]['std_for_season'].iloc[1]
    mean_city_value = data[(data['city'] == selected_city) & (data['season'] == current_season)]['mean_for_season'].iloc[1]
    upper_temperature_bound = mean_city_value + 2*std_city_value
    lower_temperature_bound = mean_city_value - 2*std_city_value
    temp_table = {f'Верхняя граница температуры для {selected_city}, сезона {current_season}' : upper_temperature_bound,
f'Текущее значения для {selected_city}' : weather_data['main']['temp'],
f'Нижняя граница температуры для {selected_city}, сезона {current_season}' : lower_temperature_bound}
    st.table(temp_table) 
    
    if ((weather_data['main']['temp'] > upper_temperature_bound) |  (weather_data['main']['temp'] < lower_temperature_bound)):
        st.error(f"Текущая температура {selected_city}: аномальная.")
    else:
        st.success(f"Текущая температура {selected_city}: в норме.")


if marker:
    if st.button("Показать текущие температуры всех городов, входящих в csv файл. Multithread processing"):
        
        current_temps = {}
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(get_temperature_by_city, list(data['city'].unique()) ))

        elapsed_time = time.time() - start_time     
        citi_names = [name['name'] for name in results]
        temperature_values = [res['main']['temp'] for res in results]
        current_temps = dict(zip(citi_names, temperature_values))
        st.bar_chart(current_temps)
        elapsed_time = time.time() - start_time
        st.write(f"Время выполнения. Multithreading processing: {elapsed_time:.2f} секунд")


async def fetch_temps_by_city(city, client, api_key = API_KEY):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = await client.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}

async def fetch_all_cities(cities, api_key):
    async with httpx.AsyncClient() as client:
        tasks = [fetch_temps_by_city(city, client, api_key) for city in cities]
        return await asyncio.gather(*tasks)

if marker:
    if st.button("Показать текущие температуры всех городов, входящих в csv файл. Async processing"):
        start_time = time.time()  
        
        # Получаем список городов
        cities = list(data['city'].unique())
        
        # Запускаем асинхронную функцию
        results = asyncio.run(fetch_all_cities(cities, API_KEY))
        
        # Обрабатываем результаты
        valid_results = [r for r in results if 'error' not in r]
        if valid_results:
            citi_names = [name['name'] for name in valid_results]
            temperature_values = [res['main']['temp'] for res in valid_results]
            current_temps = dict(zip(citi_names, temperature_values))
            st.bar_chart(current_temps)
            
            elapsed_time = time.time() - start_time
            st.write(f"Время выполнения. Async processing: {elapsed_time:.2f} секунд")
        else:
            st.error("Не удалось получить данные о температурах") 
  
      

if marker:
    st.write("## Расчет скользящего среднего для заданного города в ретроспективе")
# вывод графиков временного ряда температуры городов
if marker:
    if st.checkbox(f"Отобразить графики временного ряда температуры и скользящего среднего для города {selected_city}"):
    
        sma = calculate_moving_average(data[data['city'] == selected_city]['temperature'])
        st.write("Ретроспектива температуры для выбранного города")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=data[data['city'] == selected_city]['timestamp'], y=data[data['city'] == selected_city]['temperature'], name=f"Temperature of {selected_city}")
        )

        fig.add_trace(
            go.Scatter(x=data[data['city'] == selected_city]['timestamp'], y=sma, name=f"Скользящее среднее SMA {selected_city}")
        )

        fig.update_layout(
            title=f"{selected_city} температура",
            xaxis_title="Дата",
            yaxis_title="Значение ряда",
        )
    
        st.plotly_chart(fig)

temperature_pairs = [
    ('#1f77b4', '#ff7f0e'),  # Синий - Оранжевый
    ('#2ca02c', '#d62728'),  # Зеленый - Красный
    ('#9467bd', '#8c564b'),  # Фиолетовый - Коричневый
    ('#e377c2', '#7f7f7f'),  # Розовый - Серый
    ('#17becf', '#bcbd22'),  # Бирюзовый - Оливковый
    ('#393b79', '#ff9896'),  # Темно-синий - Светло-красный
    ('#6b6ecf', '#9c9ede'),  # Пурпурный - Светло-пурпурный
    ('#b5cf6b', '#cedb9c'),  # Зелено-желтый - Светло-зеленый
    ('#8c6d31', '#bd9e39'),  # Коричневый - Золотой
    ('#843c39', '#ad494a'),  # Темно-красный - Красный
]

if marker:
    st.write("## Аномалии в ретроспективе")

#Графики (ретроспектива) температуры, с выявлением аномалий и нормы по городам. 1. Последовательный вывод графика
if marker:    
    cities_for_plot = st.multiselect("Выберите города для отображения аномалий на графике", [col for col in list(data['city'].unique())])
    figc = go.Figure()
    for i, city in enumerate(cities_for_plot):
        normal_data = data[data['is_anomal'] == False]
        anomal_data = data[data['is_anomal'] == True]

        normal_color, anomal_color = temperature_pairs[i % len(temperature_pairs)]
        # Разделяем данные на нормальные и аномальные

        # Создаем график
    
    
        # Нормальные точки (синий)
        figc.add_trace(go.Scatter(
            x=normal_data['timestamp'],
            y=normal_data[normal_data['city'] == city]['temperature'],
            mode='lines+markers',
            name=f'Нормальные значения {city}',
            line=dict(color=normal_color, width=1),
            marker=dict(size=4)
         ))

    # Аномальные точки (красный)
        figc.add_trace(go.Scatter(
            x=anomal_data['timestamp'],
            y=anomal_data[anomal_data['city'] == city]['temperature'],
            mode='markers',
            name=f'Аномалии {city}',
            line=dict(color=anomal_color, width=2),
            marker=dict(size = 8)
        ))

        figc.update_layout(
            title='Температура с выделением аномалий',
            xaxis_title='Дата',
            yaxis_title='Температура',
            hovermode='x unified'
        )
    if len(cities_for_plot) != 0:
        st.plotly_chart(figc)


#Вывод:
st.write("####  Выводы")
st.write("1. Единственный процесс, который я посчитал подходящим для распараллеливания - получение температур для отображения графиков температур для всех городов, входящих в загруженный uploaded_file. Пользовался двумя подходами - многопоточное выполнение синхронных методов, асинхронные запросы с асинхронными библиотеками. В данном случае результаты для асинхронного подхода лучше, чем для многопоточного, поскольку задача I/O-bounded, а такие задачи ограничиваются временем отлкика интеграции, а не вычислительными способностями. хотя данных не так и много, и запросы осуществляются к одному и тому же ресурсу, поэтому видимость разницы между подходами не так существенна.



    
       


	
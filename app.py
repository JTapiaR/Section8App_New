import streamlit as st
import pandas as pd
import pydeck as pdk
from dotenv import load_dotenv

# Configuración de la página debe ser la primera llamada de Streamlit
st.set_page_config(
    page_title="Section-8 Properties Map",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Agregar un logo en el encabezado del dashboard
logo_url = "Analíticalogo.png"  # Reemplaza con la ruta de tu logo
st.image(logo_url, width=400)

# Título visible en la aplicación
st.title(":blue[Section 8 Properties Analysis]")
st.divider()

# Título general del dashboard
st.subheader("This tool contains the mapping and relevant information of properties available for sale, and highlights the information of those properties for which an estimated rent less than or equal to the Section 8 FRM.")
st.divider()

# Función para cargar datos
@st.cache_data
def load_data():
    df = pd.read_csv('Datos/Data_Final2VF.csv')
    #df = pd.read_parquet('Datos/Data_Final2.parquet')
    df['yearBuilt'] = df['yearBuilt'].astype(str)
    df['zpid'] = df['zpid'].astype(str)
    df['price_sq_foot'] = df['price_sq_foot'].apply(lambda d: f'{round(d, 2):,}')
    df['sizediff'] = df['FRM'] - df['rent_estimate']
    df['sizediff'] = df['sizediff'].apply(lambda d: f'{round(d, 2):,}')  # Crear la columna sizediff
    return df

@st.cache_data
def get_filtered_data(state, counties):
    df = load_data()
    if state:
        df = df[df['state'] == state]
    if counties:
        df = df[df['County'].isin(counties)]
    return df

# Cargar los datos completos
df = load_data()

# Filtrar por estado
states = df['state'].unique()
selected_state = st.selectbox('Select a State', states)

# Filtrar por condados
filtered_df_state = get_filtered_data(selected_state, None)
counties = filtered_df_state['County'].unique()
selected_counties = st.multiselect('Select one or more counties click in the desired name', counties)

# Crear tarjetas y mapas para cada condado seleccionado
if selected_counties:
    for county in selected_counties:
        county_df = get_filtered_data(selected_state, [county])

        # Añadir columna de colores basada en la columna Section_8
        county_df['color'] = county_df['Section_8'].apply(lambda x: [0, 255, 0, 160] if x == 1 else [255, 0, 0, 160])

        # Obtener valores únicos de 'bedrooms' y 'homeType'
        bedrooms = county_df['bedrooms'].unique()
        bedrooms = sorted(bedrooms)
        bedrooms.insert(0, 'All')  # Agregar la opción 'All' al principio

        home_types = county_df['homeType'].unique()
        home_types = sorted(home_types)
        home_types.insert(0, 'All')  # Agregar la opción 'All' al principio

        st.write(f"## {county} County")

        # Control de selección de número de cuartos
        selected_bedrooms = st.radio(f'Select Bedrooms for {county}', bedrooms, index=0, key=f'bedrooms_{county}', horizontal=True)

        # Control de selección de tipo de vivienda
        selected_home_types = st.radio(f'Select Home Types for {county}', home_types, index=0, key=f'hometypes_{county}', horizontal=True)

        # Aplicar filtros
        filtered_county_df = county_df.copy()
        if selected_bedrooms != 'All':
            filtered_county_df = filtered_county_df[filtered_county_df['bedrooms'] == selected_bedrooms]
        if selected_home_types != 'All':
            filtered_county_df = filtered_county_df[filtered_county_df['homeType'] == selected_home_types]

        # Verificar que hay datos en el DataFrame filtrado
        if filtered_county_df.empty:
            st.warning(f"No data available for {county} County with the selected filters.")
            continue

        # Actualizar las métricas
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Total Section 8 Properties", value=filtered_county_df[filtered_county_df['Section_8'] == 1].shape[0])
        with col2:
            st.metric(label="Total Non-Section 8 Properties", value=filtered_county_df[filtered_county_df['Section_8'] == 0].shape[0])

        # Crear el mapa interactivo con Pydeck centrado en el condado
        midpoint = (filtered_county_df['latitude'].mean(), filtered_county_df['longitude'].mean())

        # Control de visualización de propiedades
        display_options = st.radio(
            f"Select which properties to display for {county}",
            ("Both", "Section 8", "Non Section 8"),
            key=f'display_options_{county}',
            horizontal=True
        )

        # Filtrar según la opción seleccionada
        if display_options == "Section 8":
            display_df = filtered_county_df[filtered_county_df['Section_8'] == 1]
        elif display_options == "Non Section 8":
            display_df = filtered_county_df[filtered_county_df['Section_8'] == 0]
        else:
            display_df = filtered_county_df

        section_8_layer = pdk.Layer(
            "ScatterplotLayer",
            data=display_df[display_df['Section_8'] == 1],
            get_position='[longitude, latitude]',
            get_color='color',
            get_radius='sizediff / 5',  # Tamaño del marcador basado en sizediff
            pickable=True,
            auto_highlight=True,
        )

        non_section_8_layer = pdk.Layer(
            "ScatterplotLayer",
            data=display_df[display_df['Section_8'] == 0],
            get_position='[longitude, latitude]',
            get_color='color',
            get_radius=200,
            pickable=True,
            auto_highlight=True,
        )

        layers = []
        if display_options in ["Both", "Section 8"]:
            layers.append(section_8_layer)
        if display_options in ["Both", "Non Section 8"]:
            layers.append(non_section_8_layer)

        view_state = pdk.ViewState(
            latitude=midpoint[0],
            longitude=midpoint[1],
            zoom=10,
            pitch=50,
        )

        r = pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip={
                "text":"zpid: {zpid}\nPrice per Sq Foot: {price_sq_foot}\nURL: {detailUrl_InfoTOD}\nBedrooms: {bedrooms}\nSection 8: {Section_8}\nSpread FRM-RentEstimated: {sizediff}"
            }
        )

        # Mostrar el mapa en Streamlit
        st.pydeck_chart(r, use_container_width=True)
                # Leyenda para los colores
        st.markdown("""
        <div style='background-color: black; color: white; padding: 5px; border-radius: 5px; display: inline-block;'>
            <strong>Legend:</strong> <span style='color: green;'>● Section 8</span>  <strong> The size of the green dot means difference between FRM and Rent Estimated>
            <span style='color: red;'>● Non Section 8</span>   
        </div>
        """, unsafe_allow_html=True)

        # Mostrar información adicional al hacer clic en un punto
        #selected_point = st.selectbox("Select a property point", display_df.index, format_func=lambda x: f"Property {x}")
        selected_zpid = st.selectbox("Select a property ZPID", display_df['zpid'].unique())

        if selected_zpid is not None:
            selected_data = display_df[display_df['zpid'] == selected_zpid].iloc[0]
            st.markdown(f"""
            <div style='background-color: DarkGreen; padding: 10px; border-radius: 5px;'>
                <strong>Price per Sq Foot:</strong> {selected_data['price_sq_foot']}<br>
                <strong>Bedrooms:</strong> {selected_data['bedrooms']}<br>
                <strong>Section 8:</strong> {'Yes' if selected_data['Section_8'] == 1 else 'No'}<br>
                <strong>Spread FRM-RentEstimated:</strong> {selected_data['sizediff']}<br>
                <strong><a href='{selected_data['detailUrl_InfoTOD']}' target='_blank'>More Details</a></strong>
            </div>
            """, unsafe_allow_html=True)

        section_8_properties = filtered_county_df[filtered_county_df['Section_8'] == 1]

        # Mostrar tabla con propiedades Section 8
        st.write("### Section 8 Properties")
        st.dataframe(section_8_properties[[
            "sizediff",
            "zpid",
            "parcelId",
            "detailUrl_InfoTOD",
            "FRM",
            "rent_estimate",
            "price",
            "livingArea",
            "price_sq_foot",
            "bedrooms",
            "yearBuilt",
            "lastSoldPrice",
            "price_to_rent_ratio_InfoTOD",
            "MeanPricesnearbyHomes",
            "SCHOOLSMeandistance",
            "homeType",
            "description"
        ]].rename(columns={
            "sizediff": "Spread_FRM-RentEstimated",
            "zpid": "Zpid",
            "parcelId": "ParcelId",
            "detailUrl_InfoTOD": "URL",
            "FRM": "Fair_Rent_Market",
            "rent_estimate": "Rent_Estimate",
            "price": "Price",
            "livingArea": "Living_Area",
            "price_sq_foot": "Price_sq_foot",
            "bedrooms": "No._Bedrooms",
            "yearBuilt": "Year_Built",
            "lastSoldPrice": "Last_Sold_Price",
            "price_to_rent_ratio_InfoTOD": "Price_to_Rent_Ratio",
            "MeanPricesnearbyHomes": "MeanPrices_NearbyHomes",
            "SCHOOLSMeandistance": "Mean_Distance_NearSchools",
            "homeType": "Home_type",
            "description": "Description"
        }), use_container_width=True)
else:
    st.write("Please select at least one county to view the data.")





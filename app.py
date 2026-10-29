import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import json
import os

st.set_page_config(page_title="SQL Faker", layout="wide")
st.title("👤 Fake User Generator (Faker in SQL)")

if 'batch' not in st.session_state:
    st.session_state.batch = 1

col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1:
    locale = st.selectbox("Locale", ["en_US", "de_DE"])
with col2:
    seed = st.number_input("Seed", value=42, step=1)
with col3:
    st.write("") # Spacer
    if st.button("🔄 Reset & Generate"):
        st.session_state.batch = 1
with col4:
    st.write("") # Spacer
    if st.button("⏭️ Next Batch"):
        st.session_state.batch += 1

st.info(f"Currently generating **Batch #{st.session_state.batch}**")

@st.cache_resource
def init_connection():
    db_url = st.secrets["postgres"]["DB_URL"]
    return psycopg2.connect(db_url)

conn = init_connection()

with st.spinner("Generating users in SQL..."):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM generate_batch(%s, %s, %s, 10)", (int(seed), st.session_state.batch, locale))
    raw_data = cur.fetchall()
    cur.close()

if raw_data:
    parsed_data = [json.loads(row['generate_batch']) for row in raw_data]
    
    for row in parsed_data:
        coords = row.pop('Coordinates')
        row['Lat'] = round(coords['lat'], 4)
        row['Lon'] = round(coords['lon'], 4)

    df = pd.DataFrame(parsed_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.error("No data returned. Check database connection.")
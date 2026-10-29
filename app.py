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

def _mask_url(url: str) -> str:
    # Hide the password but keep user/host/port/db visible for debugging
    try:
        from urllib.parse import urlsplit
        u = urlsplit(url)
        user = u.username or ""
        host = u.hostname or ""
        port = f":{u.port}" if u.port else ""
        return f"{u.scheme}://{user}:****@{host}{port}{u.path}"
    except Exception:
        return "<could not parse DB_URL>"


@st.cache_resource
def init_connection():
    db_url = st.secrets["postgres"]["DB_URL"].strip()
    kwargs = {"connect_timeout": 10}
    if "sslmode=" not in db_url:
        kwargs["sslmode"] = "require"  # cloud Postgres (Supabase, Neon, Render...) needs SSL
    return psycopg2.connect(db_url, **kwargs)


def get_connection():
    try:
        conn = init_connection()
        if conn.closed:  # cached connection was dropped by the server
            init_connection.clear()
            conn = init_connection()
        return conn
    except psycopg2.OperationalError as e:
        init_connection.clear()  # don't cache the failure
        db_url = st.secrets["postgres"]["DB_URL"]
        st.error("Could not connect to the database.")
        st.code(f"DB_URL: {_mask_url(db_url)}\n\n{e}")
        st.stop()


conn = get_connection()

with st.spinner("Generating users in SQL..."):
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM generate_batch(%s, %s, %s, 10)", (int(seed), st.session_state.batch, locale))
            raw_data = cur.fetchall()
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        st.error("SQL error while generating users:")
        st.code(str(e))
        st.stop()

if raw_data:
    parsed_data = [json.loads(row['generate_batch']) for row in raw_data]
    
    for row in parsed_data:
        coords = row.pop('Coordinates')
        row['Lat'] = round(coords['lat'], 4)
        row['Lon'] = round(coords['lon'], 4)

    df = pd.DataFrame(parsed_data)
    st.dataframe(df, width="stretch", hide_index=True)
else:
    st.error("No data returned. Check database connection.")
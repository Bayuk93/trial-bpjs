import streamlit as st
import pandas as pd
from datetime import datetime
import os

# File untuk menyimpan data
PATIENTS_FILE = 'patients.csv'
CLAIMS_FILE = 'claims.csv'

# Fungsi untuk load/save data
def load_data(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# Load data awal
patients_df = load_data(PATIENTS_FILE, ['ID_Pasien', 'Nama', 'ID_BPJS', 'Batas_Budget'])
claims_df = load_data(CLAIMS_FILE, ['ID_Pasien', 'Tanggal', 'Biaya', 'Deskripsi'])

# Fungsi untuk menghitung total klaim per pasien
def calculate_totals(patients_df, claims_df):
    totals = claims_df.groupby('ID_Pasien')['Biaya'].sum().reset_index()
    totals.columns = ['ID_Pasien', 'Total_Klaim']
    merged = patients_df.merge(totals, on='ID_Pasien', how='left').fillna(0)
    merged['Sisa_Budget'] = merged['Batas_Budget'] - merged['Total_Klaim']
    merged['Status'] = merged.apply(lambda row: 
        'Over Budget' if row['Total_Klaim'] > row['Batas_Budget'] 
        else 'Warning' if row['Total_Klaim'] > 0.8 * row['Batas_Budget'] 
        else 'Aman', axis=1)
    return merged

# UI Streamlit
st.title("Sistem Pemantauan Klaim BPJS Kesehatan - Rawat Inap")
st.markdown("Aplikasi untuk memantau klaim agar tidak over budget.")

# Sidebar untuk navigasi
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Kelola Pasien", "Input Klaim", "Riwayat Klaim"])

if menu == "Dashboard":
    st.header("Dashboard Pemantauan")
    if patients_df.empty:
        st.warning("Belum ada data pasien. Tambahkan di menu 'Kelola Pasien'.")
    else:
        summary_df = calculate_totals(patients_df, claims_df)
        st.dataframe(summary_df[['Nama', 'ID_BPJS', 'Batas_Budget', 'Total_Klaim', 'Sisa_Budget', 'Status']])
        
        # Alert
        over_patients = summary_df[summary_df['Status'] == 'Over Budget']
        warning_patients = summary_df[summary_df['Status'] == 'Warning']
        if not over_patients.empty:
            st.error(f"Pasien Over Budget: {', '.join(over_patients['Nama'].tolist())}")
        if not warning_patients.empty:
            st.warning(f"Pasien Mendekati Budget: {', '.join(warning_patients['Nama'].tolist())}")
        
        # Chart sederhana
        st.subheader("Grafik Total Klaim vs Budget")
        chart_data = summary_df[['Nama', 'Total_Klaim', 'Batas_Budget']].set_index('Nama')
        st.bar_chart(chart_data)

elif menu == "Kelola Pasien":
    st.header("Kelola Data Pasien")
    with st.form("add_patient"):
        nama = st.text_input("Nama Pasien")
        id_bpjs = st.text_input("ID BPJS")
        batas_budget = st.number_input("Batas Budget (Rp)", min_value=0)
        submitted = st.form_submit_button("Tambah Pasien")
        if submitted and nama and id_bpjs:
            new_id = len(patients_df) + 1
            new_patient = pd.DataFrame([[new_id, nama, id_bpjs, batas_budget]], columns=patients_df.columns)
            patients_df = pd.concat([patients_df, new_patient], ignore_index=True)
            save_data(patients_df, PATIENTS_FILE)
            st.success("Pasien ditambahkan!")
    
    st.subheader("Daftar Pasien")
    st.dataframe(patients_df)

elif menu == "Input Klaim":
    st.header("Input Klaim Baru")
    if patients_df.empty:
        st.warning("Tambahkan pasien dulu.")
    else:
        patient_options = {row['Nama']: row['ID_Pasien'] for _, row in patients_df.iterrows()}
        selected_patient = st.selectbox("Pilih Pasien", list(patient_options.keys()))
        with st.form("add_claim"):
            tanggal = st.date_input("Tanggal Klaim", datetime.today())
            biaya = st.number_input("Biaya Klaim (Rp)", min_value=0)
            deskripsi = st.text_area("Deskripsi Klaim")
            submitted = st.form_submit_button("Tambah Klaim")
            if submitted:
                new_claim = pd.DataFrame([[patient_options[selected_patient], tanggal, biaya, deskripsi]], columns=claims_df.columns)
                claims_df = pd.concat([claims_df, new_claim], ignore_index=True)
                save_data(claims_df, CLAIMS_FILE)
                st.success("Klaim ditambahkan!")
                
                # Cek alert langsung
                summary_df = calculate_totals(patients_df, claims_df)
                patient_status = summary_df[summary_df['ID_Pasien'] == patient_options[selected_patient]]['Status'].iloc[0]
                if patient_status == 'Over Budget':
                    st.error("Peringatan: Klaim ini menyebabkan over budget!")
                elif patient_status == 'Warning':
                    st.warning("Peringatan: Klaim mendekati batas budget.")

elif menu == "Riwayat Klaim":
    st.header("Riwayat Klaim")
    if claims_df.empty:
        st.info("Belum ada klaim.")
    else:
        # Filter by pasien
        patient_options = {row['Nama']: row['ID_Pasien'] for _, row in patients_df.iterrows()}
        selected_patient = st.selectbox("Filter by Pasien", ["Semua"] + list(patient_options.keys()))
        if selected_patient != "Semua":
            filtered_claims = claims_df[claims_df['ID_Pasien'] == patient_options[selected_patient]]
        else:
            filtered_claims = claims_df
        st.dataframe(filtered_claims)
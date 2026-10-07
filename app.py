import streamlit as st
from auth import login_user, register_user
from db import get_connection
import pandas as pd
from PIL import Image
from ultralytics import YOLO
import os
import base64
import hashlib
import hmac
import time

SESSION_DURATION_SECONDS = 60 * 60 * 24 * 7
SESSION_SECRET = os.getenv("MBG_SESSION_SECRET", "mbg-nutrition-local-session-secret")


def create_session_token(user_id):
    """Membuat token sesi bertanda tangan yang valid selama tujuh hari."""
    payload = f"{user_id}:{int(time.time()) + SESSION_DURATION_SECONDS}".encode("utf-8")
    payload_encoded = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_encoded}.{signature}"


def get_user_from_session_token(token):
    """Memvalidasi token sesi dan memuat ulang akun pengguna dari database."""
    try:
        payload_encoded, signature = token.split(".", 1)
        expected_signature = hmac.new(
            SESSION_SECRET.encode("utf-8"),
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        padding = "=" * (-len(payload_encoded) % 4)
        user_id, expires_at = base64.urlsafe_b64decode(payload_encoded + padding).decode("utf-8").split(":", 1)
        if int(expires_at) < int(time.time()):
            return None

        conn = get_connection()
        if conn is None:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (int(user_id),))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except (ValueError, TypeError, UnicodeDecodeError):
        return None

def get_gizi(nama_makanan):

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM tkpi WHERE nama_makanan=%s",
        (nama_makanan,)
    )

    data = cursor.fetchone()

    cursor.close()
    conn.close()

    return data

def simpan_hasil(
    user_id,
    foto,
    energi,
    protein,
    lemak,
    karbo,
    serat
):

    conn = get_connection()

    cursor = conn.cursor()

    sql = """
    INSERT INTO hasil_deteksi
    (
        user_id,
        foto,
        energi_total,
        protein_total,
        lemak_total,
        karbo_total,
        serat_total
    )
    VALUES
    (%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(
        sql,
        (
            user_id,
            foto,
            energi,
            protein,
            lemak,
            karbo,
            serat
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

st.set_page_config(page_title="MBG Nutrition", layout="wide", page_icon="🍲")

st.markdown("""
<style>
    .stApp { background: #F8F9FA; color: #2C3E50; }
    [data-testid="stHeader"] { background: rgba(255, 255, 255, 0); }
    [data-testid="stAppViewBlockContainer"] { max-width: 1240px; padding-top: 2.5rem; }
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E8ECEF; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.6rem; }
    [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
        display: flex;
        flex-direction: column;
        min-height: calc(100vh - 2rem);
    }
    [data-testid="stSidebar"] div[data-testid="stButton"]:last-child { margin-top: auto; }
    [data-testid="stSidebar"] div[data-testid="stRadio"] label {
        border-radius: 9px;
        margin: 0.12rem 0;
        padding: 0.4rem 0.5rem;
        transition: background 0.2s ease;
    }
    [data-testid="stSidebar"] div[data-testid="stRadio"] label:hover { background: #EAF8F0; }
    .sidebar-profile {
        background: linear-gradient(135deg, #EAF8F0, #F8FDF9);
        border: 1px solid #CDEFD9;
        border-radius: 14px;
        margin-bottom: 0.65rem;
        padding: 1rem;
    }
    .sidebar-brand { color: #197A43; font-size: 0.78rem; font-weight: 750; letter-spacing: 0.07em; text-transform: uppercase; }
    .sidebar-name { color: #2C3E50; font-size: 1.08rem; font-weight: 750; margin: 0.35rem 0 0.15rem; }
    .sidebar-role { color: #6C7A89; font-size: 0.78rem; }
    .sidebar-nav-label { color: #95A5A6; font-size: 0.72rem; font-weight: 750; letter-spacing: 0.08em; margin-top: 0.5rem; text-transform: uppercase; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #E8ECEF;
        border-radius: 4px;
        box-shadow: none;
        padding: 1rem;
    }
    h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] { color: #2C3E50; }
    div[data-testid="stTextInput"] { width: 100%; }
    div[data-testid="stTextInput"] input {
        background: #FFFFFF;
        border: 1px solid #D5DBDB;
        border-radius: 10px;
        color: #2C3E50;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #2ECC71;
        box-shadow: 0 0 0 1px #2ECC71;
    }
    [data-testid="InputInstructions"] {
        display: none;
    }
    div[data-testid="stRadio"] { width: 100%; padding: 0.25rem 0 0.5rem; }
    div[data-testid="stButton"] > button {
        width: 100%;
        background: #E67E22;
        border: 1px solid #E67E22;
        border-radius: 10px;
        color: #FFFFFF;
        font-weight: 700;
        min-height: 2.8rem;
    }
    div[data-testid="stButton"] > button:hover {
        background: #CF6D17;
        border-color: #CF6D17;
        color: #FFFFFF;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E8ECEF;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(44, 62, 80, 0.05);
        padding: 0.85rem;
    }
    [data-testid="stFileUploader"] {
        background: #FFFFFF;
        border: 1px dashed #A9DFBF;
        border-radius: 14px;
        padding: 0.5rem;
    }
    .app-hero {
        background: linear-gradient(125deg, #1E9E55, #2ECC71);
        border-radius: 18px;
        box-shadow: 0 12px 30px rgba(46, 204, 113, 0.20);
        color: #FFFFFF;
        margin-bottom: 1.75rem;
        padding: 2rem 2.25rem;
    }
    .app-hero div { color: #FFFFFF; }
    .app-kicker { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.9; }
    .app-hero-title { font-size: 2.1rem; font-weight: 750; line-height: 1.2; margin: 0.4rem 0; }
    .app-hero-copy { font-size: 1rem; opacity: 0.93; }
    .section-kicker { color: #2ECC71; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; }
    .section-title { color: #2C3E50; font-size: 1.45rem; font-weight: 750; margin: 0.15rem 0 0.8rem; }
    .food-chip {
        background: #EAF8F0;
        border-radius: 999px;
        color: #197A43;
        display: inline-block;
        font-size: 0.9rem;
        font-weight: 650;
        margin: 0 0.45rem 0.45rem 0;
        padding: 0.45rem 0.8rem;
    }
    .image-card-title { color: #2C3E50; font-size: 0.95rem; font-weight: 700; margin-bottom: 0.65rem; }
    .nutrition-source-card {
        background: #FFFFFF;
        border: 1px solid #E8ECEF;
        border-radius: 12px;
        min-height: 112px;
        padding: 0.9rem;
    }
    .nutrition-source-title { color: #197A43; font-size: 0.82rem; font-weight: 750; margin-bottom: 0.45rem; }
    .nutrition-source-foods { color: #2C3E50; font-size: 0.95rem; font-weight: 650; line-height: 1.45; }
    .login-brand {
        color: #2ECC71;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-align: center;
        text-transform: uppercase;
        margin-bottom: 1.25rem;
    }
    .login-title {
        color: #2C3E50;
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 1.25rem;
    }
    .login-subtitle { color: #6C7A89; text-align: center; margin-bottom: 1rem; }
    .login-hero {
        background: #2ECC71;
        border-radius: 8px;
        color: #FFFFFF;
        min-height: 0;
        padding: 1.5rem;
    }
    .login-hero p, .login-hero h2, .login-hero div { color: #FFFFFF; }
    .login-hero-kicker {
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .login-hero-icon {
        align-items: center;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.35);
        border-radius: 50%;
        display: flex;
        font-size: 1.5rem;
        height: 48px;
        justify-content: center;
        margin-top: 1rem;
        width: 48px;
    }
    .login-hero-title {
        font-size: 1.7rem;
        font-weight: 750;
        line-height: 1.15;
        margin: 0.9rem 0 0.65rem;
    }
    .login-hero-copy { font-size: 0.9rem; line-height: 1.5; opacity: 0.92; }
    .login-trust { font-size: 0.78rem; font-weight: 600; margin-top: 1rem; opacity: 0.92; }
    .login-help { color: #6C7A89; font-size: 0.82rem; text-align: center; margin-top: -0.35rem; }
    .login-footer { color: #95A5A6; font-size: 0.75rem; text-align: center; margin-top: 1.25rem; }
</style>
""", unsafe_allow_html=True)

# Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# Memulihkan sesi setelah browser direfresh selama token masih valid.
if not st.session_state.logged_in:
    saved_session = st.query_params.get("session")
    if saved_session:
        saved_user = get_user_from_session_token(saved_session)
        if saved_user:
            st.session_state.logged_in = True
            st.session_state.user = saved_user
        else:
            st.query_params.clear()

# ====================== LOGIN ======================

if not st.session_state.logged_in:
    left_space, login_column, right_space = st.columns([1.6, 3.2, 1.6])

    with login_column:
        st.markdown("<div style='height: 7vh'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            info_column, form_column = st.columns([1.1, 1], gap="large")

            with info_column:
                st.markdown(
                    """
                    <div class="login-hero">
                        <div class="login-hero-kicker">✦ MBG Nutrition</div>
                        <div class="login-hero-icon">🥗</div>
                        <div class="login-hero-title">Gizi seimbang,<br>hidup sehat.</div>
                        <div class="login-hero-copy">Deteksi makanan dan pantau kebutuhan gizi Anda dalam satu tempat.</div>
                        <div class="login-trust">✓ Data gizi berbasis TKPI</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with form_column:
                st.markdown("<div class='login-title'>Masuk ke akun Anda</div>", unsafe_allow_html=True)
                menu_auth = st.radio(
                    "Akses akun",
                    ["Login", "Register"],
                    horizontal=True,
                    label_visibility="collapsed",
                )

                if menu_auth == "Login":
                    username = st.text_input("Username", key="login_username", placeholder="Masukkan username")
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="login_password",
                        placeholder="Masukkan password",
                    )

                    if st.button("Login", use_container_width=True):
                        user = login_user(username, password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user = user
                            st.query_params["session"] = create_session_token(user["id"])
                            st.rerun()
                        else:
                            st.error("Username atau password salah")
                    st.markdown("<div class='login-help'>Lupa password? Hubungi administrator.</div>", unsafe_allow_html=True)

                else:
                    nama = st.text_input("Nama Lengkap", key="register_nama", placeholder="Masukkan nama lengkap")
                    username = st.text_input("Username", key="register_username", placeholder="Buat username")
                    email = st.text_input("Email", key="register_email", placeholder="contoh@email.com")
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="register_password",
                        placeholder="Buat password",
                    )

                    if st.button("Daftar", use_container_width=True):
                        sukses = register_user(
                            username=username,
                            email=email,
                            password=password,
                            role="user",
                            nama_lengkap=nama,
                        )
                        if sukses:
                            st.success("Registrasi berhasil. Silakan masuk dengan akun baru Anda.")
                        else:
                            st.error("Registrasi gagal")
        st.markdown("<div class='login-footer'>© 2026 MBG Nutrition &nbsp;•&nbsp; Privasi &nbsp;•&nbsp; Bantuan</div>", unsafe_allow_html=True)
else:
    # Sudah Login
    user = st.session_state.user
    st.sidebar.markdown(
        f"""
        <div class="sidebar-profile">
            <div class="sidebar-brand">🥗 MBG Nutrition</div>
            <div class="sidebar-name">Halo, {user['nama_lengkap']}!</div>
            <div class="sidebar-role">Akun {user['role'].upper()} · Pantau gizi harian Anda</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='sidebar-nav-label'>Menu utama</div>", unsafe_allow_html=True)

    navigation_labels = {
        "Deteksi Makanan": "🔍  Deteksi Makanan",
        "Riwayat Saya": "🕘  Riwayat Saya",
        "Data Master Makanan": "📚  Data Master Makanan",
        "Laporan": "📊  Laporan Deteksi",
    }

    # Menu
    if user['role'] == 'admin':
       menu = st.sidebar.radio(
            "Navigasi",
            ["Deteksi Makanan", "Laporan", "Data Master Makanan"],
            format_func=navigation_labels.get,
            label_visibility="collapsed",
        )
    else:
        menu = st.sidebar.radio(
            "Navigasi",
            ["Deteksi Makanan", "Riwayat Saya", "Data Master Makanan"],
            format_func=navigation_labels.get,
            label_visibility="collapsed",
        )

    st.sidebar.divider()
    if st.sidebar.button("↪  Logout", key="logout_button", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.query_params.clear()
        st.rerun()

    # ==================== HALAMAN DETEKSI ====================
    if menu == "Deteksi Makanan":

        st.markdown(
            """
            <div class="app-hero">
                <div class="app-kicker">Asisten Gizi Pintar</div>
                <div class="app-hero-title">Kenali isi piring, pahami gizinya.</div>
                <div class="app-hero-copy">Unggah foto makanan untuk mendapatkan deteksi menu dan estimasi nilai gizi berbasis TKPI.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='section-kicker'>Langkah 1</div><div class='section-title'>Upload foto piring makanan</div>", unsafe_allow_html=True)

        sumber_foto = st.radio(
            "Sumber foto",
            ["Upload Foto", "Buka Kamera"],
            horizontal=True,
        )

        if sumber_foto == "Upload Foto":
            uploaded_file = st.file_uploader(
                "Pilih Foto",
                type=["jpg", "jpeg", "png"],
            )
        else:
            st.info("Izinkan akses kamera pada browser, arahkan kamera ke piring makanan, lalu tekan tombol ambil foto.")
            uploaded_file = st.camera_input("Ambil foto makanan")

        if uploaded_file:

            image = Image.open(uploaded_file)

            st.markdown("<div class='section-kicker'>Hasil analisis</div><div class='section-title'>Perbandingan foto dan deteksi AI</div>", unsafe_allow_html=True)
            col1, col2 = st.columns(2, gap="large")
            with col1:
                with st.container(border=True):
                    st.markdown("<div class='image-card-title'>Foto yang diupload</div>", unsafe_allow_html=True)
                    st.image(image, use_container_width=True)

            model = YOLO("models/best.pt")

            results = model(
                image,
                conf=0.5
            )

            annotated = results[0].plot()

            with col2:
                with st.container(border=True):
                    st.markdown("<div class='image-card-title'>Hasil deteksi YOLO</div>", unsafe_allow_html=True)
                    st.image(annotated, use_container_width=True)

            st.success("Deteksi selesai! Berikut rangkuman makanan dan estimasi gizinya.")

            st.markdown("<div class='section-kicker'>Menu terdeteksi</div><div class='section-title'>Makanan dalam piring Anda</div>", unsafe_allow_html=True)

            detected_foods = []

            for box in results[0].boxes:

                class_id = int(box.cls[0])

                nama_makanan = model.names[class_id]

                detected_foods.append(nama_makanan)

            detected_foods = list(set(detected_foods))

            if len(detected_foods) == 0:

                st.warning("Tidak ada makanan terdeteksi")

            else:

                chips = "".join(f"<span class='food-chip'>✓ {makanan.title()}</span>" for makanan in detected_foods)
                st.markdown(chips, unsafe_allow_html=True)
                

            # ========================
            # ESTIMASI NILAI GIZI
            # ========================

            st.markdown("<div class='section-kicker'>Estimasi gizi</div><div class='section-title'>Ringkasan nutrisi piring Anda</div>", unsafe_allow_html=True)

            total_energi = 0
            total_protein = 0
            total_lemak = 0
            total_karbo = 0
            total_serat = 0

            detail_gizi = []
            sumber_gizi = {}

            for makanan in detected_foods:

                data = get_gizi(makanan)

                if data:
                    kelompok = data.get("kelompok_pangan") or "Lainnya"
                    sumber_gizi.setdefault(kelompok, []).append(makanan.title())

                    detail_gizi.append({
                        "Makanan": makanan,
                        "Kelompok": kelompok,
                        "Energi": data["energi"],
                        "Protein": data["protein"],
                        "Lemak": data["lemak"],
                        "Karbohidrat": data["karbohidrat"],
                        "Serat": data["serat"]
                    })

                    total_energi += data["energi"]
                    total_protein += data["protein"]
                    total_lemak += data["lemak"]
                    total_karbo += data["karbohidrat"]
                    total_serat += data["serat"]
                   
            if sumber_gizi:
                st.markdown("<div class='section-kicker'>Komposisi piring</div><div class='section-title'>Sumber gizi yang terdeteksi</div>", unsafe_allow_html=True)
                source_icons = {
                    "Karbohidrat": "🍚",
                    "Protein hewani": "🍗",
                    "Protein nabati": "🌱",
                    "Serat & vitamin": "🥦",
                    "Kalsium & protein": "🥛",
                    "Lemak & kalsium": "🧀",
                    "Lainnya": "🍽️",
                }
                source_columns = st.columns(min(len(sumber_gizi), 4))
                for index, (kelompok, makanan_kelompok) in enumerate(sumber_gizi.items()):
                    with source_columns[index % len(source_columns)]:
                        icon = source_icons.get(kelompok, "🍽️")
                        st.markdown(
                            f"<div class='nutrition-source-card'><div class='nutrition-source-title'>{icon} Sumber {kelompok}</div><div class='nutrition-source-foods'>{', '.join(makanan_kelompok)}</div></div>",
                            unsafe_allow_html=True,
                        )

            st.markdown("<div class='section-kicker'>Rincian menu</div><div class='section-title'>Detail gizi per makanan</div>", unsafe_allow_html=True)

            df_gizi = pd.DataFrame(detail_gizi)

            st.dataframe(
                df_gizi,
                use_container_width=True,
                hide_index=True,
                height=220,
            )
                            
            st.markdown("<div class='section-kicker'>Total piring</div><div class='section-title'>Total estimasi nilai gizi</div>", unsafe_allow_html=True)
            metric_cols = st.columns(5)
            with metric_cols[0]:
                st.metric("Energi", f"{total_energi:.0f} kkal")
            with metric_cols[1]:
                st.metric("Protein", f"{total_protein:.1f} g")
            with metric_cols[2]:
                st.metric("Lemak", f"{total_lemak:.1f} g")
            with metric_cols[3]:
                st.metric("Karbohidrat", f"{total_karbo:.1f} g")
            with metric_cols[4]:
                st.metric("Serat", f"{total_serat:.1f} g")
            st.caption("Nilai merupakan estimasi berdasarkan data TKPI dan makanan yang terdeteksi oleh model.")
         
            save_col, _ = st.columns([1, 3])
            with save_col:
                if st.button("💾 Simpan Hasil", use_container_width=True):

                    simpan_hasil(
                        user["id"],
                        uploaded_file.name,
                        total_energi,
                        total_protein,
                        total_lemak,
                        total_karbo,
                        total_serat
                    )

                    st.success("Data berhasil disimpan")
                    st.balloons()

            # ==================== HALAMAN LAPORAN ====================
    if menu == "Laporan":

        st.title("📊 Laporan Deteksi")

        conn = get_connection()

        query = """
        SELECT *
        FROM hasil_deteksi
        ORDER BY id DESC
        """

        df = pd.read_sql(query, conn)

        conn.close()

        st.dataframe(
            df,
            width=800,
            height=300
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="laporan_deteksi.csv",
            mime="text/csv"
        )

        if len(df) > 0:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Grafik Energi")
                st.bar_chart(df["energi_total"])

            with col2:
                st.subheader("💪 Grafik Protein")
                st.bar_chart(df["protein_total"])

            col3, col4 = st.columns(2)

            with col3:
                st.subheader("🍚 Grafik Karbohidrat")
                st.bar_chart(df["karbo_total"])

            with col4:
                st.subheader("🥑 Grafik Lemak")
                st.bar_chart(df["lemak_total"])

            col5, col6 = st.columns(2)   
            with col5:
                st.subheader("🌾 Grafik Serat")
                st.bar_chart(df["serat_total"])

            with col6:
                st.empty()
                
            st.subheader("📋 Ringkasan Laporan")

            st.metric(
                "Rata-rata Energi",
                f"{df['energi_total'].mean():.1f} kkal"
            )

            st.metric(
                "Rata-rata Protein",
                f"{df['protein_total'].mean():.1f} g"
            )

            st.metric(
                "Jumlah Deteksi",
                len(df)
            )

            st.metric(
                "Rata-rata Karbohidrat",
                f"{df['karbo_total'].mean():.1f} g"
            )

            st.divider()

            st.caption(
                "Sistem Estimasi Nilai Gizi Program Makan Bergizi Gratis (MBG) Menggunakan YOLOv11 dan TKPI"
            )


        else:
            st.warning("Belum ada data laporan")

    if menu == "Data Master Makanan" and user['role'] != 'admin':

                st.markdown(
                    "<div class='app-hero'><div class='app-kicker'>Data referensi sistem</div><div class='app-hero-title'>Data Master Makanan</div><div class='app-hero-copy'>Daftar makanan dan nilai gizi yang menjadi acuan estimasi pada hasil deteksi.</div></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='section-kicker'>Tabel master</div><div class='section-title'>Tabel Data Master Makanan</div>", unsafe_allow_html=True)

                conn = get_connection()
                df = pd.read_sql(
                    """
                    SELECT nama_makanan AS 'Makanan', kelompok_pangan AS 'Kelompok Pangan',
                           keterangan_gizi AS 'Keterangan Gizi', berat_porsi AS 'Berat Porsi (g)',
                           energi AS 'Energi (kkal)', protein AS 'Protein (g)', lemak AS 'Lemak (g)',
                           karbohidrat AS 'Karbohidrat (g)', serat AS 'Serat (g)'
                    FROM tkpi
                    ORDER BY nama_makanan
                    """,
                    conn,
                )
                conn.close()
                st.dataframe(df, use_container_width=True, hide_index=True, height=480)
                st.caption("Data ini dikelola oleh admin dan digunakan sebagai referensi estimasi gizi.")

    if menu == "Data Master Makanan" and user['role'] == 'admin':

                st.markdown(
                    "<div class='app-hero'><div class='app-kicker'>Data referensi sistem</div><div class='app-hero-title'>Data Master Makanan</div><div class='app-hero-copy'>Kelola daftar makanan, kelompok pangan, dan nilai gizi sebagai acuan hasil deteksi.</div></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='section-kicker'>Tabel master</div><div class='section-title'>Tabel Data Master Makanan</div>", unsafe_allow_html=True)

                conn = get_connection()

                df = pd.read_sql(
                    "SELECT * FROM tkpi",
                    conn
                )

                st.dataframe(
                    df,
                    use_container_width=True,
                    height=300,
                    hide_index=True,
                )

                # =========================
                # TAMBAH DATA
                # =========================
                st.subheader("➕ Tambah Data")

                nama = st.text_input("Nama Makanan")
                kelompok = st.selectbox(
                    "Kelompok Pangan",
                    ["Karbohidrat", "Protein hewani", "Protein nabati", "Serat & vitamin", "Kalsium & protein", "Lemak & kalsium", "Lainnya"],
                )
                keterangan = st.text_input("Keterangan Gizi", placeholder="Contoh: Sumber energi utama dari karbohidrat")
                berat = st.number_input("Berat Porsi")
                energi = st.number_input("Energi")
                protein = st.number_input("Protein")
                lemak = st.number_input("Lemak")
                karbo = st.number_input("Karbohidrat")
                serat = st.number_input("Serat")

                if st.button("Tambah"):

                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        INSERT INTO tkpi
                        (
                            nama_makanan,
                            kelompok_pangan,
                            keterangan_gizi,
                            berat_porsi,
                            energi,
                            protein,
                            lemak,
                            karbohidrat,
                            serat
                        )
                        VALUES
                            (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            nama,
                            kelompok,
                            keterangan,
                            berat,
                            energi,
                            protein,
                            lemak,
                            karbo,
                            serat
                        )
                    )

                    conn.commit()
                    cursor.close()
                    st.success("Data berhasil ditambahkan")
                    st.rerun()

                # =========================
                # EDIT DATA
                # =========================
                st.subheader("✏️ Edit Data TKPI")

                edit_id = st.number_input(
                    "ID Data yang akan diubah",
                    min_value=1,
                    step=1,
                    key="edit_id"
                )

                edit_nama = st.text_input(
                    "Nama Makanan Baru",
                    key="edit_nama"
                )

                edit_kelompok = st.selectbox(
                    "Kelompok Pangan Baru",
                    ["Karbohidrat", "Protein hewani", "Protein nabati", "Serat & vitamin", "Kalsium & protein", "Lemak & kalsium", "Lainnya"],
                    key="edit_kelompok",
                )

                edit_keterangan = st.text_input(
                    "Keterangan Gizi Baru",
                    key="edit_keterangan"
                )

                edit_berat = st.number_input(
                    "Berat Porsi Baru",
                    key="edit_berat"
                )

                edit_energi = st.number_input(
                    "Energi Baru",
                    key="edit_energi"
                )

                edit_protein = st.number_input(
                    "Protein Baru",
                    key="edit_protein"
                )

                edit_lemak = st.number_input(
                    "Lemak Baru",
                    key="edit_lemak"
                )

                edit_karbo = st.number_input(
                    "Karbohidrat Baru",
                    key="edit_karbo"
                )

                edit_serat = st.number_input(
                    "Serat Baru",
                    key="edit_serat"
                )

                if st.button("Update Data"):

                    cursor = conn.cursor()

                    cursor.execute(
                        """
                        UPDATE tkpi
                        SET
                            nama_makanan=%s,
                            kelompok_pangan=%s,
                            keterangan_gizi=%s,
                            berat_porsi=%s,
                            energi=%s,
                            protein=%s,
                            lemak=%s,
                            karbohidrat=%s,
                            serat=%s
                        WHERE id=%s
                        """,
                        (
                            edit_nama,
                            edit_kelompok,
                            edit_keterangan,
                            edit_berat,
                            edit_energi,
                            edit_protein,
                            edit_lemak,
                            edit_karbo,
                            edit_serat,
                            edit_id
                        )
                    )

                    conn.commit()
                    cursor.close()
                    st.success("Data berhasil diubah")
                    st.rerun()

                # =========================
                # HAPUS DATA
                # =========================
                st.subheader("🗑️ Hapus Data")

                hapus_id = st.number_input(
                    "ID Data",
                    min_value=1,
                    step=1,
                    key="hapus_id"
                )

                if st.button("Hapus"):

                    cursor = conn.cursor()

                    cursor.execute(
                        "DELETE FROM tkpi WHERE id=%s",
                        (hapus_id,)
                    )

                    conn.commit()
                    cursor.close()
                    
                    st.success("Data berhasil dihapus")
                    st.rerun()

                conn.close()


    if menu == "Riwayat Saya":
        st.markdown(
            """
            <div class="app-hero">
                <div class="app-kicker">Pemantauan gizi pribadi</div>
                <div class="app-hero-title">Riwayat deteksi Anda</div>
                <div class="app-hero-copy">Lihat kembali hasil deteksi dan pantau pola estimasi gizi dari setiap piring makanan.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        conn = get_connection()
        query = """
        SELECT *
        FROM hasil_deteksi
        WHERE user_id = %s
        ORDER BY tanggal DESC, id DESC
        """
        df = pd.read_sql(query, conn, params=(user["id"],))
        conn.close()

        if len(df) == 0:
            st.info("Belum ada riwayat deteksi. Gunakan menu Deteksi Makanan untuk menambahkan hasil pertama Anda.")
        else:
            df["tanggal"] = pd.to_datetime(df["tanggal"])
            st.markdown("<div class='section-kicker'>Ringkasan aktivitas</div><div class='section-title'>Gambaran gizi Anda</div>", unsafe_allow_html=True)

            summary_cols = st.columns(5)
            with summary_cols[0]:
                st.metric("Total Deteksi", len(df))
            with summary_cols[1]:
                st.metric("Rata-rata Energi", f"{df['energi_total'].mean():.0f} kkal")
            with summary_cols[2]:
                st.metric("Rata-rata Protein", f"{df['protein_total'].mean():.1f} g")
            with summary_cols[3]:
                st.metric("Rata-rata Karbo", f"{df['karbo_total'].mean():.1f} g")
            with summary_cols[4]:
                st.metric("Rata-rata Serat", f"{df['serat_total'].mean():.1f} g")

            st.markdown("<div class='section-kicker'>Daftar riwayat</div><div class='section-title'>Hasil deteksi tersimpan</div>", unsafe_allow_html=True)
            history_view = df[["tanggal", "foto", "energi_total", "protein_total", "lemak_total", "karbo_total", "serat_total"]].copy()
            history_view.columns = ["Tanggal", "Foto", "Energi (kkal)", "Protein (g)", "Lemak (g)", "Karbohidrat (g)", "Serat (g)"]
            history_view["Tanggal"] = history_view["Tanggal"].dt.strftime("%d %b %Y · %H:%M")
            st.dataframe(history_view, use_container_width=True, hide_index=True, height=300)

            download_col, _ = st.columns([1, 3])
            with download_col:
                csv = history_view.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Unduh Riwayat", csv, "riwayat_gizi.csv", "text/csv", use_container_width=True)

            st.markdown("<div class='section-kicker'>Tren nutrisi</div><div class='section-title'>Perubahan estimasi gizi per deteksi</div>", unsafe_allow_html=True)
            chart_df = df.sort_values("tanggal").set_index("tanggal")
            chart_col1, chart_col2 = st.columns(2, gap="large")
            with chart_col1:
                with st.container(border=True):
                    st.markdown("<div class='image-card-title'>⚡ Energi dan protein</div>", unsafe_allow_html=True)
                    st.line_chart(chart_df[["energi_total", "protein_total"]])
            with chart_col2:
                with st.container(border=True):
                    st.markdown("<div class='image-card-title'>🥗 Karbohidrat, lemak, dan serat</div>", unsafe_allow_html=True)
                    st.line_chart(chart_df[["karbo_total", "lemak_total", "serat_total"]])

            st.caption("Nilai pada riwayat merupakan estimasi berdasarkan data TKPI dan hasil deteksi YOLO.")


                        

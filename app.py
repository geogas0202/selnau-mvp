import streamlit as st
import pandas as pd
import openai

# 1) Load your OpenAI key from Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Simply Doctor AI – Klinik Selnau MVP")

# 2) File-upload widgets
fin_file = st.file_uploader("Upload FINANCIALS.xlsx", type="xlsx")
cal_file = st.file_uploader("Upload CALENDAR.xlsx",  type="xlsx")

if fin_file and cal_file:

    # —————— Financials prep ——————
    fin = pd.read_excel(fin_file)
    fin.columns = (
        fin.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    fin = fin.rename(columns={
        "rechdatum":   "date",            # invoice date
        "transbetrag": "gross_revenue"    # transaction amount → gross_revenue
    })
    fin["date"]        = pd.to_datetime(fin["date"],        dayfirst=True)
    fin["net_revenue"] = fin["gross_revenue"]                # no discounts/refunds

    # —————— Calendar prep ——————
    cal = pd.read_excel(cal_file)
    cal.columns = (
        cal.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    cal = cal.rename(columns={
        "datum":      "scheduled_start",
        "ende":       "scheduled_end",
        "dauer":      "duration_min",
        "erschienen": "appeared",
        "deleted":    "cancelled"
    })
    cal["scheduled_start"] = pd.to_datetime(cal["scheduled_start"], dayfirst=True)
    cal["scheduled_end"]   = pd.to_datetime(cal["scheduled_end"],   dayfirst=True)
    cal["status"] = cal.apply(
        lambda r: "cancelled" if r.cancelled
                  else ("completed" if r.appeared else "no_show"),
        axis=1
    )

    # —————— KPIs & charts ——————
    util_pct = 100 * cal[cal.status=="completed"].shape[0] / cal.shape[0]
    st.metric("Utilis

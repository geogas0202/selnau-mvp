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

# normalize to snake case
fin.columns = (
    fin.columns
       .str.strip()
       .str.lower()
       .str.replace(r"\s+", "_", regex=True)
)

# **DEBUG**: show me what they really are
st.write("📋 FIN columns:", fin.columns.tolist())

# then your rename(...)
fin = fin.rename(columns={ 
    "rechdatum": "date",
    "transbetrag": "gross_revenue",
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
        # —————— KPIs & charts ——————
    util_pct = 100 * cal[cal.status=="completed"].shape[0] / cal.shape[0]
    st.metric("Utilisation %", f"{util_pct:,.1f}")
    rev_trend = fin.groupby(fin["date"].dt.to_period("M"))["net_revenue"].sum()
    st.bar_chart(rev_trend)

    # —————— Chat & AI Q&A ——————
    st.write("---")
    prompt_q = st.chat_input("Ask me about revenue, utilisation, no-shows…")
    if prompt_q:
        sample_md = fin.head(50).to_markdown(index=False)
        full_prompt = (
            f"Data sample:\n{sample_md}\n\n"
            f"Question: {prompt_q}\nAnswer in one paragraph."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":full_prompt}],
            temperature=0
        )
        st.chat_message("assistant").write(resp.choices[0].message.content.strip())

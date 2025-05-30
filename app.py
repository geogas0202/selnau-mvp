import streamlit as st, pandas as pd, openai, io, datetime as dt

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Klinik Selnau – AI Report MVP")

fin_file = st.file_uploader("Upload FINANCIALS.xlsx", type="xlsx")
if fin_file:
    # 1) Read raw
    fin = pd.read_excel(fin_file)
    # 2) Normalize headers...
    fin.columns = (
        fin.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    # 3) Rename German → expected names
    fin = fin.rename(columns={
        "rechdatum":     "date",
        "transbetrag":   "gross_revenue",
    })
    # 4) Parse dates
    fin["date"] = pd.to_datetime(fin["date"], dayfirst=True)
    # 5) Compute net_revenue
    fin["net_revenue"] = fin["gross_revenue"]

cal_file = st.file_uploader("Upload CALENDAR.xlsx", type="xlsx")
if cal_file:
    cal = pd.read_excel(cal_file)

    # 1) Normalize headers
    cal.columns = (
        cal.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    # Now: ["datum", "ende", "dauer", "kalender", "termin",
    #       "kommentar", "erschienen", "deleted"]

    # 2) Rename to our expected names
    cal = cal.rename(columns={
        "datum":     "scheduled_start",
        "ende":      "scheduled_end",
        "dauer":     "duration_min",      # assuming 'dauer' is in minutes
        "kalender":  "provider_id",
        "termin":    "appointment_type",
        "erschienen":"appeared",          # boolean: True if patient showed
        "deleted":   "cancelled"          # boolean: True if cancelled
    })

    # 3) Parse datetimes
    cal["scheduled_start"] = pd.to_datetime(cal["scheduled_start"], dayfirst=True)
    cal["scheduled_end"]   = pd.to_datetime(cal["scheduled_end"],   dayfirst=True)

    # 4) Derive status & utilisation flag
    def map_status(row):
        if row["cancelled"]:
            return "cancelled"
        if row["appeared"]:
            return "completed"
        return "no_show"
    cal["status"] = cal.apply(map_status, axis=1)
    cal["utilised_slot"] = cal["status"].isin(["completed", "confirmed", "appeared"]).astype(int)

    # … now you can compute utilisation % as before …

if fin_file and cal_file:
    fin = pd.read_excel(fin_file).rename(str.lower, axis=1)
    cal = pd.read_excel(cal_file).rename(str.lower, axis=1)
    fin["net_revenue"] = fin["gross_revenue"] - fin.get("discount",0) - fin.get("refund",0)
    util_pct = 100*cal[cal.status.isin(["confirmed","completed"])].shape[0]/cal.shape[0]

    st.metric("Utilisation %", f"{util_pct:,.1f}")
    st.bar_chart(fin.groupby(pd.to_datetime(fin.date).dt.to_period("M"))["net_revenue"].sum())

    st.write("---")
    q = st.chat_input("Ask me about revenue, utilisation, no-shows…")
    if q:
        with st.spinner("Thinking…"):
            df_sample = fin.head(50).to_markdown(index=False)  # keeps tokens low
            prompt = f"Data sample:\n{df_sample}\n\nQuestion: {q}\nAnswer in one paragraph."
            reply = openai.ChatCompletion.create(model="gpt-4o-mini",
                                                 messages=[{"role":"user","content":prompt}],
                                                 temperature=0)
        st.chat_message("assistant").write(reply.choices[0].message.content.strip())

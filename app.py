import streamlit as st, pandas as pd, openai, io, datetime as dt

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Klinik Selnau – AI Report MVP")

fin_file   = st.file_uploader("Upload FINANCIALS.xlsx", type="xlsx")
cal_file   = st.file_uploader("Upload CALENDAR.xlsx",  type="xlsx")

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

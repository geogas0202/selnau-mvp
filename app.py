import streamlit as st
import pandas as pd
import openai

# ── 1) Configure OpenAI ───────────────────────────────────────────────────
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ── 2) Page setup ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Simply Doctor AI", layout="centered")
st.title("Simply Doctor AI – Klinik Selnau MVP")

# ── 3) File upload widgets ────────────────────────────────────────────────
fin_file = st.file_uploader("Upload FINANCIALS.xlsx", type="xlsx")
cal_file = st.file_uploader("Upload CALENDAR.xlsx",  type="xlsx")

if fin_file and cal_file:

    # …—— A) Financials prep ——…
    fin = pd.read_excel(fin_file)

    # Normalize headers once (snake_case)
    fin.columns = (
        fin.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    # DEBUG: uncomment to inspect your actual columns
    # st.write("FIN columns:", fin.columns.tolist())

    # 1) Find the date column (anything containing “rech” + “datum”)
    date_cols = [c for c in fin.columns if "rech" in c and "datum" in c]
    if not date_cols:
        st.error(f"❌ Could not find your date column in financials. Available: {fin.columns.tolist()}")
        st.stop()
    date_col = date_cols[0]
    fin["date"] = pd.to_datetime(fin[date_col], dayfirst=True)

    # 2) Find the gross amount column (TransBetrag)
    gross_cols = [c for c in fin.columns if "transbetrag" == c]
    if not gross_cols:
        st.error(f"❌ Could not find your transaction column in financials. Available: {fin.columns.tolist()}")
        st.stop()
    fin["gross_revenue"] = fin[gross_cols[0]]

    # 3) Compute net_revenue (no discounts/refunds)
    fin["net_revenue"] = fin["gross_revenue"]

    # …—— B) Calendar prep ——…
    cal = pd.read_excel(cal_file)
    cal.columns = (
        cal.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )
    # DEBUG: uncomment to inspect your actual columns
    # st.write("CAL columns:", cal.columns.tolist())

    # Map your calendar columns dynamically
    # scheduled_start: find “datum” or “date”
    start_cols = [c for c in cal.columns if "datum" in c or "date" in c]
    if not start_cols:
        st.error(f"❌ Could not find start-date column in calendar. Available: {cal.columns.tolist()}")
        st.stop()
    cal["scheduled_start"] = pd.to_datetime(cal[start_cols[0]], dayfirst=True)

    # scheduled_end: find “ende” or “end”
    end_cols = [c for c in cal.columns if "ende" in c or "end" in c]
    if not end_cols:
        st.error(f"❌ Could not find end-date column in calendar. Available: {cal.columns.tolist()}")
        st.stop()
    cal["scheduled_end"] = pd.to_datetime(cal[end_cols[0]], dayfirst=True)

    # duration in minutes: find “dauer”
    dur_cols = [c for c in cal.columns if "dauer" in c or "duration" in c]
    cal["duration_min"] = cal[dur_cols[0]] if dur_cols else (
        (cal["scheduled_end"] - cal["scheduled_start"]).dt.total_seconds() / 60
    )

    # appeared / cancelled flags
    appeared_cols  = [c for c in cal.columns if "erschienen" in c or "appeared" in c]
    cancelled_cols = [c for c in cal.columns if "deleted" in c or "cancel" in c]
    cal["appeared"]  = cal[appeared_cols[0]]  if appeared_cols  else False
    cal["cancelled"] = cal[cancelled_cols[0]] if cancelled_cols else False

    # derive status & utilisation
    cal["status"] = cal.apply(
        lambda r: "cancelled" if r.cancelled
                  else ("completed" if r.appeared else "no_show"),
        axis=1
    )
    cal["utilised_slot"] = (cal["status"] == "completed").astype(int)

    # ── 4) KPIs & Charts ────────────────────────────────────────────────────
    # Utilisation % = completed slots / total slots
    util_pct = 100 * cal["utilised_slot"].sum() / len(cal)
    st.metric("Utilisation %", f"{util_pct:,.1f}%")

    # Monthly net revenue trend
    rev_trend = (
        fin
        .groupby(fin["date"].dt.to_period("M"))["net_revenue"]
        .sum()
        .to_timestamp()
    )
    st.bar_chart(rev_trend)

    # ── 5) Chat Q&A ──────────────────────────────────────────────────────────
    st.write("---")
    question = st.chat_input("Ask me about revenue, utilisation, no-shows…")

    if question:
        sample_md = fin.head(50).to_markdown(index=False)
        prompt = (
            f"You are a clinic operations analyst.\n\n"
            f"Here is a sample of the data:\n{sample_md}\n\n"
            f"Question: {question}\nAnswer in one concise paragraph."
        )
        with st.spinner("Thinking…"):
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        st.chat_message("assistant").write(resp.choices[0].message.content.strip())

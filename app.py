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

# ── 4) Main logic ─────────────────────────────────────────────────────────
if fin_file and cal_file:

    # …—— A) Financials prep ——…
    fin = pd.read_excel(fin_file)

    # Normalize headers: lowercase, strip, spaces → underscores
    fin.columns = (
        fin.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )

    # Rename German → expected names
    fin = fin.rename(columns={
        "rechdatum":   "date",
        "transbetrag": "gross_revenue",
    })

    # Parse and compute
    fin["date"]        = pd.to_datetime(fin["date"], dayfirst=True)
    fin["net_revenue"] = fin["gross_revenue"]  # no discounts/refunds column here

    # …—— B) Calendar prep ——…
    cal = pd.read_excel(cal_file)

    # Normalize headers
    cal.columns = (
        cal.columns
           .str.strip()
           .str.lower()
           .str.replace(r"\s+", "_", regex=True)
    )

    # Rename German → expected names
    cal = cal.rename(columns={
        "datum":      "scheduled_start",
        "ende":       "scheduled_end",
        "dauer":      "duration_min",
        "erschienen": "appeared",
        "deleted":    "cancelled",
    })

    # Parse datetimes
    cal["scheduled_start"] = pd.to_datetime(cal["scheduled_start"], dayfirst=True)
    cal["scheduled_end"]   = pd.to_datetime(cal["scheduled_end"],   dayfirst=True)

    # Derive status and utilisation flag
    cal["status"] = cal.apply(
        lambda r: "cancelled"
                  if r.cancelled
                  else ("completed" if r.appeared else "no_show"),
        axis=1
    )
    cal["utilised_slot"] = cal["status"].isin(["completed"]).astype(int)

    # ── 5) KPIs & Charts ────────────────────────────────────────────────────
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

    # ── 6) Chat Q&A ──────────────────────────────────────────────────────────
    st.write("---")
    question = st.chat_input("Ask me about revenue, utilisation, no-shows…")

    if question:
        # Sample first 50 rows to keep token count low
        sample_md = fin.head(50).to_markdown(index=False)

        prompt = (
            f"You are a clinic operations analyst.\n\n"
            f"Here is a sample of the data:\n{sample_md}\n\n"
            f"Question: {question}\n"
            f"Answer in one concise paragraph."
        )

        with st.spinner("Thinking…"):
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )

        answer = resp.choices[0].message.content.strip()
        st.chat_message("assistant").write(answer)

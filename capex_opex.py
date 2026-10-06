# Capex / Opex vs. years in deployment for A100, H100, B200.
#   Capex = GPU price / GPU_CAPEX_SHARE (GPU is ~75% of total capex)
#   Opex  = cumulative electricity cost to run that GPU for N years (USD)
#   y     = Capex / cumulative Opex(N)  -> falls as 1/N; crosses 1.0 when
#           lifetime electricity spend equals the chip price.
#
# Power model: avg power = TDP * utilization (linear, ignores idle floor).
# Run: streamlit run capex_opex.py

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

HOURS_PER_YEAR = 24 * 365

# Approximate per-GPU street prices (USD) and board TDP (W), SXM variants.
# Prices vary a lot by volume/vendor/date; edit as needed.
SOURCES = {
    "A100 80GB price": "https://jarvislabs.ai/ai-faqs/nvidia-a100-gpu-price",
    "A100 80GB TDP (SXM4)": "https://www.techpowerup.com/gpu-specs/a100-sxm4-80-gb.c3746",
    "H100 SXM price": "https://northflank.com/blog/how-much-does-an-nvidia-h100-gpu-cost",
    "H100 SXM TDP": "https://www.nvidia.com/en-us/data-center/h100/",
    "B200 SXM price": "https://modal.com/blog/nvidia-b200-pricing",
    "B200 SXM6 TDP": "https://www.techpowerup.com/gpu-specs/b200-sxm6.c4210",
    "Electricity price (2026 US industrial avg, EIA)": "https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a",
    "GPU purchase = 75% of capex (Fig. 3)": "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=11617794",
    "Rental price, on-demand $/GPU-hr (Lambda, Oct 2026)": "https://lambda.ai/pricing",
    "Rental price ranges across providers (2026)": "https://www.cloudzero.com/blog/cloud-gpu-pricing-comparison/",
}

# On-demand rental price, USD per GPU-hour (Lambda 8x SXM instances, Oct 2026).
RENTAL_PRICE = {
    "A100 80GB SXM": 2.79,
    "H100 SXM": 3.99,
    "B200 SXM": 6.69,
}

# GPU purchase is ~75% of total capex; the rest is server/network/facility.
GPU_CAPEX_SHARE = 0.75


CHIPS = {
    #          price_usd  tdp_w
    "A100 80GB SXM": (19_000,  400),
    "H100 SXM":  (37_500,  700),
    "B200 SXM":      (35_000, 1000),
}

# US average commercial electricity ~ $0.13/kWh (EIA); industrial ~ $0.08.
DEFAULT_KWH_PRICE = 0.0977 # 2026 US Industrial average, source: https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a
DEFAULT_UTIL = 0.3


def annual_opex(tdp_w, util, kwh_price):
    kwh_per_year = tdp_w / 1000 * util * HOURS_PER_YEAR
    return kwh_per_year * kwh_price


st.set_page_config(page_title="Capex / Opex", layout="wide")
st.title("Capex / cumulative Opex vs. years in deployment")

with st.sidebar:
    util = st.slider("Utilization", 0.05, 1.0, DEFAULT_UTIL, 0.01, format="%.2f")
    kwh = st.slider("Electricity price ($/kWh)", 0.06, 0.35, DEFAULT_KWH_PRICE, 0.0025, format="%.4f")
    years = st.slider("Years", 0.25, 6.0, 3.0, 0.25, format="%.2f")
    max_years = 6
    log_y = st.checkbox("Log y-axis", value=True)
    chips = st.multiselect("Chips", list(CHIPS), default=list(CHIPS))
    st.markdown("**Rental price ($/GPU-hr)**")
    rates = {name: st.number_input(name, 0.0, 50.0, RENTAL_PRICE[name], 0.05, format="%.2f")
             for name in CHIPS}

years = np.linspace(0, max_years, 241)
rows, summary = [], []
for name in chips:
    price, tdp = CHIPS[name]
    capex = price / GPU_CAPEX_SHARE
    opex = annual_opex(tdp, util, kwh)
    revenue = rates[name] * util * HOURS_PER_YEAR  # billed only while utilized
    rows.append(pd.DataFrame({
        "chip": name,
        "years": years,
        # undefined at t=0 (no opex yet); NaN points are dropped from the chart
        "capex_over_opex": np.divide(capex, opex * years, out=np.full_like(years, np.nan), where=years > 0),
        "cumulative_opex": opex * years,
        "net_cash": (revenue - opex) * years - capex,
    }))
    summary.append({
        "Chip": name,
        "GPU price ($)": price,
        "Capex ($)": round(capex),
        "TDP (W)": tdp,
        "Opex / yr ($)": round(opex),
        "Capex/Opex @ 3 yr": round(capex / (opex * 3), 1),
        "Capex/Opex @ 5 yr": round(capex / (opex * 5), 1),
        "Breakeven (yr)": round(capex / opex, 1),
        "$/GPU-hr": rates[name],
        "Revenue / yr ($)": round(revenue),
        "Revenue per kWh ($)": round(rates[name] / (tdp / 1000), 2),
        "Payback (yr)": round(capex / (revenue - opex), 2) if revenue > opex else float("inf"),
    })

if not chips:
    st.info("Select at least one chip.")
    st.stop()

df = pd.concat(rows)
y_scale = alt.Scale(type="log") if log_y else alt.Scale(zero=False)

hover = alt.selection_point(fields=["years"], nearest=True, on="pointerover", empty=False)
lines = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
    x=alt.X("years:Q", title="Years in deployment", scale=alt.Scale(domain=[0, max_years])),
    y=alt.Y("capex_over_opex:Q", title="Capex / cumulative Opex", scale=y_scale),
    color=alt.Color("chip:N", title=None, legend=alt.Legend(orient="top-right")),
)
points = lines.mark_point(filled=True, size=60).encode(
    opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    tooltip=[
        alt.Tooltip("chip:N", title="Chip"),
        alt.Tooltip("years:Q", title="Years", format=".2f"),
        alt.Tooltip("capex_over_opex:Q", title="Capex/Opex", format=".2f"),
        alt.Tooltip("cumulative_opex:Q", title="Cumulative opex ($)", format=",.0f"),
    ],
).add_params(hover)
breakeven = alt.Chart(pd.DataFrame({"y": [1.0]})).mark_rule(strokeDash=[4, 4], color="gray").encode(y="y:Q")

st.altair_chart((lines + points + breakeven).properties(height=520), use_container_width=True)
st.caption(f"Utilization {util:.0%}, \\${kwh:.4f}/kWh. Capex = GPU price / {GPU_CAPEX_SHARE:.0%}. "
           "Dashed line: capex = cumulative opex.")
st.dataframe(pd.DataFrame(summary), hide_index=True)

st.subheader("Cumulative net cash: revenue − electricity − capex")
cash = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
    x=alt.X("years:Q", title="Years in deployment", scale=alt.Scale(domain=[0, max_years])),
    y=alt.Y("net_cash:Q", title="Cumulative net cash ($)", axis=alt.Axis(format="$,.0f")),
    color=alt.Color("chip:N", title=None, legend=alt.Legend(orient="top-left")),
    tooltip=[
        alt.Tooltip("chip:N", title="Chip"),
        alt.Tooltip("years:Q", title="Years", format=".2f"),
        alt.Tooltip("net_cash:Q", title="Net cash ($)", format=",.0f"),
    ],
)
zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(strokeDash=[4, 4], color="gray").encode(y="y:Q")
st.altair_chart((cash + zero).properties(height=420), use_container_width=True)
st.caption("Revenue = rental price (\\$/GPU-hr) × utilization × 8760 h/yr, "
           "where utilization is the fraction of the year the GPU is rented out. "
           "Payback is where a line crosses \\$0.")

st.subheader("Sources")
st.markdown("\n".join(f"- {label}: [{url}]({url})".replace("$", r"\$") for label, url in SOURCES.items()))
st.caption("Opex assumes average power = TDP × utilization (no idle floor, no cooling/PUE).")

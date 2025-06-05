# Interactive financial dashboard using Streamlit
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# Minimalistic header font style
st.markdown(
    "<style>h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 300; }</style>",
    unsafe_allow_html=True
)
# Sidebar gentle background tint
st.markdown(
    """
    <style>
    .css-1d391kg { background-color: #f5f5f5; }
    </style>
    """,
    unsafe_allow_html=True
)


def run_simulation(
    jack_income_usd,
    fx_rate,
    jessica_income_cad,
    jessica_start_month,
    bonus_milestone_total,
    start_savings,
    cottage_sale_price,
    loan_repay_month="2026-12",
):
    heloc_bal = 330000
    cash = start_savings
    cra_rate = 0.0938
    heloc_rate = 0.0545
    expenses = 18700

    bonus_month = "2025-07"
    refund_month = "2025-10"
    cottage_month = "2025-10"
    refund = 28046
    cottage = 135000

    jack_income_cad = jack_income_usd * fx_rate
    data = []
    cra_bal = 170000  # Assuming initial CRA balance, as it was missing
    cra_paid_off = False
    heloc_paid_off = False

    months = pd.date_range("2024-06", "2027-01", freq="MS")

    for m in months:
        m_str = m.strftime("%Y-%m")
        j_income = jessica_income_cad if m_str >= jessica_start_month else 0
        inflow = jack_income_cad + j_income + 3400  # includes rental income
        if m_str >= "2025-11":
            monthly_expenses = expenses - 1700  # remove cottage mortgage after sale
        else:
            monthly_expenses = expenses
        net = inflow - monthly_expenses
        if m.year == 2026:
            net += 1200  # FTC benefit begins in 2026

        labels = []

        # Apply bonus and loan
        if m_str == bonus_month:
            bonus_amount = 50000 + bonus_milestone_total  # confirmed + future milestone bonuses
            loan_amount = 50000

            # Apply bonus to CRA first
            if cra_bal > 0:
                applied = min(bonus_amount, cra_bal)
                cra_bal -= applied
                bonus_amount -= applied
            if bonus_amount > 0 and heloc_bal > 0:
                applied = min(bonus_amount, heloc_bal)
                heloc_bal -= applied
            # Add loan amount directly to cash
            cash += loan_amount

        # Apply refund to CRA first
        if m_str == refund_month:
            if cra_bal > 0:
                applied = min(refund, cra_bal)
                cra_bal -= applied
                remainder = refund - applied
                heloc_bal -= remainder
            else:
                heloc_bal -= refund

        # Apply cottage proceeds to CRA first
        if m_str == cottage_month:
            labels.append("Cottage")
            net_cottage_proceeds = cottage_sale_price - 285000  # 245K mortgage + 40K tax estimate
            if cra_bal > 0:
                applied = min(net_cottage_proceeds, cra_bal)
                cra_bal -= applied
                remainder = net_cottage_proceeds - applied
                if heloc_bal > 0:
                    applied_heloc = min(remainder, heloc_bal)
                    heloc_bal -= applied_heloc
                    cash += remainder - applied_heloc
                else:
                    cash += remainder
            else:
                if heloc_bal > 0:
                    applied_heloc = min(net_cottage_proceeds, heloc_bal)
                    heloc_bal -= applied_heloc
                    cash += net_cottage_proceeds - applied_heloc
                else:
                    cash += net_cottage_proceeds
            # add $420K sale proceeds, $135K goes to debt as before, rest used for taxes + capital gains
            # assume $12K tax bill appears following month
        elif m_str == "2025-11":
            labels.append("CG Tax")
            cash -= 12000

        # Interest accrual
        cra_int = max(0, cra_bal * cra_rate / 12)
        heloc_int = heloc_bal * heloc_rate / 12

        # Add income, subtract interest, then apply surplus to debt
        cash += net

        reserved_for_loan = 50000 if m_str >= "2025-07" and m_str < loan_repay_month else 0
        available_cash = max(cash - reserved_for_loan, 0)

        # CRA interest accrues regardless of ability to pay
        cra_int = max(0, cra_bal * cra_rate / 12)

        # Subtract interest from available_cash if affordable
        if available_cash >= cra_int:
            available_cash -= cra_int
        else:
            available_cash = 0  # Interest is still owed but cash is gone
            available_cash -= heloc_int
        if available_cash < 0:
            heloc_int += available_cash
            available_cash = 0

        # Apply loan repayment at end of 2026
        if m_str == loan_repay_month:
            labels.append("Loan")
            cash -= 50000

        # Apply remaining available_cash to CRA first, then HELOC
        if available_cash > 0:
            if cra_bal > 0:
                applied = min(available_cash, cra_bal)
                cra_bal -= applied
                available_cash -= applied
            if heloc_bal > 0 and available_cash > 0:
                applied = min(available_cash, heloc_bal)
                heloc_bal -= applied
                available_cash -= applied

        # Update cash to reflect payments made from available_cash
        cash = reserved_for_loan + available_cash

        # Annotations
        if m_str == "2025-11":
            labels.append("CG Tax")
        if m_str == cottage_month:
            labels.append("Cottage")
        if m_str == bonus_month:
            labels.append("Bonus")
        if m_str == refund_month:
            labels.append("Refund")
        if m_str == jessica_start_month:
            labels.append("Jessica Starts")
        if m_str == "2026-01":
            labels.append("FTC Relief")
        if not cra_paid_off and cra_bal <= 0:
            labels.append("CRA Paid Off")
            cra_paid_off = True
        if not heloc_paid_off and heloc_bal <= 0:
            labels.append("HELOC Paid Off")
            heloc_paid_off = True
        label = " | ".join(labels)

        data.append(
            {
                "Month": m_str,
                "Cash": cash,
                "CRA Balance": cra_bal,
                "HELOC Balance": heloc_bal,
                "CRA Interest": cra_int,
                "HELOC Interest": heloc_int,
                "Label": label,
                "Monthly Surplus": net - cra_int - heloc_int,
                "Monthly Income": inflow,
                "Monthly Expenses": monthly_expenses,
            }
        )

    return pd.DataFrame(data)


st.set_page_config(layout="wide")

# Sidebar controls
st.sidebar.title("🧭 Navigate Your Scenario")
jack_income = st.sidebar.number_input("Jack's Monthly Income (USD)", value=12600)
fx_rate = st.sidebar.slider(
    "USD to CAD Exchange Rate", min_value=1.2, max_value=1.5, value=1.35, step=0.01
)
jess_income = st.sidebar.number_input("Jessica's Monthly Income (CAD)", value=3000)
jess_start = st.sidebar.selectbox(
    "Jessica Starts Working",
    ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"],
)
savings = st.sidebar.number_input("Starting Savings (CAD)", value=20000)

# New: Compensation scenario toggle
comp_case = st.sidebar.radio("Comp Scenario", ["Base Case", "Best Case"])
bonus_milestone_total = 150000 if comp_case == "Best Case" else 0

# Cottage sale slider
cottage_sale_price = st.sidebar.slider(
    "Cottage Sale Price (CAD)", min_value=350000, max_value=450000, value=420000, step=10000
)

# Run simulation
df = run_simulation(
    jack_income,
    fx_rate,
    jess_income,
    jess_start,
    bonus_milestone_total,
    savings,
    cottage_sale_price,
)

# Display plots
st.title("✨ Forward Flow: 2025+ Cash Compass")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Month"], y=df["Cash"], name="Cash Position"))
fig.add_trace(
    go.Scatter(x=df["Month"], y=df["CRA Balance"], name="CRA Balance", line=dict(dash="dash"))
)
fig.add_trace(
    go.Scatter(x=df["Month"], y=df["HELOC Balance"], name="HELOC Balance", line=dict(dash="dot"))
)


# Replace per-event stars with a single grouped trace per month
event_months = df[df["Label"] != ""]
grouped_labels = event_months.groupby("Month").agg({
    "Label": lambda x: " | ".join(x),
    "Cash": "first"
}).reset_index()

fig.add_trace(
    go.Scatter(
        x=grouped_labels["Month"],
        y=grouped_labels["Cash"],
        mode="markers",
        marker=dict(symbol="star", size=14, color="gold"),
        name="Key Events",
        hovertemplate="<b>%{text}</b><br>Month: %{x}<extra></extra>",
        text=grouped_labels["Label"]
    )
)

fig.update_layout(
    title="Cash and Debt Balances Over Time", xaxis_title="Month", yaxis_title="CAD", height=600
)
st.plotly_chart(fig, use_container_width=True)

# Interest stacked chart
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=df["Month"], y=df["CRA Interest"], name="CRA Interest"))
fig2.add_trace(go.Bar(x=df["Month"], y=df["HELOC Interest"], name="HELOC Interest"))
fig2.update_layout(
    barmode="stack", title="Monthly Interest Payments", xaxis_title="Month", yaxis_title="CAD", height=400
)
st.plotly_chart(fig2, use_container_width=True)

# Combined income, expenses, and surplus chart
fig_combined = go.Figure()

fig_combined.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Monthly Income"],
        name="Monthly Income",
        line=dict(color="blue"),
        mode="lines+markers",
        marker=dict(size=6),
    )
)
fig_combined.add_trace(
    go.Scatter(
        x=df["Month"],
        y=df["Monthly Expenses"],
        name="Monthly Expenses",
        line=dict(color="orange"),
        mode="lines+markers",
        marker=dict(size=6),
    )
)

# Surplus positive values in green
fig_combined.add_trace(
    go.Scatter(
        x=df["Month"],
        y=[val if val >= 0 else None for val in df["Monthly Surplus"]],
        name="Surplus",
        line=dict(color="green"),
        mode="lines+markers",
        marker=dict(size=6),
    )
)
# Surplus negative values in red (deficit)
fig_combined.add_trace(
    go.Scatter(
        x=df["Month"],
        y=[val if val < 0 else None for val in df["Monthly Surplus"]],
        name="Deficit",
        line=dict(color="red"),
        mode="lines+markers",
        marker=dict(size=6),
    )
)


# Add grouped star markers for key events per month on surplus line for context
event_months = df[df["Label"] != ""]
grouped_labels2 = event_months.groupby("Month").agg({
    "Label": lambda x: " | ".join(x),
    "Monthly Surplus": "first"
}).reset_index()
fig_combined.add_trace(
    go.Scatter(
        x=grouped_labels2["Month"],
        y=[y if not pd.isna(y) else 0 for y in grouped_labels2["Monthly Surplus"]],
        mode="markers",
        marker=dict(symbol="star", size=14, color="gold"),
        name="Key Events",
        hovertemplate="<b>%{text}</b><br>Month: %{x}<extra></extra>",
        text=grouped_labels2["Label"],
        showlegend=True,
    )
)

fig_combined.update_layout(
    title="Monthly Income, Expenses, and Surplus",
    xaxis_title="Month",
    yaxis_title="CAD",
    height=500,
    hovermode="x unified",
)

st.plotly_chart(fig_combined, use_container_width=True)

# Assumptions Sidebar Section
with st.expander("🔍 Model Assumptions + Flow Notes", expanded=True):
    st.markdown(
        """
### 💡 Key Financial Assumptions
- **Starting Cash:** $20,000 CAD
- **Jack’s Income:** $12,600 USD/month × FX → approx. $17,010 CAD/month
- **Jessica’s Income:** $5,000 CAD/month starting from the selected month
- **Rental Income:** $3,400 CAD/month (Esplanade)
- **Expenses:** $18,700/month before cottage sale, $17,000/month after
- **Bonus & Loan:** $50K bonus + $50K interest-free loan in July 2025 (loan repaid Dec 2026)
- **Tax Refund:** $28,046 CAD in Oct 2025 (from ABIL claim)
- **Cottage Sale:** $420K in Oct 2025; $135K applied to debt; $12K tax due in April 2026
- **CRA Interest Rate:** 9.38% annually, monthly compounding
- **HELOC Interest Rate:** 5.45% annually, monthly compounding
- **U.S. FTC Relief:** +$1,200/month from Jan 2026 due to Canadian capital gains

### 📊 Cash Flow Logic
- Net income pays expenses first
- CRA and HELOC interest applied monthly
- Surplus cash goes first to CRA, then HELOC
- Cash is preserved until debt is fully paid

---
⭐ **Key Events** shown as gold stars may combine multiple occurrences (e.g., Bonus + Refund). Hover for breakdown.
        """
    )

# Expense and Income Summary Table
summary_data = {
    "Category": [
        "Jack Income (CAD)",
        "Jessica Income (CAD)",
        "Rental Income",
        "Total Income",
        "Zaya Tuition (Aug 2025 onward)",
        "Ruby Daycare",
        "Cottage Mortgage (until Oct 2025)",
        "Esplanade Mortgage",
        "Durocher Mortgage",
        "Other Expenses (based on real Monarch averages)",
        "Total Expenses Before Interest",
    ],
    "Monthly Amount": [
        jack_income * fx_rate,
        jess_income,
        3400,
        jack_income * fx_rate + jess_income + 3400,
        1500,
        200,
        1700,
        3000,
        6000,
        5000,
        18700,
    ],
}
sum_df = pd.DataFrame(summary_data)
st.markdown("### 📊 Monthly Income and Expense Breakdown")
st.table(sum_df.set_index("Category"))

# Data Table
st.markdown("### 📅 Monthly Financial Simulation Table")
st.dataframe(df.set_index("Month"))

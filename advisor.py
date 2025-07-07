import requests

def generate_recommendation(age, income, profession, region, goal):
    if goal == "Wealth Accumulation":
        equity_pct, debt_pct, gold_pct = 70, 20, 10
    elif goal == "Retirement Planning":
        equity_pct, debt_pct, gold_pct = 50, 40, 10
    elif goal == "Short-term Savings":
        equity_pct, debt_pct, gold_pct = 20, 70, 10
    else:  # ELSS Tax Saving
        equity_pct, debt_pct, gold_pct = 80, 10, 10

    equity_amt = round(income * equity_pct / 100)
    debt_amt = round(income * debt_pct / 100)
    gold_amt = round(income * gold_pct / 100)

    allocation = {
        "Equity": f"{equity_pct}% (~₹{equity_amt})",
        "Debt": f"{debt_pct}% (~₹{debt_amt})",
        "Gold": f"{gold_pct}% (~₹{gold_amt})"
    }

    advice_text = f"""
    ## Investment Advice
    Based on your profile:

    - Age: {age}
    - Income: ₹{income}
    - Profession: {profession}
    - Region: {region}
    - Goal: {goal}

    **Suggested allocation:**
    - {equity_pct}% in Equity (~₹{equity_amt})
    - {debt_pct}% in Debt (~₹{debt_amt})
    - {gold_pct}% in Gold (~₹{gold_amt})
    """

    return {
        "allocation": allocation,
        "advice_text": advice_text
    }


def search_funds(query):
    search_results = []
    try:
        mf_list = requests.get("https://api.mfapi.in/mf").json()
        for mf in mf_list:
            if query.lower() in mf["schemeName"].lower():
                search_results.append(mf)
    except Exception:
        search_results.append({"schemeName": "Unable to fetch results. Check your internet or API."})
    return search_results

import yfinance as yf
import requests

def get_real_mutual_funds():
    scheme_codes = {
        "Axis Bluechip Fund": "120503",
        "Mirae Asset Large Cap Fund": "118834",
        "Canara Robeco Bluechip Equity Fund": "103241"
    }
    funds = []
    for name, code in scheme_codes.items():
        url = f"https://api.mfapi.in/mf/{code}"
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                nav = data["data"][0]["nav"]
                funds.append({"name": name, "code": code, "latest_nav": f"₹{nav}"})
        except:
            funds.append({"name": name, "code": code, "latest_nav": "Unavailable"})
    return funds

def get_stock_suggestions():
    symbols = ['INFY.NS', 'TCS.NS', 'RELIANCE.NS', 'SBIN.NS', 'HDFCBANK.NS']
    stocks = []
    for s in symbols:
        try:
            stock = yf.Ticker(s)
            info = stock.info
            stocks.append({
                "name": info.get("shortName", s),
                "symbol": s,
                "price": f"₹{info.get('currentPrice', 'N/A')}",
                "sector": info.get("sector", "N/A")
            })
        except:
            stocks.append({"name": s, "symbol": s, "price": "N/A", "sector": "N/A"})
    return stocks

def generate_recommendation(age, income, profession, region):
    if age < 30:
        risk = "Aggressive"; eq, de, go = 60, 20, 20
    elif 30 <= age <= 45:
        risk = "Balanced"; eq, de, go = 50, 30, 20
    else:
        risk = "Conservative"; eq, de, go = 30, 50, 20

    eq_amt, de_amt, go_amt = income * eq // 100, income * de // 100, income * go // 100
    funds = get_real_mutual_funds()
    stocks = get_stock_suggestions()

    summary = f"""
🧾 Based on your profile ({age} yrs, {profession}, ₹{income}/mo, region: {region}):

🔐 **Risk Profile**: {risk}

💡 **Split**:
- ₹{eq_amt} in equity
- ₹{de_amt} in debt
- ₹{go_amt} in gold

📈 **Mutual Funds**:
"""
    for f in funds:
        summary += f"- {f['name']} (NAV: {f['latest_nav']})\n"
    summary += "\n💹 **Stocks**:\n"
    for s in stocks:
        summary += f"- {s['name']} ({s['symbol']}): {s['price']} | Sector: {s['sector']}\n"

    return {
        "risk_profile": risk,
        "allocation": {
            "Equity": f"{eq}% (~₹{eq_amt})",
            "Debt": f"{de}% (~₹{de_amt})",
            "Gold": f"{go}% (~₹{go_amt})"
        },
        "suggested_mutual_funds": funds,
        "suggested_stocks": stocks,
        "advice_text": summary
    }

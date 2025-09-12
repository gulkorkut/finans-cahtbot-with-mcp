# fraud_server.py
import joblib
import os
import requests
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import json

MODEL_PATH = "models/fraud_model.pkl"
ALERT_LOG = "alerts_log.txt"

mcp = FastMCP(
    "FraudAgent",
    instructions="You are a Fraud Detection agent. Provide fraud scores, flags and human-readable explanations. If uncertain, return 'unknown' and recommend escalation.",
    host="localhost",
    port=8005
)

# Load model if exists
model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
        print("Loaded fraud model.")
    except Exception as e:
        print("Failed to load model:", e)

# --- Helper functions ---
def simple_features_from_tx(tx: dict):
    amount = float(tx.get("amount", 0))
    hour = 0
    try:
        dt = datetime.fromisoformat(tx.get("date").replace("Z", "+00:00"))
        hour = dt.hour
    except:
        hour = 0
    card_present = 1 if tx.get("payment_method") in ["credit_card","debit_card"] else 0
    merchant_risk = 0
    merchant = tx.get("merchant","").lower()
    if "casino" in merchant or "bet" in merchant or "adult" in merchant:
        merchant_risk = 2
    elif "online" in merchant or "market" in merchant:
        merchant_risk = 1
    user_avg = tx.get("user_avg", 500)
    location_mismatch = int(tx.get("location_mismatch", 0))
    return [amount, hour, card_present, merchant_risk, user_avg, location_mismatch]

def log_alert(transaction_id: str, score: float):
    """ Append fraud alerts to alerts_log.txt if flagged """
    if score > 0.6:  # risk threshold
        alert = {
            "alert_id": f"A_{transaction_id}_{int(datetime.utcnow().timestamp())}",
            "transaction_id": transaction_id,
            "score": round(score, 4),
            "time": datetime.utcnow().isoformat()
        }
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(alert) + "\n")

def read_alerts(since_minutes: int = 60):
    """ Read alerts from log file within last X minutes """
    if not os.path.exists(ALERT_LOG):
        return []
    now = datetime.utcnow()
    alerts = []
    with open(ALERT_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                a = json.loads(line.strip())
                t = datetime.fromisoformat(a["time"])
                delta = (now - t).total_seconds() / 60
                if delta <= since_minutes:
                    alerts.append(a)
            except:
                continue
    return alerts

# --- MCP Tools ---
@mcp.tool()
def score_transaction(transaction_id: str) -> dict:
    """Score a transaction and log if fraudulent"""
    try:
        resp = requests.get(f"http://localhost:8000/transaction/1414141")
        resp.raise_for_status()
        data = resp.json()
        tx = next((t for t in data.get("spending_history", []) if t["transaction_id"] == transaction_id), None)
        if tx is None:
            return {"error": "transaction_not_found"}

        features = simple_features_from_tx(tx)
        if model:
            prob = float(model.predict_proba([features])[0, 1])
        else:
            score = min(features[0]/20000,1.0)*0.6 + (features[3]/2)*0.2 + features[5]*0.2
            prob = min(max(score, 0.0), 1.0)
        flag = prob > 0.6
        explanation = f"Score based on amount={features[0]:.2f}, merchant_risk={features[3]}, location_mismatch={features[5]}"

        # Log fraud alerts
        if flag:
            log_alert(transaction_id, prob)

        return {"transaction_id": transaction_id, "score": round(prob, 4), "flag": flag, "explanation": explanation}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def check_transactions_range(user_id: str = "1414141", last_n: int = 1) -> list:
    """Check last N transactions for fraud risk"""
    results = []
    try:
        tx_resp = requests.get(f"http://localhost:8000/transaction/{user_id}")
        tx_resp.raise_for_status()
        tx_data = tx_resp.json()
        txs = tx_data.get("spending_history", [])
        sorted_txs = sorted(
            txs,
            key=lambda t: datetime.fromisoformat(t["date"].replace("Z","+00:00")),
            reverse=True
        )
        for tx in sorted_txs[:last_n]:
            features = simple_features_from_tx(tx)
            if model:
                prob = float(model.predict_proba([features])[0,1])
            else:
                score = min(features[0]/20000,1.0)*0.6 + (features[3]/2)*0.2 + features[5]*0.2
                prob = min(max(score,0.0),1.0)
            flag = prob > 0.6
            explanation = f"Score based on amount={features[0]:.2f}, merchant_risk={features[3]}, location_mismatch={features[5]}"
            if flag:
                log_alert(tx["transaction_id"], prob)
            results.append({
                "transaction_id": tx["transaction_id"],
                "score": round(prob,4),
                "flag": flag,
                "explanation": explanation
            })
        return results
    except Exception as e:
        return {"error": str(e)}
@mcp.tool()
def check_transaction_by_merchant(user_id: str = "1414141", merchant_keyword: str = "") -> str:
    """Check transactions for a given merchant and return detailed info"""
    try:
        resp = requests.get(f"http://localhost:8000/transaction/{user_id}")
        resp.raise_for_status()
        data = resp.json()
        txs = data.get("spending_history", [])

        # Merchant adıyla eşleşen işlemleri filtrele
        filtered_txs = [tx for tx in txs if merchant_keyword.lower() in tx.get("merchant","").lower()]
        if not filtered_txs:
            return f"{merchant_keyword} ile ilgili harcama bulunamadı."

        messages = []
        flagged_count = 0
        for tx in filtered_txs:
            features = simple_features_from_tx(tx)
            if model:
                prob = float(model.predict_proba([features])[0,1])
            else:
                score = min(features[0]/20000,1.0)*0.6 + (features[3]/2)*0.2 + features[5]*0.2
                prob = min(max(score,0.0),1.0)
            flag = prob > 0.6
            if flag:
                flagged_count += 1
                log_alert(tx["transaction_id"], prob)

            messages.append(
                f"- İşlem ID: {tx['transaction_id']}\n"
                f"  Tarih: {tx['date']}\n"
                f"  Kategori: {tx.get('category','')}\n"
                f"  Ödeme Yöntemi: {tx.get('payment_method','')} (****{tx.get('card_last4','')})\n"
                f"  Miktar: {tx.get('amount',0):.2f} {tx.get('currency','')}\n"
                f"  Lokasyon: {tx.get('location','')}\n"
                f"  Risk Skoru: {prob:.4f}\n"
                f"  Şüpheli mi?: {'Evet' if flag else 'Hayır'}\n"
            )

        summary = f"{merchant_keyword} harcamalarınızda "
        summary += "şüpheli bir durum tespit edildi." if flagged_count else "şüpheli bir durum tespit edilmedi."
        summary += f" {len(filtered_txs)} işlem kaydedildi.\n\nİşlem Detayları:\n"

        return summary + "\n".join(messages)

    except Exception as e:
        return f"Hata oluştu: {str(e)}"


@mcp.tool()
def recent_fraud_alerts(since_minutes: int = 60) -> list:
    """Return fraud alerts from log within timeframe"""
    return read_alerts(since_minutes)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

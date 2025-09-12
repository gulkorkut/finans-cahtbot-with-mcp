# train_fraud_model.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import os

os.makedirs("models", exist_ok=True)

def synthesize_data(n=20000, seed=42):
    rng = np.random.RandomState(seed)
    # Features: amount, hour, card_present, merchant_risk, user_avg_amount, location_mismatch
    amount = rng.exponential(scale=2000, size=n)
    hour = rng.randint(0, 24, size=n)
    card_present = rng.binomial(1, 0.9, size=n)
    merchant_risk = rng.choice([0,1,2], size=n, p=[0.85,0.13,0.02])
    user_avg = rng.normal(loc=500, scale=300, size=n).clip(1,None)
    location_mismatch = rng.binomial(1, 0.02 + (amount>5000)*0.05, size=n)

    # Label: fraud more likely with high amount, high merchant_risk, location_mismatch, odd hour
    score = (amount>5000).astype(int) + (merchant_risk==2).astype(int)*2 + location_mismatch + ((hour<6)|(hour>23)).astype(int)
    prob = 1/(1+np.exp(-(score-1.5)))
    label = rng.binomial(1, prob*0.6)

    df = pd.DataFrame({
        "amount": amount,
        "hour": hour,
        "card_present": card_present,
        "merchant_risk": merchant_risk,
        "user_avg": user_avg,
        "location_mismatch": location_mismatch,
        "is_fraud": label
    })
    return df

if __name__ == "__main__":
    df = synthesize_data(20000)
    X = df[["amount","hour","card_present","merchant_risk","user_avg","location_mismatch"]]
    y = df["is_fraud"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    preds = clf.predict_proba(X_test)[:,1]
    print("ROC AUC:", roc_auc_score(y_test, preds))
    print(classification_report(y_test, (preds>0.5).astype(int)))
    joblib.dump(clf, "models/fraud_model.pkl")
    print("Saved model to models/fraud_model.pkl")

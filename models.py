import os
import sys

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

sys.stdout.reconfigure(encoding="utf-8")

RANDOM_STATE = 42   # щоб результати повторювалися
MIN_ATTEMPTS = 5    # беремо лише учасників, у яких хоча б стільки спроб
TEST_SIZE = 0.3     # 30% спроб лишаємо для перевірки

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "features_clean.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

SERVICE_COLUMNS = ["user", "session_id", "attempt_id", "backspace_count", "error_count"]

def load_data():
    if not os.path.exists(DATA_PATH):
        sys.exit(f"Не знайдено {DATA_PATH}. Спочатку запустіть features.py і eda.ipynb.")
    df = pd.read_csv(DATA_PATH)

    df = df.drop(columns=[c for c in df.columns if c.startswith("dd_")])
    feature_cols = [c for c in df.columns if c not in SERVICE_COLUMNS]
    return df, feature_cols

def identification(df, feature_cols):
    counts = df["user"].value_counts()
    keep = counts[counts >= MIN_ATTEMPTS].index
    data = df[df["user"].isin(keep)]
    print(f"Задача 'хто це?': {len(keep)} учасників, {len(data)} спроб")

    X = data[feature_cols]
    y = data["user"]
    # stratify=y: кожна людина потрапляє і в навчання, і в тест
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )

    candidates = {
        "knn": GridSearchCV(
            make_pipeline(StandardScaler(), KNeighborsClassifier()),
            {"kneighborsclassifier__n_neighbors": [1, 3, 5, 7]},
            cv=3,
        ),
        "random_forest": GridSearchCV(
            RandomForestClassifier(random_state=RANDOM_STATE),
            {"n_estimators": [100, 200], "max_depth": [None, 5, 10]},
            cv=3,
        ),
    }

    results = []
    for name, search in candidates.items():
        search.fit(X_train, y_train)
        model = search.best_estimator_
        pred = model.predict(X_test)

        precision, recall, _, _ = precision_recall_fscore_support(
            y_test, pred, average="macro", zero_division=0
        )
        row = {
            "задача": "хто це?",
            "модель": name,
            "accuracy": round(accuracy_score(y_test, pred), 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "FAR": "",
            "FRR": "",
            "параметри": str(search.best_params_),
        }
        results.append(row)
        print(f"  {name}: accuracy={row['accuracy']}, precision={row['precision']}, "
              f"recall={row['recall']}, параметри: {search.best_params_}")

        joblib.dump(model, os.path.join(MODELS_DIR, f"{name}.pkl"))
        save_confusion_matrix(y_test, pred, name)

    return results


def save_confusion_matrix(y_true, y_pred, name):
    labels = sorted(set(y_true) | set(y_pred))
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(f"Матриця помилок: {name}")
    plt.xlabel("модель сказала")
    plt.ylabel("насправді")
    plt.savefig(os.path.join(REPORTS_DIR, f"confusion_{name}.png"), dpi=150, bbox_inches="tight")
    plt.close()


def make_one_class(kind):
    if kind == "one_class_svm":
        return make_pipeline(StandardScaler(), OneClassSVM(nu=0.1, gamma="scale"))
    return make_pipeline(StandardScaler(), IsolationForest(contamination=0.1, random_state=RANDOM_STATE))


def verify_owner(df, feature_cols, owner, kind):
    own = df[df["user"] == owner]
    others = df[df["user"] != owner]

    own_train, own_test = train_test_split(own, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    model = make_one_class(kind)
    model.fit(own_train[feature_cols])

    # predict: 1 = "свій", -1 = "чужий"
    own_pred = model.predict(own_test[feature_cols])
    others_pred = model.predict(others[feature_cols])

    frr = (own_pred == -1).mean()     # своїх помилково відхилили
    far = (others_pred == 1).mean()   # чужих помилково пропустили
    return model, far, frr


def verification(df, feature_cols):
    counts = df["user"].value_counts()
    owners = counts[counts >= MIN_ATTEMPTS].index
    print(f"Задача 'свій чи чужий?': власників {len(owners)}")

    results = []
    for kind in ["one_class_svm", "isolation_forest"]:
        fars, frrs = [], []
        best_model = None
        for owner in owners:
            model, far, frr = verify_owner(df, feature_cols, owner, kind)
            fars.append(far)
            frrs.append(frr)
            if best_model is None:      # owners відсортовані: перший = найбільше спроб
                best_model = model
                joblib.dump(model, os.path.join(MODELS_DIR, f"{kind}_{owner}.pkl"))

        row = {
            "задача": "свій чи чужий?",
            "модель": kind,
            "accuracy": "",
            "precision": "",
            "recall": "",
            "FAR": round(sum(fars) / len(fars), 3),
            "FRR": round(sum(frrs) / len(frrs), 3),
            "параметри": "усереднено за власниками",
        }
        results.append(row)
        print(f"  {kind}: FAR={row['FAR']}, FRR={row['FRR']}")
    return results


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    df, feature_cols = load_data()
    print(f"Спроб: {len(df)}, учасників: {df['user'].nunique()}, ознак: {len(feature_cols)}\n")

    results = identification(df, feature_cols)
    print()
    results += verification(df, feature_cols)

    table = pd.DataFrame(results)
    table.to_csv(os.path.join(REPORTS_DIR, "models_results.csv"), index=False, encoding="utf-8")
    print("\nТаблиця збережена: reports/models_results.csv")
    print(f"Моделі збережені в папці: {MODELS_DIR}")


if __name__ == "__main__":
    main()

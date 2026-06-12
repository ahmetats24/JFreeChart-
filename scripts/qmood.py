#!/usr/bin/env python3
"""
QMOOD quality computation + visualisation.

Reads data/<version>/summary.json files produced by run_all.py, normalises
every design property against the baseline (first) version exactly as in
Bansiya & Davis (2002), then computes the six QMOOD quality attributes:

  Reusability       = -0.25*Coupling + 0.25*Cohesion + 0.5*Messaging + 0.5*DesignSize
  Flexibility       =  0.25*Encapsulation - 0.25*Coupling + 0.5*Composition + 0.5*Polymorphism
  Understandability = -0.33*Abstraction + 0.33*Encapsulation - 0.33*Coupling + 0.33*Cohesion
                      -0.33*Polymorphism - 0.33*Complexity - 0.33*DesignSize
  Functionality     =  0.12*Cohesion + 0.22*Polymorphism + 0.22*Messaging
                      +0.22*DesignSize + 0.22*Hierarchies
  Extendibility     =  0.5*Abstraction - 0.5*Coupling + 0.5*Inheritance + 0.5*Polymorphism
  Effectiveness     =  0.2*Abstraction + 0.2*Encapsulation + 0.2*Composition
                      +0.2*Inheritance + 0.2*Polymorphism

Reference: J. Bansiya, C. G. Davis, "A Hierarchical Model for Object-Oriented
Design Quality Assessment", IEEE Trans. Software Eng. 28(1), 2002.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
CHARTS = os.path.join(ROOT, "charts")

PROPS = ["DesignSize", "Hierarchies", "Abstraction", "Encapsulation", "Coupling",
         "Cohesion", "Composition", "Inheritance", "Polymorphism", "Messaging",
         "Complexity"]

WEIGHTS = {
    "Reusability":       {"Coupling": -0.25, "Cohesion": 0.25, "Messaging": 0.5, "DesignSize": 0.5},
    "Flexibility":       {"Encapsulation": 0.25, "Coupling": -0.25, "Composition": 0.5, "Polymorphism": 0.5},
    "Understandability": {"Abstraction": -0.33, "Encapsulation": 0.33, "Coupling": -0.33,
                          "Cohesion": 0.33, "Polymorphism": -0.33, "Complexity": -0.33,
                          "DesignSize": -0.33},
    "Functionality":     {"Cohesion": 0.12, "Polymorphism": 0.22, "Messaging": 0.22,
                          "DesignSize": 0.22, "Hierarchies": 0.22},
    "Extendibility":     {"Abstraction": 0.5, "Coupling": -0.5, "Inheritance": 0.5,
                          "Polymorphism": 0.5},
    "Effectiveness":     {"Abstraction": 0.2, "Encapsulation": 0.2, "Composition": 0.2,
                          "Inheritance": 0.2, "Polymorphism": 0.2},
}


def load():
    with open(os.path.join(ROOT, "versions.json")) as fh:
        versions = json.load(fh)
    rows = []
    for v in versions:
        p = os.path.join(ROOT, "data", v["label"], "summary.json")
        if not os.path.exists(p):
            continue
        s = json.load(open(p))
        rows.append({"version": v["label"], "date": v["date"],
                     "n_classes": s["n_classes"], "n_interfaces": s["n_interfaces"],
                     **s["properties"],
                     **{f"raw_{k}": vv for k, vv in s["raw_means"].items()}})
    return pd.DataFrame(rows)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    os.makedirs(CHARTS, exist_ok=True)
    df = load()
    labels = [f"{r.version}\n{r.date[:4]}" for r in df.itertuples()]

    # --- normalisation against baseline (first version) ----------------------
    norm = df.copy()
    base = df.iloc[0]
    for p in PROPS:
        norm[p] = df[p] / base[p] if base[p] else df[p]

    # --- quality attributes ---------------------------------------------------
    qual = pd.DataFrame({"version": df["version"], "date": df["date"]})
    for q, w in WEIGHTS.items():
        qual[q] = sum(coef * norm[p] for p, coef in w.items())

    df.to_csv(os.path.join(RESULTS, "design_properties.csv"), index=False)
    norm[["version", "date"] + PROPS].to_csv(
        os.path.join(RESULTS, "design_properties_normalized.csv"), index=False)
    qual.to_csv(os.path.join(RESULTS, "qmood_quality_scores.csv"), index=False)
    df[["version", "date"] + [c for c in df.columns if c.startswith("raw_")]].to_csv(
        os.path.join(RESULTS, "raw_metric_means.csv"), index=False)

    # --- chart 1: quality attribute evolution ---------------------------------
    fig, ax = plt.subplots(figsize=(11, 6))
    for q in WEIGHTS:
        ax.plot(labels, qual[q], marker="o", linewidth=2, label=q)
    ax.axhline(0, color="gray", linewidth=0.7, linestyle="--")
    ax.set_title("JFreeChart — QMOOD Kalite Niteliklerinin Evrimi (2007–2025)\n"
                 "(1.0.6 sürümüne göre normalize edilmiş indeks değerleri)", fontsize=12)
    ax.set_ylabel("QMOOD kalite indeksi")
    ax.set_xlabel("Sürüm")
    ax.legend(ncol=3, fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "01_qmood_kalite_evrimi.png"), dpi=150)

    # --- chart 2: design properties (normalised, small multiples) -------------
    fig, axes = plt.subplots(3, 4, figsize=(14, 8), sharex=True)
    for ax, p in zip(axes.flat, PROPS):
        ax.plot(range(len(norm)), norm[p], marker="o", color="#1f6f8b")
        ax.axhline(1, color="gray", linewidth=0.7, linestyle="--")
        ax.set_title(p, fontsize=10)
        ax.set_xticks(range(len(norm)))
        ax.set_xticklabels([r.version for r in norm.itertuples()], rotation=90, fontsize=6)
        ax.grid(alpha=0.3)
    axes.flat[-1].axis("off")
    fig.suptitle("JFreeChart — QMOOD Tasarım Özellikleri (1.0.6 = 1.0 taban çizgisi)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(CHARTS, "02_tasarim_ozellikleri.png"), dpi=150)

    # --- chart 3: growth -------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(labels, df["n_classes"], color="#1f6f8b", label="Sınıf sayısı (DSC)")
    ax.bar(labels, df["n_interfaces"], bottom=df["n_classes"], color="#f4a259",
           label="Arayüz sayısı")
    for i, (c, n) in enumerate(zip(df["n_classes"], df["n_interfaces"])):
        ax.text(i, c + n + 5, str(c + n), ha="center", fontsize=8)
    ax.set_title("JFreeChart — Tasarım Boyutunun Büyümesi (ana kütüphane, test kodu hariç)")
    ax.set_ylabel("Tür sayısı")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, "03_tasarim_boyutu.png"), dpi=150)

    # --- chart 4: raw metric means ---------------------------------------------
    keys = ["raw_WMC", "raw_CBO", "raw_RFC", "raw_LCOM", "raw_MPC", "raw_DIT"]
    names = ["WMC (ort.)", "CBO (ort.)", "RFC (ort.)", "LCOM (ort.)", "MPC (ort.)", "DIT (ort.)"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 6), sharex=True)
    for ax, k, n in zip(axes.flat, keys, names):
        ax.plot(range(len(df)), df[k], marker="o", color="#9a3b3b")
        ax.set_title(n, fontsize=10)
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df["version"], rotation=90, fontsize=7)
        ax.grid(alpha=0.3)
    fig.suptitle("JFreeChart — Sınıf Başına Ortalama Nesne Yönelimli Metrikler", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(CHARTS, "04_ham_metrikler.png"), dpi=150)

    print(qual.round(3).to_string(index=False))
    print("\nProperties (raw):")
    print(df[["version"] + PROPS].round(3).to_string(index=False))


if __name__ == "__main__":
    main()

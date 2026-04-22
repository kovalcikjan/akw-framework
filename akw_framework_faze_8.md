# Fáze 8: Weighted Prioritization (Scoring)

Výpočet priority score pro každé keyword.

---

## Cíl fáze

Vypočítat composite score pro prioritizaci keywords na základě business value, difficulty a traffic potenciálu.

---

## Scoring Formula

```
PRIORITY_SCORE = (
    business_value × 0.40 +
    ranking_probability × 0.35 +
    traffic_potential × 0.25
)
```

Kde:
- **Business value**: Intent score × relevance × conversion potential
- **Ranking probability**: 100 - KD + position bonus
- **Traffic potential**: Volume × CTR estimate × (1 - SERP feature loss)

---

## Vstupy

| Soubor | Zdroj |
|--------|-------|
| `data/interim/keywords_categorized.csv` | Fáze 5 |
| `data/interim/keywords_clustered.csv` | Fáze 6 (pokud byla spuštěna) |
| `data/interim/competitive_gaps.csv` | Fáze 7 |
| `params.yaml` (weights) | Config |

> **Poznámka**: Pokud běžela Fáze 6 (SERP Clustering), použij `keywords_clustered.csv`. Jinak `keywords_categorized.csv`.

---

## Workflow

```
1. Load and merge data
         ↓
2. Calculate business value
         ↓
3. Calculate ranking probability
         ↓
4. Calculate traffic potential
         ↓
5. Compute priority score
         ↓
6. Rank and segment
         ↓
7. Output: keywords_scored.csv
```

---

## 8.1 Scoring Parameters

### Default weights (params.yaml)

```yaml
scoring:
  weights:
    business_value: 0.40
    ranking_probability: 0.35
    traffic_potential: 0.25

  intent_scores:
    transactional: 10
    commercial: 7
    informational: 3
    navigational: 1

  position_bonus:
    "1-3": 30
    "4-10": 20
    "11-20": 10
    "21-50": 5
    "51+": 0

  ctr_by_position:
    1: 0.32
    2: 0.17
    3: 0.11
    4: 0.08
    5: 0.06
    6: 0.05
    7: 0.04
    8: 0.03
    9: 0.03
    10: 0.02

  serp_feature_ctr_loss:
    featured_snippet: 0.15
    local_pack: 0.10
    shopping: 0.12
    video: 0.05
    paa: 0.08
```

---

## 8.2 Business Value Score

### Components

```python
def calculate_business_value(row: pd.Series, params: dict) -> float:
    """Calculate business value score (0-100)."""
    # Intent score (0-10)
    intent_scores = params["scoring"]["intent_scores"]
    intent_score = intent_scores.get(row["intent"], 3)

    # Relevance score (0-100, from Fáze 6)
    relevance = row.get("relevance_score", 50)

    # Conversion potential (based on funnel position)
    funnel_conversion = {
        "BOFU": 1.0,   # High conversion
        "MOFU": 0.6,   # Medium conversion
        "TOFU": 0.3,   # Low conversion
        "BRAND": 0.8   # Direct traffic
    }
    conversion = funnel_conversion.get(row.get("funnel", "TOFU"), 0.3)

    # Combine: normalize to 0-100
    business_value = (
        (intent_score / 10) * 40 +  # Max 40 points from intent
        (relevance / 100) * 40 +     # Max 40 points from relevance
        conversion * 20               # Max 20 points from conversion
    )

    return round(business_value, 1)

df["business_value"] = df.apply(lambda r: calculate_business_value(r, params), axis=1)
```

### Business value distribution

```python
print(f"Business value stats:")
print(df["business_value"].describe())
print(f"\nBy intent:")
print(df.groupby("intent")["business_value"].mean().round(1))
```

---

## 8.3 Ranking Probability Score

### Components

```python
def calculate_ranking_probability(row: pd.Series, params: dict) -> float:
    """Calculate ranking probability score (0-100)."""
    # Base from KD (inverted)
    kd = row.get("kd", 50)
    base_score = 100 - kd  # KD 0 = 100 points, KD 100 = 0 points

    # Position bonus (if already ranking)
    position = row.get("client_position", row.get("position", 101))
    position_bonus = params["scoring"]["position_bonus"]

    if position <= 3:
        bonus = position_bonus["1-3"]
    elif position <= 10:
        bonus = position_bonus["4-10"]
    elif position <= 20:
        bonus = position_bonus["11-20"]
    elif position <= 50:
        bonus = position_bonus["21-50"]
    else:
        bonus = position_bonus["51+"]

    # Quick win bonus (from gap analysis)
    quick_win_bonus = 0
    if row.get("gap_category") == "quick_win":
        quick_win_bonus = 15
    elif row.get("gap_category") == "close_gap":
        quick_win_bonus = 20

    # Cap at 100
    ranking_prob = min(100, base_score + bonus + quick_win_bonus)

    return round(ranking_prob, 1)

df["ranking_probability"] = df.apply(lambda r: calculate_ranking_probability(r, params), axis=1)
```

### Ranking probability distribution

```python
print(f"Ranking probability stats:")
print(df["ranking_probability"].describe())
print(f"\nBy KD bucket:")
df["kd_bucket"] = pd.cut(df["kd"], bins=[0, 20, 40, 60, 80, 100], labels=["0-20", "20-40", "40-60", "60-80", "80-100"])
print(df.groupby("kd_bucket")["ranking_probability"].mean().round(1))
```

---

## 8.4 Traffic Potential Score

### CTR estimation

```python
def estimate_ctr(position: float, params: dict) -> float:
    """Estimate CTR based on position."""
    ctr_map = params["scoring"]["ctr_by_position"]

    if position <= 0 or position > 100:
        return 0.01  # Minimal CTR for not ranking

    pos_int = min(int(position), 10)
    return ctr_map.get(pos_int, 0.02)
```

### SERP feature loss

```python
def estimate_serp_loss(serp_features: list, params: dict) -> float:
    """Estimate CTR loss from SERP features."""
    loss_map = params["scoring"]["serp_feature_ctr_loss"]

    total_loss = 0
    for feature in serp_features:
        total_loss += loss_map.get(feature, 0)

    return min(0.5, total_loss)  # Cap at 50% loss
```

### Traffic potential calculation

```python
def calculate_traffic_potential(row: pd.Series, params: dict) -> float:
    """Calculate traffic potential score (0-100)."""
    volume = row.get("volume", 0)

    # Target position (current or estimated achievable)
    current_pos = row.get("client_position", row.get("position", 101))
    if current_pos <= 10:
        target_pos = max(1, current_pos - 2)  # Can improve by 2
    elif current_pos <= 20:
        target_pos = 8  # Target top 10
    else:
        target_pos = 10  # Optimistic target

    # CTR at target position
    ctr = estimate_ctr(target_pos, params)

    # SERP feature adjustment
    serp_features = row.get("serp_features", [])
    if isinstance(serp_features, str):
        serp_features = serp_features.split(",") if serp_features else []
    serp_loss = estimate_serp_loss(serp_features, params)

    # Estimated monthly traffic
    estimated_traffic = volume * ctr * (1 - serp_loss)

    # Normalize to 0-100 (log scale for volume)
    # Assuming max practical traffic is ~10000/month
    import math
    if estimated_traffic <= 0:
        traffic_score = 0
    else:
        traffic_score = min(100, math.log10(estimated_traffic + 1) * 25)

    return round(traffic_score, 1)

df["traffic_potential"] = df.apply(lambda r: calculate_traffic_potential(r, params), axis=1)
```

---

## 8.5 Composite Priority Score

### Calculate weighted score

```python
def calculate_priority_score(row: pd.Series, params: dict) -> float:
    """Calculate final priority score."""
    weights = params["scoring"]["weights"]

    score = (
        row["business_value"] * weights["business_value"] +
        row["ranking_probability"] * weights["ranking_probability"] +
        row["traffic_potential"] * weights["traffic_potential"]
    )

    return round(score, 1)

df["priority_score"] = df.apply(lambda r: calculate_priority_score(r, params), axis=1)
```

### Component contribution analysis

```python
# See which component contributes most
df["bv_contribution"] = df["business_value"] * params["scoring"]["weights"]["business_value"]
df["rp_contribution"] = df["ranking_probability"] * params["scoring"]["weights"]["ranking_probability"]
df["tp_contribution"] = df["traffic_potential"] * params["scoring"]["weights"]["traffic_potential"]

print("Average contribution by component:")
print(f"Business Value: {df['bv_contribution'].mean():.1f}")
print(f"Ranking Probability: {df['rp_contribution'].mean():.1f}")
print(f"Traffic Potential: {df['tp_contribution'].mean():.1f}")
```

---

## 8.6 Ranking and Segmentation

### Priority tiers

```python
def assign_priority_tier(score: float) -> str:
    """Assign priority tier based on score."""
    if score >= 70:
        return "P1_critical"
    elif score >= 55:
        return "P2_high"
    elif score >= 40:
        return "P3_medium"
    elif score >= 25:
        return "P4_low"
    else:
        return "P5_backlog"

df["priority_tier"] = df["priority_score"].apply(assign_priority_tier)
```

### Tier distribution

```python
tier_dist = df.groupby("priority_tier").agg({
    "keyword": "count",
    "volume": "sum",
    "priority_score": "mean"
}).round(1)

tier_dist["pct_keywords"] = (tier_dist["keyword"] / len(df) * 100).round(1)
tier_dist["pct_volume"] = (tier_dist["volume"] / df["volume"].sum() * 100).round(1)

print(tier_dist)
```

### Top opportunities

```python
top_100 = df.nlargest(100, "priority_score")[
    ["keyword", "volume", "kd", "intent", "priority_score", "priority_tier"]
]
print("Top 100 keywords by priority:")
print(top_100.head(20))
```

---

## 8.7 Validation

### Score distribution check

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

df["business_value"].hist(bins=20, ax=axes[0, 0])
axes[0, 0].set_title("Business Value Distribution")

df["ranking_probability"].hist(bins=20, ax=axes[0, 1])
axes[0, 1].set_title("Ranking Probability Distribution")

df["traffic_potential"].hist(bins=20, ax=axes[1, 0])
axes[1, 0].set_title("Traffic Potential Distribution")

df["priority_score"].hist(bins=20, ax=axes[1, 1])
axes[1, 1].set_title("Priority Score Distribution")

plt.tight_layout()
plt.savefig("data/interim/scoring_distributions.png")
```

### Sanity checks

```python
def validate_scoring(df: pd.DataFrame) -> dict:
    """Validate scoring results."""
    checks = {
        "score_range_valid": df["priority_score"].between(0, 100).all(),
        "high_intent_high_score": df[df["intent"] == "transactional"]["priority_score"].mean() > df["priority_score"].mean(),
        "low_kd_high_ranking_prob": df[df["kd"] < 30]["ranking_probability"].mean() > 50,
        "high_volume_high_traffic": df[df["volume"] > df["volume"].median()]["traffic_potential"].mean() > df["traffic_potential"].mean(),
        "tier_distribution_reasonable": 0.05 <= (df["priority_tier"] == "P1_critical").mean() <= 0.25
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"{check}: {status}")

    return checks
```

---

## 8.8 Output

### Main output

```python
output_columns = [
    "keyword",
    "keyword_normalized",
    "volume",
    "kd",
    "cluster_id",
    "cluster_name",
    "intent",
    "funnel",
    "relevance_score",
    "client_position",
    "competitor_position",
    "gap_category",
    "business_value",
    "ranking_probability",
    "traffic_potential",
    "priority_score",
    "priority_tier"
]

df_output = df[[c for c in output_columns if c in df.columns]]
df_output = df_output.sort_values("priority_score", ascending=False)
df_output.to_csv("data/interim/keywords_scored.csv", index=False)
```

### Priority summary

```python
summary = {
    "total_keywords": len(df),
    "avg_priority_score": df["priority_score"].mean(),
    "p1_count": (df["priority_tier"] == "P1_critical").sum(),
    "p2_count": (df["priority_tier"] == "P2_high").sum(),
    "p1_p2_volume": df[df["priority_tier"].isin(["P1_critical", "P2_high"])]["volume"].sum(),
    "p1_p2_volume_pct": df[df["priority_tier"].isin(["P1_critical", "P2_high"])]["volume"].sum() / df["volume"].sum() * 100
}

pd.Series(summary).to_csv("data/interim/scoring_summary.csv")
print(summary)
```

### Top keywords per tier

```python
for tier in ["P1_critical", "P2_high", "P3_medium"]:
    tier_df = df[df["priority_tier"] == tier].nlargest(20, "volume")
    tier_df[["keyword", "volume", "kd", "priority_score"]].to_csv(
        f"data/interim/top_{tier.lower()}.csv", index=False
    )
```

---

## src/scoring.py

```python
"""Weighted keyword prioritization scoring module."""

import math
from pathlib import Path

import pandas as pd
import yaml


def load_params(path: str = "params.yaml") -> dict:
    """Load scoring parameters."""
    with open(path) as f:
        return yaml.safe_load(f)


def calculate_business_value(
    intent: str,
    relevance: float,
    funnel: str,
    params: dict
) -> float:
    """Calculate business value score (0-100)."""
    intent_scores = params["scoring"]["intent_scores"]
    intent_score = intent_scores.get(intent, 3)

    funnel_conversion = {"BOFU": 1.0, "MOFU": 0.6, "TOFU": 0.3, "BRAND": 0.8}
    conversion = funnel_conversion.get(funnel, 0.3)

    return round(
        (intent_score / 10) * 40 +
        (relevance / 100) * 40 +
        conversion * 20,
        1
    )


def calculate_ranking_probability(
    kd: float,
    position: float,
    gap_category: str,
    params: dict
) -> float:
    """Calculate ranking probability score (0-100)."""
    base_score = 100 - kd

    pos_bonus = params["scoring"]["position_bonus"]
    if position <= 3:
        bonus = pos_bonus["1-3"]
    elif position <= 10:
        bonus = pos_bonus["4-10"]
    elif position <= 20:
        bonus = pos_bonus["11-20"]
    elif position <= 50:
        bonus = pos_bonus["21-50"]
    else:
        bonus = pos_bonus["51+"]

    quick_win_bonus = 20 if gap_category == "close_gap" else (15 if gap_category == "quick_win" else 0)

    return round(min(100, base_score + bonus + quick_win_bonus), 1)


def calculate_traffic_potential(volume: int, position: float) -> float:
    """Calculate traffic potential score (0-100)."""
    ctr_map = {1: 0.32, 2: 0.17, 3: 0.11, 4: 0.08, 5: 0.06,
               6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.02}

    target_pos = min(10, max(1, int(position) - 2)) if position <= 20 else 10
    ctr = ctr_map.get(target_pos, 0.02)
    traffic = volume * ctr

    if traffic <= 0:
        return 0
    return round(min(100, math.log10(traffic + 1) * 25), 1)


def calculate_priority_score(
    business_value: float,
    ranking_prob: float,
    traffic_pot: float,
    params: dict
) -> float:
    """Calculate final priority score."""
    w = params["scoring"]["weights"]
    return round(
        business_value * w["business_value"] +
        ranking_prob * w["ranking_probability"] +
        traffic_pot * w["traffic_potential"],
        1
    )


def assign_tier(score: float) -> str:
    """Assign priority tier."""
    if score >= 70:
        return "P1_critical"
    elif score >= 55:
        return "P2_high"
    elif score >= 40:
        return "P3_medium"
    elif score >= 25:
        return "P4_low"
    return "P5_backlog"


def main():
    """Run scoring pipeline."""
    import os

    params = load_params()

    # Load keywords - prefer clustered if exists
    if os.path.exists("data/interim/keywords_clustered.csv"):
        df = pd.read_csv("data/interim/keywords_clustered.csv")
    else:
        df = pd.read_csv("data/interim/keywords_categorized.csv")

    # Try to merge gap data
    try:
        gaps = pd.read_csv("data/interim/competitive_gaps.csv")
        df = df.merge(gaps[["keyword", "gap_category", "client_position", "competitor_position"]],
                      on="keyword", how="left")
    except FileNotFoundError:
        df["gap_category"] = None
        df["client_position"] = 101

    # Calculate scores
    df["business_value"] = df.apply(
        lambda r: calculate_business_value(
            r.get("intent", "informational"),
            r.get("relevance_score", 50),
            r.get("funnel", "TOFU"),
            params
        ), axis=1
    )

    df["ranking_probability"] = df.apply(
        lambda r: calculate_ranking_probability(
            r.get("kd", 50),
            r.get("client_position", 101),
            r.get("gap_category", ""),
            params
        ), axis=1
    )

    df["traffic_potential"] = df.apply(
        lambda r: calculate_traffic_potential(
            r.get("volume", 0),
            r.get("client_position", 101)
        ), axis=1
    )

    df["priority_score"] = df.apply(
        lambda r: calculate_priority_score(
            r["business_value"],
            r["ranking_probability"],
            r["traffic_potential"],
            params
        ), axis=1
    )

    df["priority_tier"] = df["priority_score"].apply(assign_tier)

    # Sort and save
    df = df.sort_values("priority_score", ascending=False)
    df.to_csv("data/interim/keywords_scored.csv", index=False)

    # Stats
    print(f"Scored {len(df)} keywords")
    print(f"Tier distribution:\n{df['priority_tier'].value_counts()}")


if __name__ == "__main__":
    main()
```

---

## Checklist

- [ ] Scoring parameters loaded
- [ ] Business value calculated
- [ ] Ranking probability calculated
- [ ] Traffic potential calculated
- [ ] Priority score computed
- [ ] Priority tiers assigned
- [ ] Score distributions validated
- [ ] Sanity checks passed
- [ ] Output files saved

---

## Očekávané výsledky

| Metrika | Typická hodnota |
|---------|-----------------|
| P1 (critical) | 5-15% |
| P2 (high) | 15-25% |
| P3 (medium) | 25-35% |
| P4 (low) | 20-30% |
| P5 (backlog) | 10-20% |
| P1+P2 volume share | 40-60% |

---

## Návaznost

**Další fáze**: Fáze 9 - Content Mapping

**Předává**:
- `data/interim/keywords_scored.csv`
- Scoring summary
- Top keywords per tier

---

*Framework version: 1.1*
*Aktualizováno: Vstupy z Fáze 5/6*

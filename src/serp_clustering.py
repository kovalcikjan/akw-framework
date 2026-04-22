"""Faze 6: SERP Clustering (optional).

Groups money keywords that share SERP results (>30% URL overlap).
Keywords in the same cluster should target the SAME page.

Requires SERP data (top 10 URLs per keyword) from Marketing Miner or Ahrefs.

Usage:
    python src/serp_clustering.py
    python src/serp_clustering.py --input data/interim/money_keywords.csv --serp-data data/raw/serp_results.csv
    python src/serp_clustering.py --threshold 0.3
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


SERP_COLUMN_ALIASES: dict[str, list[str]] = {
    "keyword": ["keyword", "keywords", "query", "kw"],
    "url": ["url", "result_url", "serp_url", "landing_page", "page"],
    "position": ["position", "pos", "rank", "serp_position"],
}


def load_params(project_root: Path) -> dict:
    """Load params.yaml."""
    params_path = project_root / "params.yaml"
    if params_path.exists():
        with open(params_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def normalize_serp_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map SERP data column names to standard schema."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rename_map: dict[str, str] = {}
    for standard, aliases in SERP_COLUMN_ALIASES.items():
        if standard in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (strip protocol, www, trailing slash)."""
    url = str(url).lower().strip()
    url = url.replace("https://", "").replace("http://", "")
    url = url.replace("www.", "")
    url = url.rstrip("/")
    return url


def load_serp_data(serp_path: Path) -> dict[str, set[str]]:
    """Load SERP data and return {keyword: set of top 10 URLs}."""
    if serp_path.suffix == ".xlsx":
        df = pd.read_excel(serp_path, engine="openpyxl")
    else:
        for encoding in ["utf-8", "utf-8-sig", "cp1250"]:
            try:
                df = pd.read_csv(serp_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

    df = normalize_serp_columns(df)

    if "keyword" not in df.columns or "url" not in df.columns:
        log.error("SERP data must have 'keyword' and 'url' columns. Found: %s", list(df.columns))
        sys.exit(1)

    # Filter top 10 per keyword
    if "position" in df.columns:
        df["position"] = pd.to_numeric(df["position"], errors="coerce")
        df = df[df["position"] <= 10]

    # Build keyword -> URLs mapping
    df["keyword_lower"] = df["keyword"].str.lower().str.strip()
    df["url_normalized"] = df["url"].apply(normalize_url)

    serp_map: dict[str, set[str]] = {}
    for kw, group in df.groupby("keyword_lower"):
        urls = set(group["url_normalized"].dropna().unique()[:10])
        if urls:
            serp_map[kw] = urls

    log.info("Loaded SERP data: %d keywords with URLs", len(serp_map))
    return serp_map


def compute_overlap_matrix(
    keywords: list[str], serp_map: dict[str, set[str]], max_results: int = 10
) -> np.ndarray:
    """Compute URL overlap matrix between all keyword pairs.

    Overlap = |intersection| / max_results (not Jaccard).
    """
    n = len(keywords)
    matrix = np.zeros((n, n))

    for i in range(n):
        urls_i = serp_map.get(keywords[i].lower(), set())
        for j in range(i + 1, n):
            urls_j = serp_map.get(keywords[j].lower(), set())
            if urls_i and urls_j:
                overlap = len(urls_i & urls_j) / max_results
            else:
                overlap = 0.0
            matrix[i][j] = overlap
            matrix[j][i] = overlap
        matrix[i][i] = 1.0

    return matrix


def cluster_keywords(
    keywords: list[str],
    overlap_matrix: np.ndarray,
    threshold: float = 0.3,
) -> dict[str, int]:
    """Cluster keywords based on URL overlap using hierarchical clustering."""
    # Convert similarity to distance
    distance_matrix = 1.0 - overlap_matrix
    np.fill_diagonal(distance_matrix, 0)

    # Ensure no negative values (floating point)
    distance_matrix = np.maximum(distance_matrix, 0)

    # Hierarchical clustering
    condensed = squareform(distance_matrix)
    linkage_matrix = linkage(condensed, method="average")
    clusters = fcluster(linkage_matrix, t=1.0 - threshold, criterion="distance")

    return dict(zip(keywords, clusters))


def name_clusters(
    cluster_assignments: dict[str, int], df: pd.DataFrame
) -> dict[int, str]:
    """Name each cluster by its highest-volume keyword."""
    cluster_names: dict[int, str] = {}
    kw_col = "keyword_normalized" if "keyword_normalized" in df.columns else "keyword"

    for cluster_id in set(cluster_assignments.values()):
        cluster_kws = [kw for kw, cid in cluster_assignments.items() if cid == cluster_id]
        cluster_df = df[df[kw_col].str.lower().isin([k.lower() for k in cluster_kws])]
        if "volume" in cluster_df.columns and len(cluster_df) > 0:
            best_kw = cluster_df.loc[cluster_df["volume"].idxmax(), kw_col]
        elif len(cluster_kws) > 0:
            best_kw = cluster_kws[0]
        else:
            best_kw = f"cluster_{cluster_id}"
        cluster_names[cluster_id] = best_kw

    return cluster_names


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SERP-based keyword clustering")
    parser.add_argument("--input", type=Path, default=Path("data/interim/money_keywords.csv"))
    parser.add_argument("--serp-data", type=Path, default=Path("data/raw/serp_results.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/keywords_clustered.csv"))
    parser.add_argument("--threshold", type=float, default=0.3, help="Min URL overlap for clustering (0.0-1.0)")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()

    # Load money keywords
    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        sys.exit(1)

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    log.info("Loaded %d money keywords", len(df))

    if len(df) < 2:
        log.warning("Not enough keywords to cluster (need at least 2)")
        df["cluster_id"] = 1
        df["cluster_name"] = df.iloc[0]["keyword_normalized"] if len(df) > 0 else ""
        df.to_csv(args.output, index=False, encoding="utf-8-sig")
        return

    # Load SERP data
    if not args.serp_data.exists():
        log.error("SERP data not found: %s", args.serp_data)
        log.error("Upload SERP results (top 10 URLs per keyword) to data/raw/")
        sys.exit(1)

    serp_map = load_serp_data(args.serp_data)

    # Match keywords to SERP data
    kw_col = "keyword_normalized" if "keyword_normalized" in df.columns else "keyword"
    keywords_with_serp = [
        kw for kw in df[kw_col].tolist()
        if kw.lower() in serp_map
    ]
    keywords_no_serp = [
        kw for kw in df[kw_col].tolist()
        if kw.lower() not in serp_map
    ]

    log.info("Keywords with SERP data: %d", len(keywords_with_serp))
    log.info("Keywords without SERP data: %d (will be unclustered)", len(keywords_no_serp))

    if len(keywords_with_serp) < 2:
        log.warning("Not enough keywords with SERP data to cluster")
        df["cluster_id"] = None
        df["cluster_name"] = ""
        df.to_csv(args.output, index=False, encoding="utf-8-sig")
        return

    # Compute overlap matrix
    log.info("Computing URL overlap matrix (%dx%d)...", len(keywords_with_serp), len(keywords_with_serp))
    overlap_matrix = compute_overlap_matrix(keywords_with_serp, serp_map)

    # Cluster
    log.info("Clustering (threshold=%.0f%% overlap)...", args.threshold * 100)
    cluster_assignments = cluster_keywords(keywords_with_serp, overlap_matrix, args.threshold)

    # Name clusters
    cluster_names = name_clusters(cluster_assignments, df)

    # Map back to dataframe
    df["cluster_id"] = None
    df["cluster_name"] = ""

    for idx in df.index:
        kw = df.loc[idx, kw_col]
        if kw in cluster_assignments:
            cid = cluster_assignments[kw]
            df.loc[idx, "cluster_id"] = cid
            df.loc[idx, "cluster_name"] = cluster_names.get(cid, "")

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    log.info("Saved: %s (%d keywords)", args.output, len(df))

    # Summary
    n_clusters = len(set(cluster_assignments.values()))
    sizes = pd.Series(list(cluster_assignments.values())).value_counts()
    log.info("=" * 50)
    log.info("CLUSTERING SUMMARY")
    log.info("=" * 50)
    log.info("Total clusters: %d", n_clusters)
    log.info("Avg cluster size: %.1f", sizes.mean())
    log.info("Max cluster size: %d", sizes.max())
    log.info("Single-keyword clusters: %d", (sizes == 1).sum())
    log.info("")
    log.info("Top 10 clusters:")
    for cid in sizes.head(10).index:
        name = cluster_names.get(cid, "?")
        size = sizes[cid]
        log.info("  [%d] %-40s %d keywords", cid, name, size)


if __name__ == "__main__":
    main()

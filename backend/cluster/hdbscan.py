def process_cluster_hdbscan(
    min_cluster_size=15,
    min_samples=3,
    use_umap=True
):
    """
    UMAP -> HDBSCAN（用于聚类）
    """
    import torch
    import numpy as np
    import matplotlib.pyplot as plt
    from sklearn.preprocessing import normalize
    from sklearn.decomposition import PCA

    try:
        import umap
    except ImportError:
        raise ImportError("请先安装 umap-learn")

    try:
        import hdbscan
    except ImportError:
        raise ImportError("请先安装 hdbscan")

    # =====================
    # 1. 读取 embedding
    # =====================
    ckpt_path = "embeddings_深圳金融工程学院.ckpt"
    ckpt = torch.load(ckpt_path, map_location="cpu")

    embeddings = ckpt["embeddings"].cpu().numpy()  # [N, D]
    keywords = ckpt.get("keywords", None)

    # 🔑 语义聚类必做：L2 normalize
    embeddings = normalize(embeddings, norm="l2")

    # =====================
    # 2. UMAP（用于聚类）
    # =====================
    reducer = umap.UMAP(
        n_neighbors=15,      # 小一点，更容易形成簇
        min_dist=0.0,        # 拉紧簇
        n_components=5,      # 给 HDBSCAN 用的低维空间
        metric="cosine",
        random_state=42
    )
    X_umap = reducer.fit_transform(embeddings)

    # =====================
    # 3. HDBSCAN（在 UMAP 空间）
    # =====================
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="leaf"
    )

    labels = clusterer.fit_predict(X_umap)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = np.sum(labels == -1)

    print(f"发现簇数: {n_clusters}")
    print(f"噪声点数: {n_noise}")

    # =====================
    # 4. 再降到 2D 仅用于可视化
    # =====================
    X_vis = PCA(n_components=2).fit_transform(X_umap)

    # =====================
    # 5. 可视化
    # =====================
    plt.figure(figsize=(8, 8))
    unique_labels = set(labels)

    for label in unique_labels:
        idx = labels == label
        if label == -1:
            plt.scatter(
                X_vis[idx, 0],
                X_vis[idx, 1],
                c="lightgray",
                s=15,
                label="Noise"
            )
        else:
            plt.scatter(
                X_vis[idx, 0],
                X_vis[idx, 1],
                s=30,
                label=f"Cluster {label}"
            )

    plt.title("UMAP → HDBSCAN (clustering)")
    plt.axis("off")
    plt.legend(markerscale=1.1)
    plt.show()

    return labels

  

def write_cluster_to_graph(
    graph_path,
    labels,
    output_path=None
):
    """
    将 HDBSCAN 的 labels 写回 graph.json 的 nodes[].group
    """
    if output_path is None:
        output_path = graph_path

    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph["nodes"]

    assert len(nodes) == len(labels), \
        f"节点数 {len(nodes)} 与 labels 数 {len(labels)} 不一致"

    for i, node in enumerate(nodes):
        node["group"] = int(labels[i])   # 直接覆盖 group

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"✅ 已写回 cluster 结果到 {output_path}")


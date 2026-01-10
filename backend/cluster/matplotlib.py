
import json
import torch
import numpy as np
import matplotlib.pyplot as plt
import umap
from sklearn.preprocessing import normalize
from scipy.spatial import ConvexHull
from collections import defaultdict


# =========================
# 配置
# =========================

CKPT_PATH = "embeddings_深圳金融工程学院.ckpt"
CLUSTER_JSON = "graph_深圳金融工程学院_leiden_mix.json"
OUTPUT_FIG = "cluster_boundary_vis_leiden_mix_25.png"

RANDOM_STATE = 42
POINT_SIZE = 30
ALPHA_POINT = 0.85
ALPHA_HULL = 0.18


# =========================
# 1. 读取 embedding
# =========================

print("🔹 加载 embedding...")
ckpt = torch.load(CKPT_PATH, map_location="cpu")

embeddings = ckpt["embeddings"].cpu().numpy()
embeddings = normalize(embeddings, norm="l2")

keywords = ckpt.get("keywords", None)


# =========================
# 2. UMAP 降维
# =========================

print("🔹 UMAP 降维到 2D...")
reducer = umap.UMAP(
    n_components=2,
    n_neighbors=25,
    min_dist=0.1,
    metric="cosine",
    random_state=RANDOM_STATE
)

X_2d = reducer.fit_transform(embeddings)


# =========================
# 3. 读取 Leiden 聚类结果
# =========================

print("🔹 加载聚类结果...")
with open(CLUSTER_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

cluster_ids = np.array([node["group"] for node in data["nodes"]])
unique_clusters = sorted(set(cluster_ids))

print(f"✅ Cluster 数量: {len(unique_clusters)}")


# =========================
# 4. 按 cluster 分组
# =========================

cluster_points = defaultdict(list)

for idx, cid in enumerate(cluster_ids):
    cluster_points[cid].append(X_2d[idx])

# 转 numpy
for k in cluster_points:
    cluster_points[k] = np.array(cluster_points[k])


# =========================
# 5. 可视化（带边界）
# =========================

print("🔹 绘制可视化...")

plt.figure(figsize=(14, 12))
cmap = plt.cm.get_cmap("tab20", len(unique_clusters))

for i, cid in enumerate(unique_clusters):
    pts = cluster_points[cid]
    color = cmap(i)

    # 画点
    plt.scatter(
        pts[:, 0],
        pts[:, 1],
        s=POINT_SIZE,
        color=color,
        alpha=ALPHA_POINT
    )

    # 至少 3 个点才画 hull
    if pts.shape[0] >= 3:
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices]

        plt.fill(
            hull_pts[:, 0],
            hull_pts[:, 1],
            color=color,
            alpha=ALPHA_HULL,
            linewidth=0
        )

    # cluster 中心
    center = pts.mean(axis=0)
    plt.text(
        center[0],
        center[1],
        f"Cluster {cid}",
        fontsize=11,
        weight="bold",
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.3",
            fc="white",
            ec=color,
            alpha=0.9
        )
    )

plt.title("Keyword Clustering with Real Cluster Boundaries", fontsize=16)
plt.axis("off")
plt.tight_layout()

plt.savefig(OUTPUT_FIG, dpi=300)
plt.show()

print(f"🎉 完成！输出文件: {OUTPUT_FIG}")

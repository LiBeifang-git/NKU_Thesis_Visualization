
import json
import torch
import numpy as np
import matplotlib.pyplot as plt
import umap
from sklearn.preprocessing import normalize
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import alphashape
from collections import defaultdict


# =========================
# 配置
# =========================

CKPT_PATH = "embeddings_深圳金融工程学院.ckpt"
CLUSTER_JSON = "graph_深圳金融工程学院_leiden_mix.json"
OUTPUT_FIG = "cluster_map_alpha_shape.png"

RANDOM_STATE = 42
POINT_SIZE = 10
ALPHA_REGION = 0.45
ALPHA_POINT = 0.85

# Alpha Shape 参数
ALPHA_SCALE = 1.6      # ↑ 越大越保守（区域更圆）
BUFFER_RADIUS = 0.06   # 微调平滑


# =========================
# 1. 读取 embedding
# =========================

print("🔹 加载 embedding...")
ckpt = torch.load(CKPT_PATH, map_location="cpu")

embeddings = ckpt["embeddings"].cpu().numpy()
embeddings = normalize(embeddings, norm="l2")


# =========================
# 2. UMAP 降维
# =========================

print("🔹 UMAP 降维到 2D...")
reducer = umap.UMAP(
    n_components=2,
    n_neighbors=15,
    min_dist=0.1,
    metric="cosine",
    random_state=RANDOM_STATE
)

X_2d = reducer.fit_transform(embeddings)


# =========================
# 3. 读取聚类结果
# =========================

print("🔹 加载聚类结果...")
with open(CLUSTER_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

cluster_ids = np.array([node["group"] for node in data["nodes"]])


# =========================
# 4. 按 cluster 分组
# =========================

clusters = defaultdict(list)
for i, cid in enumerate(cluster_ids):
    if cid != -1:   # 跳过噪声
        clusters[cid].append(X_2d[i])

print(f"✅ Cluster 数量: {len(clusters)}")


# =========================
# 5. Alpha Shape 构建
# =========================

cluster_regions = {}

print("🔹 计算 Alpha Shape...")
for cid, pts in clusters.items():
    pts = np.array(pts)

    # 少点直接用凸包
    if len(pts) < 4:
        region = Polygon(pts).convex_hull
        cluster_regions[cid] = region
        continue

    # 🔑 自适应 alpha（基于点间距）
    dists = np.linalg.norm(
        pts[:, None, :] - pts[None, :, :], axis=-1
    )
    median_dist = np.median(dists[dists > 0])
    alpha = ALPHA_SCALE / median_dist

    shape = alphashape.alphashape(pts, alpha)

    if shape.is_empty:
        shape = Polygon(pts).convex_hull

    # 形态学平滑（去毛刺）
    shape = shape.buffer(BUFFER_RADIUS).buffer(-BUFFER_RADIUS)

    cluster_regions[cid] = shape


# =========================
# 6. 绘制地图式可视化
# =========================

print("🔹 绘制地图式可视化...")

plt.figure(figsize=(14, 12))
cmap = plt.cm.get_cmap("tab20")

def draw_region(region, color):
    if isinstance(region, Polygon):
        polys = [region]
    elif isinstance(region, MultiPolygon):
        polys = list(region.geoms)
    else:
        return

    for poly in polys:
        x, y = poly.exterior.xy
        plt.fill(x, y, color=color, alpha=ALPHA_REGION, linewidth=0)

for i, (cid, region) in enumerate(cluster_regions.items()):
    draw_region(region, cmap(i % 20))

# 原始点
plt.scatter(
    X_2d[:, 0],
    X_2d[:, 1],
    s=POINT_SIZE,
    c=[cmap(cid % 20) if cid != -1 else "#999999" for cid in cluster_ids],
    alpha=ALPHA_POINT,
    zorder=5
)

plt.title("Map-style Cluster Visualization (Alpha Shape)", fontsize=16)
plt.axis("off")
plt.tight_layout()
plt.savefig(OUTPUT_FIG, dpi=300)
plt.show()

print(f"🎉 完成！输出文件: {OUTPUT_FIG}")

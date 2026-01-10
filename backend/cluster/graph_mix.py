
import json
import math
import torch
import igraph as ig
import leidenalg
import numpy as np
from pyvis.network import Network
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from cluster.gpt import *

# =========================
# 配置参数（你主要调这里）
# =========================

import os

# =========================
# 批量处理路径配置
# =========================


OUTPUT_SUFFIX = "_leiden_mix"


# —— 语义边参数 ——
KNN_K = 15                  # 每个关键词连几个语义邻居
SEM_WEIGHT = 0.8            # 语义边权重系数

# —— 共现边参数 ——
SIM_THRESHOLD = 0.15
WEIGHT_POWER = 2.0
CO_WEIGHT = 0.6            # 共现边权重系数

# —— Leiden 参数 ——
RESOLUTION = 0.6
# =========================
# 1. 构图：embedding + 共现
# =========================

def build_graph_with_semantic_edges(json_path, ckpt_path):
    # ---------- 读取 JSON ----------
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ---------- 读取 embedding ----------
    ckpt = torch.load(ckpt_path, map_location="cpu")
    embeddings = ckpt["embeddings"].cpu().numpy()   # [N, D]

    # 🔑 语义聚类必做
    embeddings = normalize(embeddings, norm="l2")

    # ---------- 建立节点 ----------
    g = ig.Graph()
    id_map = {}

    for idx, node in enumerate(data["nodes"]):
        id_map[node["id"]] = idx
        g.add_vertex(
            name=str(node["id"]),
            label=node.get("label", "")
        )

    edge_dict = {}  # (i, j) -> weight

    # =========================
    # 1️⃣ 共现边（JSON 原有）
    # =========================
    for link in data["links"]:
        sim = link.get("value", 0.0)
        cnt = link.get("count", 1)

        if sim < SIM_THRESHOLD:
            continue

        i = id_map[link["source"]]
        j = id_map[link["target"]]

        w = (sim ** WEIGHT_POWER) * (1 + math.log1p(cnt))
        edge_dict[(i, j)] = edge_dict.get((i, j), 0.0) + CO_WEIGHT * w

    # =========================
    # 2️⃣ 语义 KNN 边（embedding）
    # =========================
    knn = NearestNeighbors(
        n_neighbors=KNN_K + 1,
        metric="cosine"
    ).fit(embeddings)

    distances, indices = knn.kneighbors(embeddings)

    for i in range(len(embeddings)):
        for j_idx, dist in zip(indices[i][1:], distances[i][1:]):
            j = j_idx
            sim = 1 - dist   # cosine similarity

            w = SEM_WEIGHT * sim
            key = (min(i, j), max(i, j))
            edge_dict[key] = edge_dict.get(key, 0.0) + w

    # =========================
    # 3️⃣ 写入 igraph
    # =========================
    edges = []
    weights = []

    for (i, j), w in edge_dict.items():
        edges.append((i, j))
        weights.append(w)

    g.add_edges(edges)
    g.es["weight"] = weights

    return g, id_map,edge_dict


# =========================
# 2. Leiden 聚类
# =========================

def leiden_clustering(g, resolution=1.0):
    partition = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=resolution
    )
    return partition.membership


# =========================
# 3. 聚类结果写回 JSON
# =========================
import json
from collections import defaultdict, Counter
def write_clusters_to_json(input_path, output_path, id_map, membership, label_len,top_k=10):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # group -> Counter(label)
    cluster_keyword_counter = defaultdict(Counter)

    # =======================
    # 1️⃣ 写回 group + 统计关键词
    # =======================
    for node in data["nodes"]:
        node_id = node["id"]
        group = int(membership[id_map[node_id]])
        node["group"] = group

        label = node.get("label")
        if label:
            weight = node.get("size", 1)  # 兜底，防止没有 size
            cluster_keyword_counter[group][label] += weight

    # =======================
    # 2️⃣ 组织 cluster_stats（全量统计）
    # =======================
    cluster_stats = {}
    for group, counter in cluster_keyword_counter.items():
        cluster_stats[str(group)] = {
            "total": sum(counter.values()),
            "keywords": dict(counter)
        }

    # =======================
    # 3️⃣ 组织 Top-K list（你新要的）利用大模型给出关键词
    # =======================
    cluster_top_keywords = {}
    for group, counter in cluster_keyword_counter.items():
        topk_list = [kw for kw, _ in counter.most_common(min(len(counter),top_k))]
        cluster_top_keywords[str(group)] = topk_list
    print(cluster_top_keywords)
    lables=extract_cluster_kw(str(cluster_top_keywords),label_len)
   
    # =======================
    # 4️⃣ 写回 JSON（两件事都保留）
    # =======================
    data["cluster_stats"] = cluster_stats
    data["cluster_labels"]=lables

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 4. 可视化
# =========================

def main_college(name):
    JSON_DIR = fr"E:\大五上学期选修课\keshi\final_work\frontend\src\json\{name}"
    EMB_DIR  = fr"E:\大五上学期选修课\keshi\final_work\backend\index\{name}"

    print(f"🔹 批量处理 {name} JSON + Embedding")

    json_files = [
        f for f in os.listdir(JSON_DIR)
        if f.endswith(".json")
    ]

    print(f"📁 发现 {len(json_files)} 个 JSON 文件")

    for json_file in json_files:
        json_path = os.path.join(JSON_DIR, json_file)

        # ---- 推断年份或后缀 ----
        base_name = os.path.splitext(json_file)[0]
        # 例：金融学院_2020

        ckpt_name = f"embeddings_{base_name}.ckpt"
        ckpt_path = os.path.join(EMB_DIR, ckpt_name)

        if not os.path.exists(ckpt_path):
            print(f"⚠️ 缺少 embedding：{ckpt_name}，跳过")
            continue
        
        OUTPUT_SUBDIR = "leiden_output"
        output_dir = os.path.join(JSON_DIR, OUTPUT_SUBDIR)
        os.makedirs(output_dir, exist_ok=True)

        output_json = os.path.join(
            output_dir,
            f"{base_name}{OUTPUT_SUFFIX}.json"
        )

        print(f"\n▶ 处理：{json_file}")
        print(f"   ↳ Embedding: {ckpt_name}")

        # =========================
        # 1. 构图
        # =========================
        g, id_map, edge_dict = build_graph_with_semantic_edges(
            json_path,
            ckpt_path
        )

        print(f"   节点数: {g.vcount()}, 边数: {g.ecount()}")

        # =========================
        # 2. Leiden
        # =========================
        membership = leiden_clustering(g, RESOLUTION)
        n_cluster = len(set(membership))
        print(f"   社区数: {n_cluster}")

        # =========================
        # 3. 写回 JSON
        # =========================
        write_clusters_to_json(
            json_path,
            output_json,
            id_map,
            membership,
            label_len=n_cluster
        )

        print(f"   ✅ 输出: {output_json}")

    print("\n🎉 全部文件处理完成")


def visualize_graph_with_clusters(json_path, edge_dict, id_map, output_html):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="black"
    )

    # ====== 1️⃣ 物理引擎（决定“放到一片去”）======
    net.force_atlas_2based(
        gravity=-50,
        central_gravity=0.01,
        spring_length=120,
        spring_strength=0.08,
        damping=0.4,
        overlap=0
    )

    # ====== 2️⃣ 节点（颜色 = 簇）======
    for node in data["nodes"]:
        net.add_node(
            node["id"],
            label=node["label"],
            group=node["group"],   # 🔑 同簇同色
            size=14 + node.get("size", 1),
            title=f"Cluster {node['group']}"
        )

    # ====== 3️⃣ 边（共现 + 语义）======
    for (i, j), w in edge_dict.items():
        source = int(list(id_map.keys())[list(id_map.values()).index(i)])
        target = int(list(id_map.keys())[list(id_map.values()).index(j)])

        net.add_edge(
            source,
            target,
            value=w,
            color="rgba(180,180,180,0.4)"
        )

    net.write_html(output_html)

# =========================
# 5. 主流程
# =========================

def main():
    print("🔹 构建融合图（语义 + 共现）...")
    g, id_map, edge_dict = build_graph_with_semantic_edges(INPUT_JSON, CKPT_PATH)

    print(f"🔹 节点数: {g.vcount()}, 边数: {g.ecount()}")

    print("🔹 执行 Leiden 聚类...")
    membership = leiden_clustering(g, RESOLUTION)

    print(f"✅ 社区数: {len(set(membership))}")

    print("🔹 写回 JSON...")
    write_clusters_to_json(INPUT_JSON, OUTPUT_JSON, id_map, membership,len(set(membership)))

    print("🔹 生成可视化...")
    #visualize_graph_with_clusters(OUTPUT_JSON, edge_dict, id_map, OUTPUT_HTML)

    print("🎉 完成")
    #print(f"👉 {OUTPUT_HTML}")


if __name__ == "__main__":
    main_college("化学学院")

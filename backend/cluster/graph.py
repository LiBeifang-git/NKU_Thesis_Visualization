"""
Graph-based keyword clustering using:
- cosine similarity as edge weight
- Leiden community detection
- PyVis visualization

Author: ChatGPT
"""

import json
import math
import igraph as ig
import leidenalg
from pyvis.network import Network


# =========================
# 配置参数（你主要调这里）
# =========================

INPUT_JSON = "graph_深圳金融工程学院.json"
OUTPUT_JSON = "graph_深圳金融工程学院_leiden.json"
OUTPUT_HTML = "graph_深圳金融工程学院_leiden_vis.html"

SIM_THRESHOLD = 0.25          # 过滤弱相似度边
WEIGHT_POWER = 2.0            # 余弦相似度非线性拉伸
RESOLUTION = 1.0              # Leiden 分辨率


# =========================
# 1. JSON -> igraph
# =========================

def load_graph_igraph(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    g = ig.Graph()
    id_map = {}

    # 添加节点
    for idx, node in enumerate(data["nodes"]):
        id_map[node["id"]] = idx
        g.add_vertex(
            name=str(node["id"]),
            label=node.get("label", "")
        )

    edges = []
    weights = []

    # 添加边（余弦相似度作为权重）
    for link in data["links"]:
        sim = link.get("value", 0.0)
        cnt = link.get("count", 1)

        if sim < SIM_THRESHOLD:
            continue

        s = id_map[link["source"]]
        t = id_map[link["target"]]

        # 权重设计：语义 + 共现
        weight = (sim ** WEIGHT_POWER) * (1 + math.log1p(cnt))

        edges.append((s, t))
        weights.append(weight)

    g.add_edges(edges)
    g.es["weight"] = weights

    return g, id_map


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

def write_clusters_to_json(input_path, output_path, id_map, membership):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for node in data["nodes"]:
        idx = id_map[node["id"]]
        node["group"] = int(membership[idx])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 4. 交互式可视化（PyVis）
# =========================

def visualize_graph(json_path, output_html):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    net = Network(
        height="850px",
        width="100%",
        bgcolor="#ffffff",
        font_color="black",
        notebook=False
    )

    # 节点
    for node in data["nodes"]:
        net.add_node(
            node["id"],
            label=node["label"],
            group=node["group"],
            size=12 + node.get("size", 1),
            title=f"Cluster {node['group']}"
        )

    # 边
    for link in data["links"]:
        net.add_edge(
            link["source"],
            link["target"],
            value=link.get("value", 1.0)
        )

    net.write_html(output_html)



# =========================
# 5. 主流程
# =========================

def main():
    print("🔹 加载图数据...")
    g, id_map = load_graph_igraph(INPUT_JSON)

    print(f"🔹 图节点数: {g.vcount()}, 边数: {g.ecount()}")

    print("🔹 执行 Leiden 社区发现...")
    membership = leiden_clustering(g, resolution=RESOLUTION)

    n_clusters = len(set(membership))
    print(f"✅ 发现社区数: {n_clusters}")

    print("🔹 写回聚类结果到 JSON...")
    write_clusters_to_json(INPUT_JSON, OUTPUT_JSON, id_map, membership)

    print("🔹 生成交互式可视化...")
    visualize_graph(OUTPUT_JSON, OUTPUT_HTML)

    print("🎉 完成！")
    print(f"👉 聚类结果: {OUTPUT_JSON}")
    print(f"👉 可视化文件: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()

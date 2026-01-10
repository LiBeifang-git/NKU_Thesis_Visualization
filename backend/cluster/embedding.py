# 字符串转向量示例
import os
from openai import OpenAI
import torch
from collections import Counter, defaultdict
# 推荐使用API中转服务，兼容OpenAI接口
client = OpenAI(
    api_key="sk-zk2f2cbe611ff420bc71ad165792f32229966e8e7463758c", # 填入您的密钥
    base_url="https://api.zhizengzeng.com/v1" # 指向中转API地址
)
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

import numpy as np
from cluster.config import *
from crawl.thesis_db import *
from collections import Counter
db = ThesisDB()
titles = []
embeddings_list = []

import csv
import numpy as np
import time
from itertools import combinations
import json


def get_embedding(text, model="text-embedding-3-large"):
   text = text.replace("\\n", " ")
   return client.embeddings.create(input=[text], model=model).data[0].embedding


def process_keywords(keywords_list,college,year,file_path):

    all_keywords=[]
    edges=[]
    for kw_str in keywords_list:
        # 替换中文分号为英文分号，然后拆分
        parts = kw_str.replace('；', ';').split(';')
        # 去掉每个词中的所有空格，并过滤空字符串
        parts = [k.replace(' ', '') for k in parts if k.replace(' ', '')]
        parts = list(set(parts))
        all_keywords.extend(parts)
        # 建立同组关键词之间的边（两两组合）
        for s, t in combinations(parts, 2):
            edges.append((s, t))
    unique_keywords = sorted(set(all_keywords))
    print("unique_kw:",len(unique_keywords))# 取得一年中所有的唯一关键词
    # 保存文本 <-> index 对应关系
    keyword_to_idx = {kw: i for i, kw in enumerate(unique_keywords)}
    idx_to_keyword = {i: kw for kw, i in keyword_to_idx.items()}

    embeddings = np.zeros((len(unique_keywords), 3072), dtype="float32")

    for kw, idx in keyword_to_idx.items():
        embeddings[idx] = get_embedding(kw)
        print(f"{kw}编码成功！")

    embeddings = normalize(embeddings, axis=1)
    embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32)

    #保存embedding
    folder_path = fr"E:\大五上学期选修课\keshi\final_work\backend\index\{college}"
    # 如果不存在就创建
    os.makedirs(folder_path, exist_ok=True)
    # 保存 ckpt 文件
    emd_path = os.path.join(folder_path, f"embeddings_{college}_{year}.ckpt")
    torch.save({
        "embeddings": embeddings_tensor,
        "keywords": unique_keywords,
    }, emd_path)

    #存初始图
    # 统计无向边出现次数
    edge_counts = Counter(frozenset((s, t)) for s, t in edges)

    # 去重，生成 links
    links = []
    for edge_frozen, count in edge_counts.items():
        
        s, t = list(edge_frozen)
        idx_s = keyword_to_idx[s]
        idx_t = keyword_to_idx[t]
        sim = cosine_similarity(
            embeddings[idx_s].reshape(1, -1),
            embeddings[idx_t].reshape(1, -1)
        )[0][0]
        links.append({
            "source": idx_s,
            "target": idx_t,
            "value": float(sim),
            "count": count   # 新增出现次数属性
        })
        print(f"source:{idx_s}, target:{idx_t}, value:{sim}, size:{count}")

    kw_counts = Counter(all_keywords)
    nodes = []
    for idx in range(len(unique_keywords)):
        kw = idx_to_keyword[idx]
        nodes.append({
            "id": idx,            # 唯一索引
            "label": kw,          # 关键词
            "group": -2,
            "size": kw_counts.get(kw, 1)
        })


    save_path = os.path.join(file_path, f"{college}_{year}.json")
    graph = {"nodes": nodes, "links": links}
    add_graph=process_teachers(college,year)
    graph.update(add_graph)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)


from collections import Counter, defaultdict

def process_teachers(college,year):
    # 假设 result 是 [(导师姓名, 中文关键词字符串), ...]
    result = db.get_first_advisor_keywords_by_department_and_year(college, year)

    # 1. 清洗并整理每位导师的关键词
    advisor_keywords = defaultdict(list)
    for advisor, kw_str in result:
        parts = kw_str.replace('；', ';').split(';')
        clean_parts = [k.replace(' ', '') for k in parts if k.replace(' ', '')]
        advisor_keywords[advisor].extend(clean_parts)

    # 2. 构建 top5_advisors 字典
    advisor_stats = []
    for advisor, kw_list in advisor_keywords.items():
        total_count = len(kw_list)  # 关键词总数
        kw_counter = Counter(kw_list)
        if kw_counter:
            max_freq = kw_counter.most_common(1)[0][1]  # 出现频率最高的次数
        else:
            max_freq = 0
        advisor_stats.append({
            "advisor": advisor,
            "total_keywords": total_count,
            "max_keyword_freq": max_freq,
            "keywords_counter": kw_counter  # 可选，保留完整计数
        })

    # 3. 按关键词总数排序，取前五
    top5_advisors = sorted(advisor_stats, key=lambda x: x["total_keywords"], reverse=True)[:5]

    # 4. 构建 graph 的 advisor_keywords 字段
    graph_advisor_keywords = {}
    for entry in top5_advisors:
        top10_keywords = entry["keywords_counter"].most_common(10)
        graph_advisor_keywords[entry["advisor"]] = {
            "total_keywords": entry["total_keywords"],
            "top10_keywords": top10_keywords
        }

    # top5_advisors 已经是前五导师的列表
    top5teacher_list = [entry["advisor"] for entry in top5_advisors]

    # 更新 graph
    graph = {
        "advisor_keywords": graph_advisor_keywords,
        "top5teacher": top5teacher_list
    }
    print(graph)
    return graph

def process_college(name,start,end):
    base_path = r"E:\大五上学期选修课\keshi\final_work\frontend\src\json"
    target_path = os.path.join(base_path, name)

    # 如果不存在就创建，存在不会报错
    os.makedirs(target_path, exist_ok=True)
    print(f"目录已确认存在：{target_path}")
    for y in range(start,end+1,1):
        ans=db.get_keywords_by_department_and_year(name,y) 
        process_keywords(ans,name,y,target_path)
    
if __name__=='__main__':
    college_info=db.keyword_count_by_year(db.get_keywords_with_year_by_department("化学学院")) #计算学院每一年有多少关键词
    #ans=db.get_all_departments()
    print(college_info)

    #process_college("金融学院",)
    process_college("化学学院",2020,2024)



    

   






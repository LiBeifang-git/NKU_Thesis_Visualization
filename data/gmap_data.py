
import pymysql
import itertools
import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from collections import Counter, defaultdict
import math
import sys
import re
import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'WaterCloset1nk',
    'database': 'nk_thesis',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

MODEL_PATH = './models/Qwen3-Embedding-0.6B'
OUTPUT_DOT_FILE = "thesis_keywords_sparse.dot"

CURRENT_YEAR = datetime.datetime.now().year
START_YEAR = 2019

SQL_QUERY = "SELECT `中文关键词`, `院系` FROM thesis_detail WHERE `学位年度` >= %s"

MIN_KEYWORD_FREQ = 10      
MIN_EDGE_FREQ = 2          
SIMILARITY_THRESHOLD = 0 

MAX_LEN_LIMIT = 3.0      
MIN_LEN_LIMIT = 0.5      
FONT_SIZE_BASE = 10.0
FONT_SIZE_SCALE = 0.8

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def load_model():
    print(f"正在加载模型: {MODEL_PATH} ...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
        model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True)
        model.eval()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        return tokenizer, model, device
    except Exception as e:
        print(f"模型加载失败: {e}")
        sys.exit(1)

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def get_embeddings(texts, tokenizer, model, device, batch_size=64):
    all_embeddings = []
    total = len(texts)
    if total == 0: return np.array([])
    
    print(f"开始计算 {total} 个关键词的 Embeddings...")
    for i in range(0, total, batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_input = tokenizer(batch_texts, padding=True, truncation=True, return_tensors='pt').to(device)
        with torch.no_grad():
            model_output = model(**encoded_input)
        sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
        all_embeddings.append(sentence_embeddings.cpu().numpy())
        if (i + batch_size) % 1000 == 0:
            print(f"已处理 {i + batch_size}/{total}")
            
    return np.vstack(all_embeddings) if all_embeddings else np.array([])

def clean_keywords(keyword_str):
    if not keyword_str: return []
    parts = re.split(r'[;；,，\s]+', keyword_str)
    return [k.strip() for k in parts if k.strip()]

def main():
    print(f"正在连接数据库读取数据 ({START_YEAR}年至今)...")
    conn = get_db_connection()
    
    keywords_college_map = defaultdict(Counter)
    keyword_counts = Counter()
    edge_counts = Counter()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(SQL_QUERY, (str(START_YEAR),))
            rows = cursor.fetchall()
            print(f"获取到 {len(rows)} 篇论文数据")
            
            for row in rows:
                raw_kws = row.get('中文关键词', '')
                college_name = row.get('院系', '未知学院')
                kws = clean_keywords(raw_kws)
                
                if not kws: continue

                for kw in kws:
                    keyword_counts[kw] += 1
                    keywords_college_map[kw][college_name] += 1

                if len(kws) > 1:
                    sorted_kws = sorted(kws)
                    for u, v in itertools.combinations(sorted_kws, 2):
                        edge_counts[(u, v)] += 1
                        
    finally:
        conn.close()

    print("正在筛选节点...")
    valid_keywords = {k for k, v in keyword_counts.items() if v >= MIN_KEYWORD_FREQ}
    print(f"保留关键词数量: {len(valid_keywords)}")
    
    if len(valid_keywords) == 0:
        print("错误：没有关键词满足频次要求。")
        return

    all_colleges = set()
    for kw in valid_keywords:
        all_colleges.update(keywords_college_map[kw].keys())
    college_to_id = {c: i+1 for i, c in enumerate(sorted(list(all_colleges)))}
    
    keyword_cluster = {}
    for kw in valid_keywords:
        most_common = keywords_college_map[kw].most_common(1)[0][0]
        keyword_cluster[kw] = college_to_id.get(most_common, 0)

    kw_list = sorted(list(valid_keywords))
    kw_to_idx = {kw: i for i, kw in enumerate(kw_list)}
    
    tokenizer, model, device = load_model()
    embeddings = get_embeddings(kw_list, tokenizer, model, device)
    
    print(f"正在生成 .dot 文件 (仅保留相似度 > {SIMILARITY_THRESHOLD} 的连线)...")

    connected_nodes = set()
    valid_edges = []

    for (u, v), freq in edge_counts.items():
        if u in valid_keywords and v in valid_keywords:

            if freq < MIN_EDGE_FREQ:
                continue

            idx_u = kw_to_idx[u]
            idx_v = kw_to_idx[v]
            
            vec_u = embeddings[idx_u]
            vec_v = embeddings[idx_v]
            similarity = np.dot(vec_u, vec_v)

            if similarity < SIMILARITY_THRESHOLD:
                continue

            sim_val = max(float(similarity), 0.01)
            length = 1.0 / sim_val
            length = max(min(length, MAX_LEN_LIMIT), MIN_LEN_LIMIT)
            
            valid_edges.append((u, v, length))
            connected_nodes.add(u)
            connected_nodes.add(v)

    with open(OUTPUT_DOT_FILE, 'w', encoding='utf-8') as f:
        f.write("graph G {\n")
        f.write('  node [fontname="SimHei"];\n') 

        for kw in kw_list:
            if kw in connected_nodes:
                freq = keyword_counts[kw]
                cluster_id = keyword_cluster[kw]
                fontsize = FONT_SIZE_BASE + math.log(freq) * 5 * FONT_SIZE_SCALE
                fontsize = min(fontsize, 50.0)
                f.write(f'  "{kw}" [label="{kw}", fontsize={fontsize:.2f}, cluster={cluster_id}];\n')

        for u, v, length in valid_edges:
            f.write(f'  "{u}" -- "{v}" [len={length:.4f}];\n')
            
        f.write("}\n")
        
    print(f"完成！生成了 {len(connected_nodes)} 个节点和 {len(valid_edges)} 条高置信度连线。")
    print(f"已过滤掉相似度 < {SIMILARITY_THRESHOLD} 的弱连接。")

if __name__ == "__main__":
    main()
import os
import sys
import pandas as pd
import numpy as np
import mysql.connector
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm  

MODEL_PATH = "./models/Qwen3-Embedding-0.6B" 

DB_CONFIG = {
    'host': '10.130.36.92',
    'user': 'root',
    'password': 'cjy20030306yuE',  
    'database': 'nk_thesis'
}

BENCHMARK_FILE = 'papers.csv'      
MIT_FILE = 'mit_cs_theses.csv'      
OUTPUT_FILE = 'public/final_data.csv' 

TARGET_COLLEGES = [
    "计算机学院",
    "网络空间安全学院"
]

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class QwenEmbedder:
    def __init__(self, model_path, device):
        print(f"正在加载模型: {model_path} 到 {device}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, padding_side='left')
            self.model = AutoModel.from_pretrained(model_path, trust_remote_code=True).to(device)
            self.model.eval() # 开启评估模式
            self.device = device
        except Exception as e:
            print(f"模型加载失败: {e}")
            sys.exit(1)

    def _last_token_pool(self, last_hidden_states, attention_mask):
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

    def encode(self, texts, batch_size=8, task_instruction=None):
        all_embeddings = []
        if task_instruction:
            processed_texts = [f"Instruct: {task_instruction}\nQuery: {t}" for t in texts]
        else:
            processed_texts = texts

        print(f"开始计算向量 (共 {len(processed_texts)} 条)")
        
        for i in tqdm(range(0, len(processed_texts), batch_size), desc="Embedding"):
            batch_texts = processed_texts[i : i + batch_size]
            batch_dict = self.tokenizer(
                batch_texts, 
                max_length=4096, 
                padding=True, 
                truncation=True, 
                return_tensors='pt'
            )
            batch_dict = {k: v.to(self.device) for k, v in batch_dict.items()}
            
            with torch.no_grad():
                outputs = self.model(**batch_dict)

            embeddings = self._last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
            all_embeddings.append(embeddings.cpu().numpy())
            
        return np.concatenate(all_embeddings, axis=0)

def get_nankai_data():
    print("连接数据库")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        format_strings = ','.join(['%s'] * len(TARGET_COLLEGES))
        query = f"""
            SELECT 
                学位年度 as year, 
                中文标题 as title, 
                中文摘要 as abstract, 
                院系 as college,
                作者 as author,
                第一导师姓名 as supervisor
            FROM thesis_detail 
            WHERE 学位年度 >= 2019 AND 院系 IN ({format_strings})
        """
        cursor.execute(query, tuple(TARGET_COLLEGES))
        rows = cursor.fetchall()
        conn.close()
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df[df['abstract'].str.len() > 20].copy()
        
        print(f"获取到 {len(df)} 条数据")
        return df
    except Exception as e:
        print(f"数据库读取失败: {e}")
        return pd.DataFrame()

def get_mit_data():
    print("读取 CSV")
    try:
        df = pd.read_csv(MIT_FILE)
        df = df.rename(columns={'Year': 'year', 'Title': 'title', 'Abstract': 'abstract'})
        df['college'] = 'MIT CSAIL'
        df['author'] = 'MIT Student'
        df['supervisor'] = 'MIT Advisor'
        df = df[df['abstract'].notna() & (df['abstract'].str.len() > 20)].copy()
        print(f"获取到 {len(df)} 条数据")
        return df
    except Exception as e:
        print(f"读取失败: {e}")
        return pd.DataFrame()

def get_benchmark_data():
    print("读取基准论文")
    df = pd.read_csv(BENCHMARK_FILE)
    df = df[df['Abstract'].notna() & (df['Abstract'] != 'No Abstract')].copy()
    domain_map = {
        'AI (cs.AI)': 'AI', 'Computer Vision (cs.CV)': 'CV',
        'Databases (cs.DB)': 'Database', 'Machine Learning (cs.LG)': 'ML',
        'NLP (cs.CL)': 'NLP', 'Networking (cs.NI)': 'Network',
        'Operating Systems (cs.OS)': 'OS', 'Robotics (cs.RO)': 'Robotics',
        'Security (cs.CR)': 'Security', 'Software Engineering (cs.SE)': 'SE'
    }
    df['clean_domain'] = df['Domain'].map(domain_map).fillna(df['Domain'])
    return df

def main():
    embedder = QwenEmbedder(MODEL_PATH, DEVICE)

    df_nk = get_nankai_data()
    df_mit = get_mit_data()
    df_bench = get_benchmark_data()

    df_targets = pd.concat([df_nk, df_mit], ignore_index=True)
    if df_targets.empty:
        return

    print("\n⚡ [1/3] 计算 Benchmark 向量库")
    bench_cache = {}
    all_bench_vecs = embedder.encode(df_bench['Abstract'].tolist(), batch_size=4) 
    df_bench['vec_idx'] = range(len(df_bench))
    for year, group in df_bench.groupby('Query_Year'):
        bench_cache[year] = {
            'vectors': all_bench_vecs[group['vec_idx'].values],
            'domains': group['clean_domain'].values
        }
    available_years = sorted(bench_cache.keys())
    print("\n[2/3] 计算目标论文向量...")
    task_instruct = "Given a research paper abstract, identify its computer science research field."
    target_vecs = embedder.encode(df_targets['abstract'].tolist(), batch_size=4, task_instruction=task_instruct)
    print("\n[3/3] 执行匹配算法 (Average Similarity Strategy)...")
    final_records = []
    
    for i, row in tqdm(df_targets.iterrows(), total=len(df_targets), desc="Matching"):
        try:
            year = int(row['year'])
        except:
            year = 2024 
        if year not in bench_cache:
            year = min(available_years, key=lambda x: abs(x - year))
        bench_data = bench_cache[year]
        b_vecs = bench_data['vectors']
        b_domains = bench_data['domains']
        t_vec = target_vecs[i].reshape(1, -1)
        sims = cosine_similarity(t_vec, b_vecs)[0]

        temp_df = pd.DataFrame({'domain': b_domains, 'score': sims})
        domain_scores = temp_df.groupby('domain')['score'].mean()
        if not domain_scores.empty:
            best_domain = domain_scores.idxmax()
            best_score = domain_scores.max()
        else:
            best_domain = "Unknown"
            best_score = 0.0
            
        final_records.append({
            'year': row['year'],
            'title': row['title'],
            'college': row['college'],
            'author': row.get('author', ''),
            'supervisor': row.get('supervisor', ''),
            'matched_domain': best_domain,
            'similarity': round(best_score, 4), 
            'abstract': row['abstract']
        })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    df_result = pd.DataFrame(final_records)
    df_result.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"\n结果已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    if torch.cuda.is_available():
        print(f"使用显卡: {torch.cuda.get_device_name(0)}")
        print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("使用 CPU 运行")
        
    main()
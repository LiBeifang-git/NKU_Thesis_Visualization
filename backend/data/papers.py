import requests
import pandas as pd
import time
import datetime

DOMAINS = {
    "Computer Vision (cs.CV)": "Computer Vision",
    "NLP (cs.CL)": "Natural Language Processing",
    "Machine Learning (cs.LG)": "Machine Learning",
    "AI (cs.AI)": "Artificial Intelligence",
    "Robotics (cs.RO)": "Robotics",
    "Operating Systems (cs.OS)": "Operating Systems",
    "Databases (cs.DB)": "Databases",
    "Security (cs.CR)": "Computer Security",
    "Networking (cs.NI)": "Computer Networks",
    "Software Engineering (cs.SE)": "Software Engineering"
}

START_YEAR = 2019
END_YEAR = 2024
TOP_N = 20
SLEEP_TIME = 3 

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

def fetch_top_papers_by_year(domain_name, query_keyword, target_year):

    print(f"[*] 正在抓取: {domain_name} | 年份: {target_year} ...")
    
    params = {
        "query": query_keyword,
        "year": str(target_year),   
        "limit": TOP_N,
        "sort": "citationCount:desc",
        "fields": "title,abstract,citationCount,year,externalIds,authors,url"
    }
    
    try:
        response = requests.get(API_URL, params=params, timeout=15)

        if response.status_code == 429:
            print(f"触发频率限制")
            time.sleep(10)
            response = requests.get(API_URL, params=params, timeout=15)
            
        response.raise_for_status()
        data = response.json()
        
        if "data" not in data:
            print(f"[-] {domain_name} ({target_year}) 无数据")
            return []
            
        papers = []
        for i, item in enumerate(data["data"]):
            arxiv_id = item.get("externalIds", {}).get("ArXiv", "N/A")
            author_list = item.get("authors", [])
            if author_list:
                authors = ", ".join([a["name"] for a in author_list[:3]])
                if len(author_list) > 3:
                    authors += " et al."
            else:
                authors = "Unknown"
            
            papers.append({
                "Domain": domain_name,
                "Query_Year": target_year, 
                "Rank_in_Year": i + 1,    
                "Title": item.get("title"),
                "Citations": item.get("citationCount"),
                "ArXiv_ID": arxiv_id,
                "URL": item.get("url"),
                "Authors": authors,
                "Abstract": item.get("abstract")
            })
            
        return papers

    except Exception as e:
        print(f"[!] 抓取失败 ({domain_name} - {target_year}): {e}")
        return []

def main():
    all_results = []
    total_requests = len(DOMAINS) * (END_YEAR - START_YEAR + 1)
    current_count = 0
    
    print(f"开始抓取 {START_YEAR}-{END_YEAR}论文")
    print(f"预计请求次数: {total_requests} 次 ")

    for domain_key, query_keyword in DOMAINS.items():
        for year in range(START_YEAR, END_YEAR + 1):
            results = fetch_top_papers_by_year(domain_key, query_keyword, year)
            all_results.extend(results)
            
            current_count += 1
            print(f"进度: {current_count}/{total_requests} 完成")
            time.sleep(SLEEP_TIME)
        
        print("------------------------------------------------------")

    if all_results:
        df = pd.DataFrame(all_results)

        df['Abstract'] = df['Abstract'].fillna("No Abstract").astype(str)
        df['Abstract'] = df['Abstract'].str.replace('\n', ' ').str.replace('\r', '')

        df = df.sort_values(by=['Domain', 'Query_Year', 'Citations'], ascending=[True, True, False])
        
        filename = f"cs_yearly_top20_{START_YEAR}_{END_YEAR}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"共获取 {len(df)} 篇论文。")
        print(f"文件已保存为: {filename}")
        print("数据预览:")
        print(df[['Domain', 'Query_Year', 'Citations', 'Title']].head().to_string(index=False))
    else:
        print("\n[Fail] 未抓取到任何数据。")

if __name__ == "__main__":
    main()
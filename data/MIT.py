import requests
from bs4 import BeautifulSoup
import time
import csv
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OAI_URL = "https://dspace.mit.edu/oai/request"
MIT_THESIS_SET = "hdl_1721.1_7582"

TARGET_PER_YEAR = 50

def get_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

def fetch_year_data(session, year):
    params = {
        'verb': 'ListRecords',
        'metadataPrefix': 'oai_dc',
        'set': MIT_THESIS_SET,
        'from': f'{year}-01-01',
        'until': f'{year}-12-31'
    }

    year_results = []
    token = None
    count = 0
    
    print(f"正在处理 {year} 年")

    while count < TARGET_PER_YEAR:
        if token:
            payload = {'verb': 'ListRecords', 'resumptionToken': token}
        else:
            payload = params

        try:
            resp = session.get(OAI_URL, params=payload, verify=False, timeout=30)
            soup = BeautifulSoup(resp.content, "xml")

            error = soup.find('error')
            if error:
                if error.get('code') == 'noRecordsMatch':
                    print(f"    - {year} 年没有数据。")
                else:
                    print(f"    - API Error: {error.text}")
                break 

            records = soup.find_all('record')
            if not records and not soup.find('resumptionToken'):
                break

            for record in records:
                if count >= TARGET_PER_YEAR:
                    break

                if record.find('header', status='deleted'):
                    continue
                
                metadata = record.find('metadata')
                if not metadata:
                    continue

                xml_text = metadata.get_text().lower()

                keywords = [
                    "computer science", "electrical engineering and computer science", 
                    "artificial intelligence", "machine learning", "computational", 
                    "robotics", "algorithm", "deep learning", "neural networks"
                ]
                
                if any(kw in xml_text for kw in keywords):
                    title = metadata.find('title').text.strip() if metadata.find('title') else "Untitled"
                    
                    descriptions = [d.text.strip() for d in metadata.find_all('description')]
                    abstract = max(descriptions, key=len) if descriptions else "No Abstract"
                    
                    link_tag = metadata.find('identifier') 
                    link = link_tag.text.strip() if link_tag else ""

                    year_results.append({
                        "Year": year, 
                        "Title": title,
                        "Link": link,
                        "Abstract": abstract
                    })
                    count += 1


            if count >= TARGET_PER_YEAR:
                print(f"    √ {year} 年任务完成，已获取 {count} 篇。")
                break

            token_tag = soup.find('resumptionToken')
            if token_tag and token_tag.text:
                token = token_tag.text
                time.sleep(0.5)
            else:
                print(f"    ! {year} 年所有数据已遍历完，共找到 {count} 篇 ")
                break

        except Exception as e:
            print(f"    x {year} 年发生异常: {e}")
            break
            
    return year_results

def main():
    session = get_session()
    all_data = []

    target_years = range(2024, 2018, -1)
    
    for year in target_years:
        year_data = fetch_year_data(session, year)
        all_data.extend(year_data)
        time.sleep(1) 

    print(f"\n{'='*30}")
    print(f"总共获取: {len(all_data)} 篇论文。")

    filename = 'mit_cs_theses_balanced.csv'
    if all_data:
        try:
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                headers = ["Year", "Title", "Link", "Abstract"]
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(all_data)
            print(f"文件已保存为: {filename}")
        except Exception as e:
            print(f"保存失败: {e}")
    else:
        print("未抓取到任何数据。")

if __name__ == "__main__":
    main()
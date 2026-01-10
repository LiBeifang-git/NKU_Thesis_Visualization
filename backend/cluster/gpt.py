import csv
from openai import OpenAI

# ================== 配置 ==================
API_KEY = "sk-zk2f2cbe611ff420bc71ad165792f32229966e8e7463758c"
BASE_URL = "https://api.zhizengzeng.com/v1" 

# ================== 改写 Prompt ==================
def make_prompt(text: str, len_cluster: int) -> str:
    return f"""
我已经完成了文献的聚类分析。
下面给出的是【每一个簇中出现频率最高的关键词列表】。

你的任务是：
1. 根据每个簇的关键词，总结该簇对应的【文献研究主题 / 研究方向】；
2. 各簇名称应具有明确的学术含义，能够概括研究内容；
3. 不同簇之间的命名应具有明显区分度，避免语义重叠；
4. 每个簇只给出一个简洁、概括性的名称（不超过10个字）。

输入（字典，key 为簇编号）：
{text}

总簇数：{len_cluster}

【输出要求（必须严格遵守）】：
- 仅输出 JSON 字典
- key 为簇编号字符串（从 0 开始）
- value 为对应簇的研究方向名称
- 不要输出解释、说明、代码块标记

输出示例：
{{
  "0": "舆情分析研究",
  "1": "虚假信息检测"
}}
""".strip()



# ================== 调用 Gemini ==================
import json
def extract_cluster_kw(text: str, len_cluster: int) -> dict:
    prompt = make_prompt(text, len_cluster)

    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}  # ✅ 强制 JSON
    )

    result = json.loads(response.choices[0].message.content)
    print(result)
    # 校验
    assert isinstance(result, dict)
    assert len(result) == len_cluster

    return result


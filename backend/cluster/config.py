# CONFIG FOR API KEYS
import os

import openai

openai.api_base = 'https://flag.smarttrot.com/'#"https://api.chatanywhere.cn"
# print('CONFIG')
# openai.api_base =  'https://api.chatanywhere.com.cn'
# semantic scholar API || Free || non-mandatory || If not provided, you may get blocked by S2 for a little while. Try solve this by setting a longer waiting time period. ||You can request a Semantic Scholar API Key via https://www.semanticscholar.org/product/api#api-key-form
s2api = '1BTuoOQ97v3iH32TE1e1i9xmQuKBjHWF5TJdhVT5'



# OPENAI API || NOT Free || non-mandatory ||  You can avoid providing this by specifying the args.field parameter. || If you have trouble accessing OpenAI, try this-> https://github.com/chatanywhere/GPT_API_free
openai_key = 'sk-zk2ea3df5fd097682a92420d3062d3a9b6b65aa2841d938e'#"sk-DDSPwwwYTJYEhIj7J7NmY3ogpLu5Ta8h76wjnF10YK4nMnzi"



# easy scholar API || Free || non-mandatory || If not provided, then no conference lever, journal IF will be presented on PDF || A key used for searching IF or CCF level for journal or conference, you can request one via https://www.easyscholar.cc/console/user/open
eskey = '2bc92dbdeeae45d99ed6e483fabf6334'

API_SECRET_KEY = "sk-zk2f2cbe611ff420bc71ad165792f32229966e8e7463758c"
BASE_URL = "https://flag.smarttrot.com/v1/"
os.environ["OPENAI_API_KEY"] = API_SECRET_KEY
os.environ["OPENAI_API_BASE"] = BASE_URL
os.environ["SERPER_API_KEY"] = "4d2c4507e5814ca9a556c5879516076991863f99"
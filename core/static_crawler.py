import requests
from bs4 import BeautifulSoup

def analyze_site(url):
    # 実務レベルの解析ロジック
    res = {"llms_txt": False, "semantic_html": False}
    try:
        # ドメイン直下のllms.txtを確認
        domain = "/".join(url.split("/")[:3])
        if requests.get(f"{domain}/llms.txt", timeout=5).status_code == 200:
            res["llms_txt"] = True
        
        # HTML構造の解析
        page = requests.get(url, timeout=10)
        soup = BeautifulSoup(page.text, 'html.parser')
        if soup.find('article') or soup.find('section'):
            res["semantic_html"] = True
            
        return res
    except:
        return res

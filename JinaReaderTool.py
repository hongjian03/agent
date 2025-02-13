from crewai.tools import BaseTool
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Union

class JinaReaderTool(BaseTool):
    name: str = "Read website content"
    description: str = "获取网页内容为纯文本。"

    def _run(self, url: str = None, website_url: str = None) -> Dict[str, Union[str, List[str]]]:
        # 使用 url 或 website_url
        target_url = url or website_url
        
        api_url = f'https://r.jina.ai/{target_url}'
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文本内容
            text_content = soup.get_text()

            return {
                "text": text_content
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"请求失败: {e}"}
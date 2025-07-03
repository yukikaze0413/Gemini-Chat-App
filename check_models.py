# check_models.py
import os
import google.generativeai as genai
from google.generativeai.client import configure
from google.generativeai.models import list_models

def read_api_key_from_txt(path="api.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None

def list_available_models():
    """
    连接到 Google API，并列出所有与'generateContent'方法兼容（即可以用于聊天）的模型。
    """
    try:
        # 1. 从 api.txt 文件加载 API 密钥
        api_key = read_api_key_from_txt()
        if not api_key:
            print("❌ 错误: 在 api.txt 文件中未找到 API Key。")
            print("请确保你的 api.txt 文件与脚本在同一个目录下，并且内容格式正确。")
            return
        print("🔑 API 密钥已成功加载。")
        
        # 2. 配置 API 客户端
        configure(api_key=api_key)
        print("✅ API 已配置成功。")

        # 3. 获取并筛选模型列表
        print("\n🔎 正在为你的API密钥获取可用模型列表...")
        print("--------------------------------------------------")
        
        found_models = False
        # genai.list_models() 会返回所有有权访问的模型
        for model in list_models():
            # 我们只关心那些支持 'generateContent'（即聊天功能）的模型
            if 'generateContent' in model.supported_generation_methods:
                found_models = True
                print(f"✔️ 模型名称: {model.name}")
        
        print("--------------------------------------------------")

        if not found_models:
            print("❌ 未找到适用于此 API 密钥的聊天模型。")
        else:
            print("\n📌 请执行操作: 从上方复制一个完整的'模型名称' (例如: models/gemini-1.5-flash-latest)")
            print("   然后把它更新到你的 main_app.py 文件的模型列表和默认值中。")

    except Exception as e:
        # 如果在这里发生异常，几乎可以肯定是API密钥本身的问题
        print(f"\n❌ 尝试连接 API 时发生严重错误。")
        print("这几乎可以100%确定你的 API 密钥是无效的或输入不正确。")
        print("-------------------- 错误详情 --------------------")
        print(e)
        print("-------------------------------------------------------")
        print("\n📌 请执行操作: 前往 Google AI Studio, 创建一个全新的 API 密钥, 然后更新你的 .env 文件。")

if __name__ == "__main__":
    list_available_models()
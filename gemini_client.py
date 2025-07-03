# gemini_client.py
import os
import google.generativeai as genai
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.types import GenerationConfig

def read_api_key_from_txt(path="api.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None

class GeminiClient:
    def __init__(self, api_key=None, model_name="gemini-2.5-flash", system_instruction=None):
        """
        初始化 Gemini 客户端。
        """
        if api_key is None:
            api_key = read_api_key_from_txt()
        if not api_key:
            raise ValueError("API Key not found. Please make sure api.txt exists and contains your API key.")
        configure(api_key=api_key)
        self.model_name = model_name
        self.system_instruction = system_instruction
        self._init_model()

    def _init_model(self):
        if self.system_instruction and str(self.system_instruction).strip():
            self.model = GenerativeModel(
                self.model_name,
                system_instruction=self.system_instruction
            )
        else:
            self.model = GenerativeModel(self.model_name)

    def set_model(self, model_name, system_instruction=None):
        """切换模型和/或系统指令"""
        changed = False
        if self.model_name != model_name:
            self.model_name = model_name
            changed = True
        if system_instruction is not None and self.system_instruction != system_instruction:
            self.system_instruction = system_instruction
            changed = True
        if changed:
            self._init_model()
            print(f"Model switched to: {self.model_name}, system_instruction updated.")

    def generate_response(self, history: list, new_prompt: str, temperature=0.7, top_p=0.9) -> str:
        """
        根据对话历史和新的提示生成回复。
        """
        try:
            # 为API格式化历史记录
            formatted_history = []
            for sender, message in history:
                if sender.lower() == 'you':
                    role = 'user'
                elif sender.lower() == 'gemini':
                    role = 'model'
                else:
                    continue
                formatted_history.append({'role': role, 'parts': [message]})
            chat_session = self.model.start_chat(history=formatted_history)
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p
            )
            response = chat_session.send_message(
                content=new_prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            error_message = f"An error occurred: {e}"
            print(error_message)
            return error_message

    @staticmethod
    def get_available_models():
        """
        获取所有支持 generateContent 的模型短名列表。
        """
        api_key = read_api_key_from_txt()
        if not api_key:
            print("❌ 错误: 在 api.txt 文件中未找到 API Key。")
            return []
        try:
            genai.configure(api_key=api_key)
            models = []
            for model in genai.list_models():
                if 'generateContent' in getattr(model, 'supported_generation_methods', []):
                    name = model.name
                    if name.startswith("models/"):
                        name = name.split("/", 1)[1]
                    models.append(name)
            return models
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
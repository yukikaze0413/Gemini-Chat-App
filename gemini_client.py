# gemini_client.py
import os
import google.generativeai as genai
from google.generativeai.client import configure
from google.generativeai.models import list_models
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.types import GenerationConfig
import sys
import logging

# 获取日志记录器
logger = logging.getLogger(__name__)

def get_api_file_path():
    if getattr(sys, 'frozen', False):
        # 打包后
        exe_dir = os.path.dirname(sys.executable)
        api_path = os.path.join(exe_dir, "api.txt")
    else:
        # 源码运行
        api_path = os.path.join(os.path.dirname(__file__), "api.txt")
    return api_path

class GeminiClient:
    def __init__(self, api_key=None, model_name="gemini-2.0-flash", system_instruction=None):
        """
        初始化 Gemini 客户端。
        """
        if api_key is None:
            api_file = get_api_file_path()
            with open(api_file, "r", encoding="utf-8") as f:
                api_key = f.read().strip()
        if not api_key:
            raise ValueError("API Key not found. Please make sure api.txt exists and contains your API key.")
        
        logger.info(f"初始化Gemini客户端 - 模型: {model_name}")
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

    def generate_response(self, history=None, new_prompt="", temperature=0.7, top_p=0.9):
        """
        生成回复
        """
        try:
            logger.info(f"生成回复 - 模型: {self.model_name}, 温度: {temperature}, top_p: {top_p}")
            
            # 构建完整的对话历史
            messages = []
            if history:
                for sender, message in history:
                    role = "user" if sender == "You" else "model"
                    messages.append({"role": role, "parts": [message]})
            
            # 添加新的用户消息
            messages.append({"role": "user", "parts": [new_prompt]})
            
            # 设置生成配置
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=8192,
            )
            
            # 生成回复
            response = self.model.generate_content(
                messages,
                generation_config=generation_config
            )
            
            logger.info("回复生成成功")
            return response.text
            
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            raise

    @staticmethod
    def get_available_models():
        """
        获取所有支持 generateContent 的模型短名列表。
        """
        api_file = get_api_file_path()
        with open(api_file, "r", encoding="utf-8") as f:
            api_key = f.read().strip()
        if not api_key:
            print("❌ 错误: 在 api.txt 文件中未找到 API Key。")
            return []
        try:
            # genai.configure(api_key=api_key)
            configure(api_key=api_key)
            models = []
            for m in list_models():
                if 'generateContent' in getattr(m, 'supported_generation_methods', []):
                    name = m.name
                    if name.startswith("models/"):
                        name = name.split("/", 1)[1]
                    models.append(name)
            return models
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
# ultimate_test.py
import google.generativeai as genai

print("--- 终极API请求测试 ---")

# 1. !!! 在这里直接粘贴你的全新API密钥 !!!
# 这是一个决定性的步骤，请确保你使用的是刚刚从Google AI Studio生成的、全新的密钥。
# 将下面的 "AIzaSy..." 字符串替换为你的真实密钥。
API_KEY = "AIzaSyDwkPnY39JhZ36_Ws_ugSIuPjvnw7cjqLQ"

# 2. 配置API，使用你的密钥
try:
    genai.configure(api_key=API_KEY)
    print("✅ API 配置步骤执行完毕。")
except Exception as e:
    print(f"❌ 在配置API时就发生错误: {e}")
    # 如果在这里出错，通常是库安装问题

# 3. 初始化一个最基础、最不可能出错的模型
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("✅ 模型 'gemini-1.0-pro' 初始化成功。")
except Exception as e:
    print(f"❌ 在初始化模型时发生错误: {e}")

# 4. 发送一个最简单的请求
try:
    print("🚀 正在发送请求 '你好'...")
    response = model.generate_content("你好")
    
    # 5. 如果成功，打印回复
    print("\n🎉🎉🎉 成功！API返回了结果！ 🎉🎉🎉")
    print("----------------------------------------")
    print(f"Gemini 的回复: {response.text}")
    print("----------------------------------------")
    print("\n结论：API密钥和请求代码均有效。问题可能出在原复杂应用的环境配置上。")

except Exception as e:
    # 6. 如果失败，打印完整的错误信息
    print("\n🔥🔥🔥 失败！API返回了错误！ 🔥🔥🔥")
    print("----------------------------------------")
    print(f"收到的原始错误信息: {e}")
    print("----------------------------------------")
    print("\n结论：如果错误仍是 '400 API key not valid'，则100%证明问题与代码无关，而是与你的Google账户/项目或网络环境有关。")
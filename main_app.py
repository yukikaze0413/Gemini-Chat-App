# main_app.py
import customtkinter as ctk
from gemini_client import GeminiClient
import json
import uuid
import os
import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog
from tkinter import messagebox, filedialog
import re
import threading
import logging
import sys
from datetime import datetime, timedelta

# 配置日志
def setup_logging():
    # 创建logs目录
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 清理超过48小时的日志文件
    cleanup_old_logs()
    
    # 生成日志文件名（包含时间戳）
    log_filename = f"logs/gemini_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)  # 同时输出到控制台
        ]
    )
    return logging.getLogger(__name__)

def cleanup_old_logs():
    """清理超过48小时的日志文件"""
    try:
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            return
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=48)
        
        deleted_count = 0
        for filename in os.listdir(logs_dir):
            if filename.startswith("gemini_chat_") and filename.endswith(".log"):
                file_path = os.path.join(logs_dir, filename)
                try:
                    # 从文件名解析时间戳
                    # 文件名格式: gemini_chat_YYYYMMDD_HHMMSS.log
                    time_str = filename.replace("gemini_chat_", "").replace(".log", "")
                    file_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                except (ValueError, OSError) as e:
                    # 如果文件名格式不对或删除失败，跳过
                    continue
        
        if deleted_count > 0:
            print(f"已清理 {deleted_count} 个超过48小时的日志文件")
    except Exception as e:
        print(f"清理日志文件时出错: {e}")

# 初始化日志
logger = setup_logging()
logger.info("程序启动")

class ChatApp(ctk.CTk):
    HISTORY_FILE = "chat_history.json"

    def __init__(self, gemini_client):
        super().__init__()
        self.chats = {}
        self.current_chat_id = None
        self.gemini_client = gemini_client

        self.title("Gemini Chat App")
        self.geometry("900x600")
        self.minsize(900, 600)

        # 设置主窗口背景色
        self.configure(fg_color="#EAFDFF")

        # --- 主体布局权重 ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # --- 一体化大框：提示词+聊天区+输入区 ---
        main_chat_frame = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=14)
        main_chat_frame.grid(row=0, column=1, rowspan=3, padx=20, pady=15, sticky="nsew")
        main_chat_frame.grid_rowconfigure(1, weight=1)
        main_chat_frame.grid_columnconfigure(0, weight=0)

        # 提示词输入框（在大框内）
        self.prompt_var = ctk.StringVar()
        self.prompt_label = ctk.CTkLabel(
            main_chat_frame,
            text="系统提示词 (Prompt)：",
            font=("Microsoft YaHei", 13)
        )
        self.prompt_label.grid(row=0, column=0, sticky="w", padx=(16, 2), pady=(14, 2))

        self.prompt_entry = ctk.CTkEntry(
            main_chat_frame,
            font=("Microsoft YaHei", 14),
            textvariable=self.prompt_var
        )
        self.prompt_entry.grid(row=0, column=1, sticky="ew", padx=(0, 2), pady=(14, 2))
        main_chat_frame.grid_columnconfigure(0, weight=0)  # Label 列不拉伸
        main_chat_frame.grid_columnconfigure(1, weight=1)  # 输入框列自动拉伸
        main_chat_frame.grid_columnconfigure(2, weight=0)  # 按钮列不拉伸
        self.apply_prompt_btn = ctk.CTkButton(main_chat_frame, text="应用", font=("Microsoft YaHei", 12), width=60, command=self.apply_prompt, fg_color="#3498db", text_color="#ffffff")
        self.apply_prompt_btn.grid(row=0, column=2, sticky="e", padx=(0, 16), pady=(14, 2))

        # 聊天显示区（在大框内）
        self.chat_display = ctk.CTkTextbox(main_chat_frame, state="disabled", wrap="word", font=("Microsoft YaHei", 14), fg_color="#ffffff", border_width=2, border_color="#636e72", corner_radius=8)
        self.chat_display.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=16, pady=(0, 8))
        main_chat_frame.grid_rowconfigure(1, weight=1)

        # 用户输入区（在大框内最下方）
        input_row = ctk.CTkFrame(main_chat_frame, fg_color="#ffffff")
        input_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 12))
        input_row.grid_columnconfigure(0, weight=1)
        self.user_input = ctk.CTkEntry(
            input_row,
            placeholder_text="在此输入你的消息...",
            font=("Microsoft YaHei", 14)
        )
        self.user_input.grid(row=0, column=0, padx=(0, 10), pady=8, sticky="ew")
        self.user_input.bind("<Return>", self.send_message_event)
        self.send_button = ctk.CTkButton(input_row, text="发送", width=80, command=self.send_message, font=("Microsoft YaHei", 12), fg_color="#3498db", text_color="#ffffff")
        self.send_button.grid(row=0, column=1, padx=(0, 6), pady=8)

        # --- 侧边栏 ---
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color="#ffffff")
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nswe", padx=(10, 0), pady=15)
        self.sidebar.grid_propagate(False)

        # 只开放三种模型
        model_list = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
        default_model = model_list[0]
        ctk.CTkLabel(self.sidebar, text="选择模型", font=("Microsoft YaHei", 14, "bold")).pack(pady=(10, 2), padx=10, anchor="w")
        self.model_var = ctk.StringVar(value=default_model)
        self.model_option = ctk.CTkOptionMenu(self.sidebar, variable=self.model_var, values=model_list, font=("Microsoft YaHei", 12), fg_color="#3498db", text_color="#ffffff", command=self.on_model_change)
        self.model_option.pack(pady=(0, 15), fill="x", padx=10)

        # temperature参数
        ctk.CTkLabel(self.sidebar, text="temperature", font=("Microsoft YaHei", 12)).pack(pady=(0, 2), padx=10, anchor="w")
        temp_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        temp_frame.pack(pady=(0, 10), fill="x", padx=10)
        self.temp_var = ctk.DoubleVar(value=0.7)
        self.temp_slider = ctk.CTkSlider(temp_frame, from_=0, to=1, variable=self.temp_var, number_of_steps=100)
        self.temp_slider.pack(side="left", fill="x", expand=True)
        self.temp_value_label = ctk.CTkLabel(temp_frame, text=f"{self.temp_var.get():.2f}", width=40, font=("Microsoft YaHei", 12))
        self.temp_value_label.pack(side="right")
        self.temp_var.trace_add("write", lambda *args: self.temp_value_label.configure(text=f"{self.temp_var.get():.2f}"))

        # top_p参数
        ctk.CTkLabel(self.sidebar, text="top_p", font=("Microsoft YaHei", 12)).pack(pady=(0, 2), padx=10, anchor="w")
        top_p_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_p_frame.pack(pady=(0, 15), fill="x", padx=10)
        self.top_p_var = ctk.DoubleVar(value=0.9)
        self.top_p_slider = ctk.CTkSlider(top_p_frame, from_=0, to=1, variable=self.top_p_var, number_of_steps=100)
        self.top_p_slider.pack(side="left", fill="x", expand=True)
        self.top_p_value_label = ctk.CTkLabel(top_p_frame, text=f"{self.top_p_var.get():.2f}", width=40, font=("Microsoft YaHei", 12))
        self.top_p_value_label.pack(side="right")
        self.top_p_var.trace_add("write", lambda *args: self.top_p_value_label.configure(text=f"{self.top_p_var.get():.2f}"))

        # 新建对话按钮
        self.new_chat_btn = ctk.CTkButton(self.sidebar, text="新建对话", command=self.new_chat, font=("Microsoft YaHei", 12), fg_color="#3498db", text_color="#ffffff")
        self.new_chat_btn.pack(pady=(0, 15), fill="x", padx=10)

        # 保存当前对话按钮
        self.save_chat_btn = ctk.CTkButton(self.sidebar, text="保存当前对话", command=self.save_current_chat_to_file, font=("Microsoft YaHei", 12), fg_color="#27ae60", text_color="#ffffff")
        self.save_chat_btn.pack(pady=(0, 8), fill="x", padx=10)

        # 导入历史对话按钮
        self.import_chat_btn = ctk.CTkButton(self.sidebar, text="导入历史对话", command=self.import_chat_from_file, font=("Microsoft YaHei", 12), fg_color="#e67e22", text_color="#ffffff")
        self.import_chat_btn.pack(pady=(0, 15), fill="x", padx=10)

        # 对话历史列表
        ctk.CTkLabel(self.sidebar, text="对话历史", font=("Microsoft YaHei", 13, "bold")).pack(pady=(0, 2), padx=10, anchor="w")
        self.chat_list_frame = ctk.CTkScrollableFrame(self.sidebar, label_text="", fg_color="#ffffff", scrollbar_button_color="#ffffff", scrollbar_button_hover_color="#aaaaaa")
        self.chat_list_frame.pack(pady=(0, 10), fill="both", expand=True, padx=10)
        self.chat_buttons = {}
        self.rename_buttons = {}

        # --- 初始化 ---
        self.load_history()
        self.refresh_chat_list()
        if not self.chats:
            # 启动时自动新建一个"新聊天"对话，不弹窗
            chat_id = str(uuid.uuid4())
            self.chats[chat_id] = {"title": "新聊天", "messages": [], "prompt": ""}
            self.current_chat_id = chat_id
            self.switch_chat(chat_id)
            self.refresh_chat_list()
            self.add_message_to_display("System", "你好！我是Gemini，有什么可以帮你的吗？")
            # 确保prompt被传递
            model_name = self.model_var.get()
            prompt = self.chats[chat_id].get("prompt", "")
            self.gemini_client.set_model(model_name, system_instruction=prompt)
        else:
            last_chat_id = list(self.chats.keys())[-1]
            self.switch_chat(last_chat_id)

    def show_title_dialog(self, title_hint="请输入对话名称：", default_value=""):
        dialog = tk.Toplevel(self)
        dialog.title(title_hint)
        dialog.geometry("320x120")
        dialog.resizable(False, False)
        dialog.grab_set()
        label = tk.Label(dialog, text=title_hint, font=("Microsoft YaHei", 12))
        label.pack(pady=(18, 5))
        entry = tk.Entry(dialog, font=("Microsoft YaHei", 13))
        entry.insert(0, default_value)
        entry.pack(pady=5, padx=20, fill="x")
        entry.focus()
        result = None
        def on_ok(event=None):
            nonlocal result
            val = entry.get().strip()
            if val:
                result = val
                dialog.destroy()
        entry.bind("<Return>", on_ok)
        ok_btn = tk.Button(dialog, text="确定", font=("Microsoft YaHei", 12), command=on_ok, width=8)
        ok_btn.pack(pady=8)
        dialog.wait_window()
        return result

    def new_chat(self):
        # 美化弹窗输入对话名称
        title = self.show_title_dialog("请输入对话名称：")
        if not title:
            return
        chat_id = str(uuid.uuid4())
        self.chats[chat_id] = {"title": title, "messages": [], "prompt": ""}
        self.current_chat_id = chat_id
        self.switch_chat(chat_id)
        self.refresh_chat_list()
        self.add_message_to_display("System", "你好！我是Gemini，有什么可以帮你的吗？")

    def rename_chat(self, chat_id):
        old_title = self.chats[chat_id]["title"]
        new_title = self.show_title_dialog("重命名对话：", old_title)
        if new_title and new_title != old_title:
            self.chats[chat_id]["title"] = new_title
            self.refresh_chat_list()
            self.save_history()

    def send_message(self):
        user_text = self.user_input.get().strip()
        if not user_text:
            return

        logger.info(f"发送消息: {user_text[:50]}...")  # 记录发送的消息（前50字符）

        # 如果当前没有对话，自动新建一个对话
        if not self.current_chat_id:
            chat_id = str(uuid.uuid4())
            self.chats[chat_id] = {"title": "新聊天", "messages": [], "prompt": ""}
            self.current_chat_id = chat_id
            self.switch_chat(chat_id)
            self.refresh_chat_list()
            self.add_message_to_display("System", "你好！我是Gemini，有什么可以帮你的吗？")

        self.add_message_to_display("You", user_text)
        self.user_input.delete(0, "end")
        self.send_button.configure(state="disabled", text="...")
        self.update_idletasks()

        def get_response():
            if self.current_chat_id is None or self.current_chat_id not in self.chats:
                return
            model_name = self.model_var.get()
            temperature = self.temp_var.get()
            top_p = self.top_p_var.get()
            current_chat = self.chats[self.current_chat_id]
            history_for_api = current_chat["messages"][:-1]
            self.gemini_client.set_model(model_name, system_instruction=current_chat.get("prompt", ""))
            try:
                logger.info(f"请求模型回复 - 模型: {model_name}, 温度: {temperature}")
                response_text = self.gemini_client.generate_response(
                    history=history_for_api,
                    new_prompt=user_text,
                    temperature=temperature,
                    top_p=top_p
                )
                logger.info("模型回复成功")
            except Exception as e:
                logger.error(f"模型回复失败: {e}")
                response_text = f"【出错】{e}"
            # 回到主线程更新界面
            self.after(0, lambda: self.finish_response(response_text, user_text))

        threading.Thread(target=get_response, daemon=True).start()

    def finish_response(self, response_text, user_text):
        if self.current_chat_id is None or self.current_chat_id not in self.chats:
            return
        self.send_button.configure(state="normal", text="发送")
        self.add_message_to_display("Gemini", response_text)
        current_chat = self.chats[self.current_chat_id]
        # 保留：如果用户未手动修改标题，发送第一条消息后自动用内容命名
        if len(current_chat["messages"]) == 2 and current_chat["title"] == "新对话":
            current_chat["title"] = user_text[:30]
            self.refresh_chat_list()
        self.save_history()

    def send_message_event(self, event):
        self.send_message()

    def add_message_to_display(self, sender, message):
        if not self.current_chat_id: return
        
        self.chats[self.current_chat_id]["messages"].append((sender, message))
        
        if self.current_chat_id == self.get_displayed_chat_id():
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"{sender}:\n{message}\n\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see("end")

    def refresh_chat_list(self):
        for widget in self.chat_list_frame.winfo_children():
            widget.destroy()
        self.chat_buttons.clear()
        self.rename_buttons.clear()
        for cid in reversed(list(self.chats.keys())):
            chat = self.chats[cid]
            title = chat["title"]
            frame = ctk.CTkFrame(self.chat_list_frame, fg_color="#ffffff")
            frame.pack(fill="x", pady=2)
            btn = ctk.CTkButton(
                frame,
                text=title,
                fg_color="#ffffff",
                text_color="#222222",
                command=lambda c=cid: self.switch_chat(c),
                font=("Microsoft YaHei", 12),
                width=140,
                anchor="w"
            )
            def on_enter(e, b=btn, c=cid):
                b.configure(fg_color="#3498db", text_color="#ffffff")
            def on_leave(e, b=btn, c=cid):
                b.configure(fg_color="#ffffff", text_color="#222222")
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            btn.pack(side="left", fill="x", expand=True)
            self.chat_buttons[cid] = btn
            rename_btn = ctk.CTkButton(
                frame,
                text="🖉",  # 编辑图标
                width=32,
                fg_color="#ffffff",
                text_color=("#666", "#aaa"),
                hover_color=("#e0e0e0", "#444444"),
                command=lambda c=cid: self.rename_chat(c),
                font=("Microsoft YaHei", 13)
            )
            rename_btn.pack(side="right", padx=(2, 0))
            self.rename_buttons[cid] = rename_btn

    def switch_chat(self, chat_id):
        if chat_id not in self.chats:
            return
        self.current_chat_id = chat_id
        # 切换时显示当前对话的prompt
        self.prompt_var.set(self.chats[chat_id].get("prompt", ""))
        # 切换对话时也重建模型对象
        model_name = self.model_var.get()
        prompt = self.chats[chat_id].get("prompt", "")
        self.gemini_client.set_model(model_name, system_instruction=prompt)
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        for sender, msg in self.chats[chat_id]["messages"]:
            self.chat_display.insert("end", f"{sender}:\n{msg}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        self.refresh_chat_list()
    
    def get_displayed_chat_id(self):
        return self.current_chat_id

    def get_safe_filename(self, title, ext=".json"):
        # 允许中文，去除不合法字符，重名自动加后缀
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        base = os.path.join("history", safe_title)
        filename = base + ext
        i = 1
        while os.path.exists(filename):
            filename = f"{base}_{i}{ext}"
            i += 1
        return filename

    def save_current_chat_to_file(self):
        if not self.current_chat_id:
            return
        chat = self.chats[self.current_chat_id]
        os.makedirs("history", exist_ok=True)
        filename = self.get_safe_filename(chat["title"])
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        logger.info(f"保存对话到文件: {filename}")
        messagebox.showinfo("保存成功", f"对话已保存到：{filename}")

    def import_chat_from_file(self):
        file_path = filedialog.askopenfilename(
            title="导入历史对话",
            filetypes=[("对话历史", "*.json")],
            initialdir="history"
        )
        if not file_path:
            return
        try:
            logger.info(f"导入对话文件: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                chat = json.load(f)
            # 数据健壮性校验和修复
            if "messages" not in chat or not isinstance(chat["messages"], list):
                chat["messages"] = []
            # 修正messages内部元素类型（如有元组转为列表）
            chat["messages"] = [list(m) if isinstance(m, tuple) else m for m in chat["messages"]]
            if "prompt" not in chat or not isinstance(chat["prompt"], str):
                chat["prompt"] = ""
            # 生成唯一ID，避免冲突
            chat_id = str(uuid.uuid4())
            # 如果title重名自动加后缀
            title = chat.get("title", "导入对话")
            exist_titles = {c["title"] for c in self.chats.values()}
            orig_title = title
            i = 1
            while title in exist_titles:
                title = f"{orig_title}_{i}"
                i += 1
            chat["title"] = title
            # 弹窗询问导入方式
            import tkinter.simpledialog
            import tkinter.messagebox
            result = tkinter.messagebox.askquestion(
                "导入方式选择",
                "请选择导入方式：\n是 - 替换所有历史\n否 - 作为新对话导入",
                icon='question'
            )
            if result == 'yes':
                # 替换所有历史
                self.chats = {chat_id: chat}
                self.current_chat_id = chat_id
                self.switch_chat(chat_id)
                self.refresh_chat_list()
                messagebox.showinfo("导入成功", f"已替换所有历史，当前对话：{title}")
            else:
                # 作为新对话导入
                self.chats[chat_id] = chat
                self.current_chat_id = chat_id
                self.switch_chat(chat_id)
                self.refresh_chat_list()
                messagebox.showinfo("导入成功", f"已导入对话：{title}")
        except Exception as e:
            messagebox.showerror("导入失败", f"导入失败：{e}")

    def save_history(self):
        # 不再自动保存，保留空实现以兼容原有调用
        pass

    def load_history(self):
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content:
                        self.chats = json.load(f)
                    else:
                        self.chats = {}
            except (json.JSONDecodeError, Exception) as e:
                print(f"加载历史失败: {e}")
                self.chats = {}

    def apply_prompt(self):
        if not self.current_chat_id:
            return
        prompt = self.prompt_var.get()
        self.chats[self.current_chat_id]["prompt"] = prompt
        model_name = self.model_var.get()
        self.gemini_client.set_model(model_name, system_instruction=prompt)
        logger.info(f"应用系统提示词: {prompt[:50]}...")  # 记录提示词（前50字符）
        self.apply_prompt_btn.configure(text="√")
        self.after(1500, lambda: self.apply_prompt_btn.configure(text="应用"))

    def on_model_change(self, *args):
        if not self.current_chat_id:
            return
        prompt = self.chats[self.current_chat_id].get("prompt", "")
        model_name = self.model_var.get()
        self.gemini_client.set_model(model_name, system_instruction=prompt)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    try:
        client = GeminiClient(model_name="gemini-2.0-flash")
        app = ChatApp(gemini_client=client)
        app.mainloop()
    except Exception as e:
        print(f"启动应用失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
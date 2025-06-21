import os
import re
import oss2
from utils import *
import gradio as gr
from prompt import *
from gpt import ask_gpt
from gradio.themes import Glass
from upload_video import up_video
from video_process import poll_tingwu_task
from search_engine import search_engine_init
from units_for_grade import get_units_for_grade

def parse_error_code(error_msg: str) -> str:
    if "KeyError: 'Data'" in error_msg:
        return "API响应格式不兼容，请检查服务版本"
    if "ValueError: OSS链接列表为空" in error_msg:
        return "未找到有效的OSS文件"
    if match := re.search(r"CODE:(\d+)", error_msg):
        return f"服务内部错误（代码{match.group(1)}）"
    return "未知服务异常，请联系管理员"

def process_media(video_path: str, file_path: str, grade: str, unit: str, progress=gr.Progress()) -> str:
    """处理流程（输出Markdown格式）"""
    global oss_url
    result = []

    try:
        progress(0.0, desc="启动多媒体处理引擎...")

        # OSS上传阶段
        oss_url = ""
        if video_path:
            try:
                progress(0.2, desc="视频上传至OSS...")
                oss_url = up_video(video_path)
                progress(0.3)
            except oss2.exceptions.OssHttpError as e:
                error_type = "权限错误" if e.status == 403 else "网络错误"
                raise gr.Error(f"🔒 OSS上传失败({error_type}): {e.message}")

        # 智能分析阶段
        video_result = ""
        if oss_url:
            try:
                progress(0.4, desc="启动智能分析模块...")
                analysis_result = poll_tingwu_task(oss_url)
                video_result = ask_gpt(video_user_prompt, video_system_prompt, analysis_result)
                result.extend(["## 📊 课堂视频分析报告", video_result])
                progress(0.8)
            except Exception as e:
                raise gr.Error(f"🤖 分析服务异常: {parse_error_code(str(e))}")

        # 文档处理阶段
        if file_path:
            try:
                progress(0.8, desc="解析文档内容...")
                if not os.path.exists(file_path):
                    raise FileNotFoundError("文件路径无效")

                file_content = read_file(file_path)
                context = f"**课堂视频分析内容**：\n{video_result}" if video_result else ""
                search_engine = search_engine_init(grade, unit)
                user_prompt = f"{file_user_prompt}\n{context}\n**教案内容**：\n{file_content}"
                file_result = search_engine.search(user_prompt)
                result.extend(["## 📂 教学分析结果", file_result.response])
                progress(0.95)
            except Exception as e:
                raise gr.Error(f"📄 文档处理失败: {str(e)}")

        progress(1.0, desc="✅ 处理完成")
        return "\n\n".join(result) if result else "## 未获取到分析结果\n请检查文件格式是否正确"

    except gr.Error as e:
        raise
    except Exception as e:
        raise gr.Error(f"⚠ 未预期错误: {str(e)}")


with gr.Blocks(title="多媒体处理中心", theme=Glass(text_size="md"), css_paths=["style.css"]) as demo:
    gr.Markdown("""<div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50; font-size: 2.2em;">🎬 多模态教学分析助手</h1>
    </div>""")

    with gr.Row():
        # 左侧上传区
        with gr.Column(scale=4, elem_classes="column-container"):
            with gr.Group(elem_classes="content-box"):
                gr.Markdown("### 📤 上传文件", elem_classes="custom-md")
                video_input = gr.Video(
                    label="视频文件",
                    sources=["upload"],
                    format="mp4",
                    interactive=True,
                    mirror_webcam=False,
                    )
                file_input = gr.File(
                    label="文档文件",
                    file_count="single",
                    file_types=[".pdf", ".docx", ".xlsx"],
                    )
                with gr.Row():
                    grade_choices = ["一年级上册", "一年级下册", "二年级上册", "二年级下册", "三年级上册", "三年级下册","四年级上册", "四年级下册", "五年级上册", "五年级下册", "六年级上册", "六年级下册"]
                    grade_selector = gr.Dropdown(
                        label="年级",
                        choices=grade_choices,
                        value="一年级上册",
                        interactive=True,
                        scale=2
                    )
                    unit_selector = gr.Dropdown(
                        label="单元",
                        choices=get_units_for_grade("一年级上册"),
                        value=get_units_for_grade("一年级上册")[0] if get_units_for_grade("一年级上册") else None,
                        interactive=True,
                        scale=3
                    )
                with gr.Row():
                    submit_btn = gr.Button("开始分析", variant="primary", scale=1)
                    clear_btn = gr.Button("清空输入", variant="secondary", scale=1)

        # 右侧分析区
        with gr.Column(scale=6, elem_classes="column-container"):
            with gr.Group(elem_classes="content-box"):
                gr.Markdown("### 📊 分析报告", elem_classes="custom-md")
                text_output = gr.Markdown(
                value="<div class='ready-prompt'>"
                      "<h1>🚀 准备就绪</h1>"
                      "<p>请上传文件并点击开始分析按钮</p>"
                      "</div>",
                elem_classes="markdown-container",
                show_label=False,
                )
            
        # 更新单元选择器的回调函数
    def update_unit_choices(grade):
        units = get_units_for_grade(grade)
        return gr.Dropdown(choices=units, value=units[0] if units else None)
    
    grade_selector.change(
        fn=update_unit_choices,
        inputs=grade_selector,
        outputs=unit_selector
    )

    submit_btn.click(
        fn=process_media,
        inputs=[video_input, file_input, grade_selector, unit_selector],
        outputs=text_output,
    )
    clear_btn.click(
        fn=lambda: [None, None, "1年级", get_units_for_grade("1年级")[0], "## 🚀 准备就绪\n请上传文件并点击开始分析按钮"],
        inputs=[],
        outputs=[video_input, file_input, grade_selector, unit_selector, text_output]
    )

if __name__ == "__main__":
    demo.launch(
        server_port=7860,
        show_api=False,
    )
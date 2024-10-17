import gradio as gr
import subprocess
import os
import tempfile
import json
import threading
import queue

def get_video_info(input_video):
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_video
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)

def process_video(input_video, start_time, end_time, width, height, fps, output_format, progress):
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, f'processed_video.{output_format}')

    command = [
        'ffmpeg',
        '-i', input_video,
        '-ss', str(start_time),
        '-to', str(end_time),
        '-vf', f'scale={int(width)}:{int(height)},fps={fps}',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-threads', '0',
        output_path
    ]

    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        progress(1.0, desc="处理完成")
        return output_path, process.stderr
    except subprocess.CalledProcessError as e:
        return None, e.stderr
    except Exception as e:
        return None, str(e)

def video_editor(input_video, start_time, end_time, width, height, fps, output_format, progress=gr.Progress()):
    if input_video is None:
        return None, "请先上传视频。"

    input_video_path = input_video.name
    result, log = process_video(input_video_path, start_time, end_time, width, height, fps, output_format, progress)

    if result:
        return result, f"处理完成！\n{log}"
    else:
        return None, f"处理失败，请检查输入参数。\n错误信息：\n{log}"

def update_params(input_video, video_info):
    if input_video is None:
        return [gr.update()] * 5 + [None]

    if video_info is None:
        video_info = get_video_info(input_video.name)

    video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
    
    if video_stream is None:
        return [gr.update()] * 5 + [None]

    duration = float(video_info['format']['duration'])
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    fps = eval(video_stream['r_frame_rate'])

    return [
        gr.update(maximum=duration, value=0),
        gr.update(maximum=duration, value=duration),
        gr.update(minimum=100, maximum=width*2, value=width),
        gr.update(minimum=100, maximum=height*2, value=height),
        gr.update(minimum=1, maximum=120, value=fps),
        video_info
    ]

with gr.Blocks(title="视频编辑器") as iface:
    gr.Markdown("# 视频编辑器")
    gr.Markdown("上传视频，设置参数，然后点击提交来编辑您的视频。")

    video_info = gr.State(None)

    with gr.Row():
        input_video = gr.File(label="输入视频")
        output_video = gr.Video(label="处理后的视频")

    with gr.Row():
        start_time = gr.Slider(minimum=0, maximum=3600, step=0.1, label="开始时间 (秒)", value=0)
        end_time = gr.Slider(minimum=0, maximum=3600, step=0.1, label="结束时间 (秒)", value=10)

    with gr.Row():
        width = gr.Slider(minimum=100, maximum=1920, step=10, label="输出宽度", value=640)
        height = gr.Slider(minimum=100, maximum=1080, step=10, label="输出高度", value=480)

    with gr.Row():
        fps = gr.Slider(minimum=1, maximum=120, step=1, label="帧率 (FPS)", value=30)
        output_format = gr.Dropdown(label="输出格式", choices=["mp4", "mov"], value="mp4")

    submit_btn = gr.Button("提交")

    log_output = gr.Textbox(label="处理日志", lines=10)

    input_video.change(
        update_params,
        inputs=[input_video, video_info],
        outputs=[start_time, end_time, width, height, fps, video_info]
    )

    submit_btn.click(
        video_editor,
        inputs=[input_video, start_time, end_time, width, height, fps, output_format],
        outputs=[output_video, log_output]
    )

if __name__ == "__main__":
    iface.queue()
    iface.launch()

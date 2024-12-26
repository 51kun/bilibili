import os
import time
import subprocess
import json

# 设置输入目录
input_directory = os.path.expanduser(r"~\Videos\bilibili")
output_directory = os.path.expanduser(r"~\Desktop\bili")  # 修改为桌面文件夹

# 确保输出目录存在
os.makedirs(output_directory, exist_ok=True)

def get_stream_type(file_path):
    """使用 ffmpeg 获取文件流的类型"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if "Video:" in result.stderr:
            return "video"
        elif "Audio:" in result.stderr:
            return "audio"
        return "unknown"
    except subprocess.SubprocessError as e:
        print(f"检查流类型时发生错误: {e}")
        return "error"

def save_trimmed_file(file_path, buffer_size_mb=1):
    """保存去除开头9个字节的文件，并检测音视频流类型"""
    start_time = time.time()
    buffer_size = buffer_size_mb * 1024 * 1024  # 转换为字节
    try:
        output_file_path = os.path.join(os.path.dirname(file_path), f"#{os.path.basename(file_path)}")
        
        with open(file_path, "rb") as file, open(output_file_path, "wb") as output_file:
            file.seek(9)  # 跳过文件开头的9个字节
            while chunk := file.read(buffer_size):
                output_file.write(chunk)

        print(f"文件已保存并覆盖: {output_file_path} (处理时间: {time.time() - start_time:.2f}秒)")

        # 检测文件流类型
        stream_type = get_stream_type(output_file_path)
        print(f"文件 {os.path.basename(output_file_path)} 流类型: {stream_type}")
        return output_file_path, stream_type
    except (FileNotFoundError, IOError) as e:
        print(f"处理文件时发生错误: {e}")
        return None, None

def clean_title(title):
    """清理标题中的无效字符"""
    return "".join(x for x in title if x.isalnum() or x in " _-")

def process_m4s_files(directory_path):
    """处理目录中一级子目录内的 .m4s 文件并合成音视频流"""
    if not os.path.isabs(directory_path):
        print("请提供目录的绝对路径。")
        return

    if not os.path.exists(directory_path):
        print(f"目录 {directory_path} 不存在。")
        return

    print(f"目录 {directory_path} 的一级子目录中的 .m4s 文件如下：")
    for entry in os.scandir(directory_path):
        if entry.is_dir(follow_symlinks=False):  # 仅检查一级子目录
            subdir = entry.path
            json_file_path = os.path.join(subdir, "videoInfo.json")
            if not os.path.exists(json_file_path):
                print(f"在 {subdir} 中没有找到 videoInfo.json 文件。跳过此目录。")
                continue

            try:
                with open(json_file_path, "r", encoding='utf-8') as json_file:
                    video_info = json.load(json_file)
                    title = video_info.get("title", "title")
                    group_title = video_info.get("groupTitle", "groupTitle")
                    p = video_info.get("p", 1)
                    safe_title = clean_title(title)
                    safe_group_title = clean_title(group_title)
            except (json.JSONDecodeError, IOError) as e:
                print(f"读取 videoInfo.json 时发生错误: {e}")
                continue

            video_file, audio_file = None, None

            # 查找视频流和音频流，仅选择文件名带 # 的 m4s 文件
            for file in os.scandir(subdir):
                if file.is_file() and file.name.endswith(".m4s") and '#' in file.name:
                    stream_type = get_stream_type(file.path)
                    if stream_type == "video":
                        video_file = file.path
                    elif stream_type == "audio":
                        audio_file = file.path

            if video_file and audio_file:
                print(f"合成文件: 视频流 {video_file} 和 音频流 {audio_file}")

                # 合成音视频流
                output_file_name = f"{safe_group_title}_{p}_{safe_title}.mp4" if safe_group_title != safe_title else f"{safe_group_title}_{p}.mp4"
                output_file_path = os.path.join(output_directory, output_file_name)

                # 使用 ffmpeg 合成音视频流，不进行重新编码，使用 CUDA 硬件加速
                ffmpeg_command = [
                    "ffmpeg",
                    "-y",  # 覆盖输出文件
                    "-loglevel", "error",  # 只显示错误信息
                    "-hwaccel", "cuda",  # 启用 CUDA 硬件加速
                    "-i", video_file,  # 输入视频文件
                    "-i", audio_file,  # 输入音频文件
                    "-map", "0:v:0",  # 映射视频流
                    "-map", "1:a:0",  # 映射音频流
                    "-c:v", "copy",  # 视频流复制（不重新编码）
                    "-c:a", "copy",  # 音频流复制（不重新编码）
                    output_file_path  # 输出文件路径
                ]

                # 执行合成命令
                subprocess.run(ffmpeg_command)
                print(f"合成完成: {output_file_path}")

                # 删除临时生成的 .m4s 文件
                os.remove(video_file)
                os.remove(audio_file)
                print(f"删除临时文件: {video_file} 和 {audio_file}")

def process_directory_files(input_directory):
    """处理输入目录下的所有子文件夹中的 m4s 文件"""
    for root, dirs, files in os.walk(input_directory):
        m4s_files = [f for f in files if f.endswith('.m4s') and '#' not in f]

        if m4s_files:
            print(f"文件夹 {os.path.basename(root)} 中的 m4s 文件：")
            for m4s_file in m4s_files:
                print(f"  {m4s_file}")
                m4s_file_path = os.path.join(root, m4s_file)
                save_trimmed_file(m4s_file_path)

if __name__ == "__main__":
    # 先处理 m4s 文件，然后再处理合成音视频流
    process_directory_files(input_directory)
    process_m4s_files(input_directory)

import os
import subprocess
import json
import time

def save_trimmed_file(file_path, output_file_path, buffer_size_mb=1):
    start_time = time.time()
    buffer_size = buffer_size_mb * 1024 * 1024  # 将 MB 转换为字节
    try:
        with open(file_path, "rb") as file:
            file.seek(9)  # 跳过文件开头的9个字节
            with open(output_file_path, "wb") as output_file:
                while True:
                    chunk = file.read(buffer_size)
                    if not chunk:
                        break
                    output_file.write(chunk)
        elapsed_time = time.time() - start_time
        print(f"文件已保存并覆盖: {output_file_path} (处理时间: {elapsed_time:.2f}秒)")
    except (FileNotFoundError, IOError) as e:
        print(f"处理文件时发生错误: {e}")

def process_directory(directory_path, output_directory):
    if not os.path.isabs(directory_path) or not os.path.isabs(output_directory):
        print("请提供目录的绝对路径。")
        return

    os.makedirs(output_directory, exist_ok=True)

    for entry in os.scandir(directory_path):
        if not entry.is_dir():
            continue

        subdir = entry.path

        m4s_files = [os.path.join(subdir, f) for f in os.listdir(subdir) if f.endswith('.m4s')]
        if len(m4s_files) != 2:
            print(f"在子目录 {subdir} 中没有找到两个 .m4s 文件。")
            continue
        
        video_file_path, audio_file_path = m4s_files
        trimmed_video_file_path = os.path.join(output_directory, f"#{os.path.basename(video_file_path)}")
        trimmed_audio_file_path = os.path.join(output_directory, f"#{os.path.basename(audio_file_path)}")

        save_trimmed_file(video_file_path, trimmed_video_file_path)
        save_trimmed_file(audio_file_path, trimmed_audio_file_path)

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
                safe_title = "".join(x for x in title if x.isalnum() or x in " _-")
                safe_group_title = "".join(x for x in group_title if x.isalnum() or x in " _-")
        except (json.JSONDecodeError, IOError) as e:
            print(f"读取 videoInfo.json 时发生错误: {e}")
            continue

        # 明确指定封面图片的文件名
        image_path = os.path.join(subdir, "image.jpg")
        if not os.path.exists(image_path):
            print(f"在 {subdir} 中没有找到 image.jpg 文件。跳过此目录。")
            continue

        output_file_name = f"{safe_group_title}_{p}_{safe_title}.mp4"
        output_file_path = os.path.join(output_directory, output_file_name)

        ffmpeg_command = [
            "ffmpeg",
            "-y",
            "-loglevel", "error",  # 只显示错误信息
            "-hwaccel", "cuda",
            "-i", trimmed_video_file_path,  # 输入视频文件
            "-i", trimmed_audio_file_path,  # 输入音频文件
            "-i", image_path,  # 输入封面图片
            "-map", "0:v:0",  # 映射视频流
            "-map", "1:a:0",  # 映射音频流
            "-map", "2",      # 映射封面图片流
            "-c:v", "copy",  # 视频编码
            "-c:a", "copy",  # 音频编码
            "-disposition:2", "attached_pic",  # 指定封面图片
            output_file_path  # 输出文件路径
        ]

        ffmpeg_start_time = time.time()
        try:
            subprocess.run(ffmpeg_command, check=True)
            ffmpeg_elapsed_time = time.time() - ffmpeg_start_time
            print(f"成功合成为 {output_file_path} (处理时间: {ffmpeg_elapsed_time:.2f}秒)")
        except subprocess.CalledProcessError as e:
            print(f"合并文件时发生错误: {e}")

        # 删除临时文件
        for file_path in [trimmed_video_file_path, trimmed_audio_file_path]:
            try:
                os.remove(file_path)
                print(f"已删除处理后的文件: {file_path}")
            except (FileNotFoundError, IOError) as e:
                print(f"删除文件时发生错误: {e}")

if __name__ == "__main__":
    input_directory = r"C:\Users\wuwuy\Videos\bilibili"
    output_directory = r"C:\Users\wuwuy\Desktop\bili"
    buffer_size_mb = 1024  # 以 MB 为单位设置 buffer_size
    process_directory(input_directory, output_directory)

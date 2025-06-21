
from oss2 import Auth, Bucket, exceptions
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# OSS初始化配置
auth = Auth(os.getenv('OSS_ACCESS_KEY'), os.getenv('OSS_SECRET_KEY'))
bucket = Bucket(
    auth,
    os.getenv('OSS_ENDPOINT'),
    os.getenv('OSS_BUCKET_NAME')
)


def generate_secure_filename(filename):
    """生成带时间戳的安全文件名[1](@ref)"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1][1:].lower()
    return f"{base_name}_{timestamp}.{extension}"


def up_video(video_file):
    """处理视频上传的核心函数"""
    try:
        # 生成OSS存储路径
        secure_name = generate_secure_filename(os.path.basename(video_file))
        oss_path = f"{video_file}{secure_name}"

        # 上传到OSS
        with open(video_file, 'rb') as f:
            result = bucket.put_object(oss_path, f)

        if result.status != 200:
            raise exceptions.OssError("OSS上传失败")

        # 生成访问链接
        download_url = bucket.sign_url('GET', oss_path, 3600)
        return download_url

    except Exception as e:
        return f"处理失败: {str(e)}"

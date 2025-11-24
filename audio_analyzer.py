import librosa
import numpy as np
import requests
import tempfile
import os
from pytube import YouTube

def download_audio_sample(video_url, duration=30):
    """下载视频的音频样本（前30秒）"""
    try:
        yt = YouTube(video_url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
            audio_stream.download(filename=tmp_file.name)
            return tmp_file.name
    except:
        return None

def analyze_voice_content(audio_file):
    """分析音频文件中的人声内容"""
    try:
        # 加载音频（只分析前30秒）
        y, sr = librosa.load(audio_file, duration=30)
        
        # 提取音频特征
        # 1. MFCC特征（人声特征）
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # 2. 频谱质心（音调特征）
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        
        # 3. 过零率（语音活动指标）
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        
        # 4. 频谱带宽
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        
        # 人声检测逻辑
        voice_indicators = {
            'avg_spectral_centroid': np.mean(spectral_centroids),
            'avg_zcr': np.mean(zcr),
            'avg_bandwidth': np.mean(spectral_bandwidth),
            'mfcc_variance': np.var(mfccs)
        }
        
        # 人声判断规则
        is_voice = (
            1000 < voice_indicators['avg_spectral_centroid'] < 4000 and  # 人声频率范围
            voice_indicators['avg_zcr'] > 0.01 and  # 语音活动
            voice_indicators['mfcc_variance'] > 10  # 语音变化
        )
        
        return {
            'has_voice': is_voice,
            'confidence': min(voice_indicators['mfcc_variance'] / 50, 1.0),
            'features': voice_indicators
        }
        
    except Exception as e:
        print(f"音频分析错误: {e}")
        return {'has_voice': False, 'confidence': 0.0, 'features': {}}
    
    finally:
        # 清理临时文件
        if os.path.exists(audio_file):
            os.unlink(audio_file)

def detect_voice_in_video(video_url):
    """检测YouTube视频中的人声"""
    # 下载音频样本
    audio_file = download_audio_sample(video_url)
    if not audio_file:
        return {'has_voice': None, 'confidence': 0.0, 'error': '无法下载音频'}
    
    # 分析音频
    result = analyze_voice_content(audio_file)
    return result
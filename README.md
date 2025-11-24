# Content Fetching Analyzer

Define the target YouTube channel, fetch the top 100 videos with their link, view amount, time length, date published, description, hashtags, isVoiceovered.

## Features

- Target specific YouTube channels for analysis
- Fetch top 100 videos from the channel
- Extract comprehensive video metadata:
  - Video links
  - View counts
  - Duration
  - Publication dates (with timezone support)
  - Descriptions
  - Hashtags
  - **Advanced Voice Detection** (keyword + audio analysis)
- Real-time sorting and filtering
- Multi-timezone support
- Interactive data visualization

## Getting Started

### Prerequisites

- Python 3.8+
- YouTube Data API key
- **Optional**: FFmpeg (for advanced audio analysis)

### Installation

```bash
git clone https://github.com/WenxinWangEngineer/content_fetching_analyzer.git
cd content_fetching_analyzer
```

## Usage

### 快速开始

1. **基础安装**:
```bash
pip3 install -r requirements.txt
```

2. **高级音频分析** (可选，提供更准确的人声检测):
```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
# Windows
# 下载 FFmpeg 并添加到 PATH

pip3 install librosa pytube
```

3. **获取YouTube API密钥**:
   - 访问 [Google Cloud Console](https://console.developers.google.com/)
   - 创建项目并启用YouTube Data API v3
   - 创建API密钥

4. **启动应用**:
```bash
python3 run.py
```

5. 在浏览器中打开 http://localhost:8501

### 功能说明

- 🔗 **频道分析** - 输入YouTube频道链接自动识别
- 🔑 **API集成** - 使用YouTube Data API v3获取数据
- 🌍 **多时区支持** - 支持PT/ET/CST/JST/GMT/UTC时区
- 🎧 **智能人声检测** - 双重检测机制：
  - **关键词检测** - 基于标题和描述的快速分析
  - **音频分析** - 使用librosa进行深度音频特征提取
- 📊 **实时排序** - 按观看量、发布日期、配音状态排序
- 📥 **数据导出** - 导出完整CSV文件包含所有分析结果

### 输出数据

CSV文件包含以下字段:
- **视频标题** - 可点击跳转到YouTube
- **视频链接** - 完整YouTube URL
- **观看量** - 数值格式，支持排序
- **视频时长** - HH:MM:SS格式
- **发布日期** - 包含时区和星期几
- **视频描述** - 前500字符
- **标签** - 提取的hashtags
- **人声检测** - 布尔值 + 置信度评分
- **检测方法** - keyword/audio标识

## 🎵 人声检测技术

### 关键词检测
- 支持中英文关键词匹配
- 识别配音、解说、教学等人声内容
- 排除纯音乐、环境声等非人声内容

### 音频分析 (Advanced)
- 使用**librosa**进行音频特征提取
- **MFCC特征** - 人声特征识别
- **频谱质心** - 音调特征分析
- **过零率** - 语音活动检测
- **频谱带宽** - 音频复杂度分析
- 人声频率范围检测 (1000-4000Hz)
- 30秒音频样本分析，平衡准确度和速度

### 技术栈
- **Frontend**: Streamlit (极简黑白UI)
- **API**: YouTube Data API v3
- **Audio**: librosa + pytube
- **Data**: pandas + numpy
- **Export**: CSV with UTF-8-BOM encoding

## 🚀 性能优化

- **智能缓存** - 使用session state避免重复API调用
- **批量处理** - 一次性获取50个视频信息
- **渐进式加载** - 实时显示处理进度
- **降级处理** - 音频分析失败时自动使用关键词检测

## 🔧 故障排除

### 音频分析不可用
```bash
# 安装音频分析依赖
pip install librosa pytube numpy

# macOS安装FFmpeg
brew install ffmpeg

# 验证安装
python -c "import librosa; print('Audio analysis ready!')"
```

### API配额限制
- YouTube Data API v3 每日配额：10,000 units
- 每个视频查询消耗：~5 units
- 建议：分批处理大量视频

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - 详见 LICENSE 文件
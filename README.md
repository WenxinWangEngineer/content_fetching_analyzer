# Content Fetching Analyzer

Define the target YouTube channel, fetch the top 100 videos with their link, view amount, time length, date published, description, hashtags, isVoiceovered.

## Features

- Target specific YouTube channels for analysis
- Fetch top 100 videos from the channel
- Extract comprehensive video metadata:
  - Video links
  - View counts
  - Duration
  - Publication dates
  - Descriptions
  - Hashtags
  - Voice-over detection

## Getting Started

### Prerequisites

- Python 3.x
- YouTube Data API key

### Installation

```bash
git clone https://github.com/WenxinWangEngineer/content_fetching_analyzer.git
cd content_fetching_analyzer
```

## Usage

### 快速开始

1. 安装依赖:
```bash
pip3 install -r requirements.txt
```

2. 获取YouTube API密钥:
   - 访问 [Google Cloud Console](https://console.developers.google.com/)
   - 创建项目并启用YouTube Data API v3
   - 创建API密钥

3. 启动应用:
```bash
python3 run.py
```

4. 在浏览器中打开 http://localhost:8501

### 功能说明

- 🔗 输入YouTube频道链接
- 🔑 输入YouTube API密钥
- 📊 自动分析频道前100个视频（或全部视频如果少于100个）
- 📥 导出CSV文件包含所有视频数据

### 输出数据

CSV文件包含以下字段:
- 视频标题
- 视频链接
- 观看量
- 视频时长
- 发布日期
- 视频描述
- 标签
- 配音检测结果

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[License information to be added]
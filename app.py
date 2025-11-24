import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import re
from datetime import datetime
import csv
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="📊 YouTube Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 黑白极简样式
st.markdown("""
<style>
    .main { background-color: #ffffff; }
    .stApp { background-color: #ffffff; }
    .css-1d391kg { background-color: #000000; }
    .stButton > button {
        background-color: #000000;
        color: #ffffff;
        border: 2px solid #000000;
        border-radius: 4px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #ffffff;
        color: #000000;
        border: 2px solid #000000;
    }
    .stTextInput > div > div > input {
        border: 2px solid #000000;
        border-radius: 4px;
    }
    h1 { color: #000000; text-align: center; }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 4px;
        border: 1px solid #000000;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def extract_channel_id(url):
    """从YouTube频道URL提取频道ID"""
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_channel_info(youtube, channel_input):
    """获取频道信息"""
    try:
        # 如果是完整的频道ID
        if channel_input.startswith('UC') and len(channel_input) == 24:
            response = youtube.channels().list(
                part='snippet,statistics',
                id=channel_input
            ).execute()
            if response['items']:
                return response['items'][0]
        
        # 尝试通过搜索找到频道
        search_response = youtube.search().list(
            part='snippet',
            q=channel_input,
            type='channel',
            maxResults=5
        ).execute()
        
        if search_response['items']:
            # 查找最匹配的频道
            for item in search_response['items']:
                channel_id = item['snippet']['channelId']
                channel_response = youtube.channels().list(
                    part='snippet,statistics',
                    id=channel_id
                ).execute()
                
                if channel_response['items']:
                    channel = channel_response['items'][0]
                    # 检查是否匹配
                    custom_url = channel['snippet'].get('customUrl', '').lower()
                    if (channel_input.lower() in custom_url or 
                        custom_url in channel_input.lower()):
                        return channel
            
            # 如果没有精确匹配，返回第一个结果
            channel_id = search_response['items'][0]['snippet']['channelId']
            channel_response = youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            ).execute()
            
            if channel_response['items']:
                return channel_response['items'][0]
                
    except Exception as e:
        print(f"Error getting channel info: {e}")
    
    return None

def get_videos(youtube, channel_id, max_results=100):
    """获取频道视频"""
    videos = []
    
    # 获取上传播放列表ID
    channel_response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    
    uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # 获取视频列表
    next_page_token = None
    while len(videos) < max_results:
        playlist_response = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_playlist_id,
            maxResults=min(50, max_results - len(videos)),
            pageToken=next_page_token
        ).execute()
        
        video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_response['items']]
        
        # 获取视频详细信息
        videos_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        for video in videos_response['items']:
            videos.append(video)
        
        next_page_token = playlist_response.get('nextPageToken')
        if not next_page_token:
            break
    
    return videos[:max_results]

def parse_duration(duration):
    """解析YouTube时长格式"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return "00:00:00"

def extract_hashtags(description):
    """提取描述中的标签"""
    hashtags = re.findall(r'#\w+', description)
    return ', '.join(hashtags) if hashtags else ''

def detect_voiceover(title, description):
    """简单的配音检测（基于关键词）"""
    voiceover_keywords = ['voiceover', 'narration', 'commentary', '配音', '解说', 'voice over']
    text = (title + ' ' + description).lower()
    return any(keyword in text for keyword in voiceover_keywords)

def main():
    st.title("📊 YouTube频道分析器")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### 🔗 频道信息")
        channel_url = st.text_input("YouTube频道链接", 
                                   value="https://www.youtube.com/@tiffanywangmeditation",
                                   placeholder="https://www.youtube.com/@channelname")
        
    with col2:
        st.markdown("### 🔑 API密钥")
        api_key = st.text_input("YouTube API Key", 
                               value="AIzaSyDrb_aKdgPLfinkgVJfzdKA9F1fgdF2yrg",
                               type="password")
    
    with col3:
        st.markdown("### 🌍 时区选择")
        timezone_options = {
            "美国太平洋时间 (PT)": "America/Los_Angeles",
            "美国东部时间 (ET)": "America/New_York", 
            "中国标准时间 (CST)": "Asia/Shanghai",
            "日本标准时间 (JST)": "Asia/Tokyo",
            "英国时间 (GMT)": "Europe/London",
            "协调世界时 (UTC)": "UTC"
        }
        selected_tz = st.selectbox("选择时区", list(timezone_options.keys()))
        timezone_str = timezone_options[selected_tz]
    
    if st.button("🚀 开始分析", use_container_width=True):
        if not api_key:
            st.error("❌ 请填写API密钥")
            return
        
        # 如果没有输入频道链接，使用默认频道
        if not channel_url:
            channel_url = "https://www.youtube.com/@tiffanywangmeditation"
        
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            with st.spinner("🔍 正在获取频道信息..."):
                # 提取频道标识
                channel_input = extract_channel_id(channel_url)
                if not channel_input:
                    # 从URL中提取用户名
                    if '@' in channel_url:
                        channel_input = channel_url.split('@')[-1]
                    else:
                        channel_input = channel_url.split('/')[-1]
                
                print(f"Searching for channel: {channel_input}")  # Debug信息
                
                # 获取频道信息
                channel_info = get_channel_info(youtube, channel_input)
                if not channel_info:
                    st.error("❌ 无法找到频道，请检查链接")
                    return
                
                channel_id = channel_info['id']
                channel_title = channel_info['snippet']['title']
                video_count = int(channel_info['statistics']['videoCount'])
                
                st.success(f"✅ 找到频道: {channel_title}")
                
                # 显示频道统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>📺 总视频数</h3>
                        <h2>{video_count:,}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    subscriber_count = int(channel_info['statistics']['subscriberCount'])
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>👥 订阅者</h3>
                        <h2>{subscriber_count:,}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    view_count = int(channel_info['statistics']['viewCount'])
                    st.markdown(f"""
                    <div class="metric-card">
                        <h3>👀 总观看量</h3>
                        <h2>{view_count:,}</h2>
                    </div>
                    """, unsafe_allow_html=True)
            
            with st.spinner("📊 正在分析视频数据..."):
                # 确定要获取的视频数量
                max_videos = min(100, video_count)
                videos = get_videos(youtube, channel_id, max_videos)
                
                # 处理视频数据
                video_data = []
                for video in videos:
                    snippet = video['snippet']
                    statistics = video['statistics']
                    content_details = video['contentDetails']
                    
                    # 解析发布日期时间并转换为选定时区
                    pub_datetime_utc = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
                    if timezone_str == 'UTC':
                        pub_datetime_local = pub_datetime_utc
                        tz_abbr = 'UTC'
                    else:
                        pub_datetime_local = pub_datetime_utc.astimezone(ZoneInfo(timezone_str))
                        tz_abbr = selected_tz.split('(')[-1].replace(')', '')
                    
                    weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][pub_datetime_local.weekday()]
                    formatted_date = f"{pub_datetime_local.strftime('%Y-%m-%d %H:%M')} {tz_abbr} ({weekday_cn})"
                    
                    video_data.append({
                        'title': snippet['title'],
                        'link': f"https://www.youtube.com/watch?v={video['id']}",
                        'view_count': int(statistics.get('viewCount', 0)),
                        'duration': parse_duration(content_details['duration']),
                        'published_date': formatted_date,
                        'description': snippet.get('description', '')[:500],
                        'hashtags': extract_hashtags(snippet.get('description', '')),
                        'is_voiceover': detect_voiceover(snippet['title'], snippet.get('description', ''))
                    })
                
                # 存储数据到session state
                st.session_state.video_data = video_data
                st.session_state.channel_title = channel_title
                st.session_state.analysis_complete = True
                
        except Exception as e:
            st.error(f"❌ 发生错误: {str(e)}")
                
    # 如果分析完成，显示结果和排序选项
    if hasattr(st.session_state, 'analysis_complete') and st.session_state.analysis_complete:
        df = pd.DataFrame(st.session_state.video_data)
        
        # 显示结果
        st.markdown("---")
        
        # 排序选择
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📋 视频列表 ({len(st.session_state.video_data)} 个视频)")
        with col2:
            sort_options = {
                "观看量 (高到低)": ("view_count", False),
                "观看量 (低到高)": ("view_count", True),
                "发布日期 (最新)": ("published_date", False),
                "发布日期 (最早)": ("published_date", True),
                "配音检测 (有配音)": ("is_voiceover", False),
                "配音检测 (无配音)": ("is_voiceover", True)
            }
            selected_sort = st.selectbox("📊 排序方式", list(sort_options.keys()), key="sort_selector")
            sort_column, ascending = sort_options[selected_sort]
            
            # 应用排序
            df_sorted = df.sort_values(by=sort_column, ascending=ascending)
        
        # 生成CSV文件名
        csv_filename = f"{st.session_state.channel_title.replace(' ', '_')}_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 显示数据表格
        st.dataframe(
            df_sorted[['title', 'view_count', 'duration', 'published_date', 'is_voiceover']],
            use_container_width=True,
            column_config={
                'title': '标题',
                'view_count': '观看量',
                'duration': '时长',
                'published_date': '发布日期',
                'is_voiceover': '配音检测'
            }
        )
        
        # 下载按钮 - 使用排序后的DataFrame
        csv_data = df_sorted.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载完整CSV文件",
            data=csv_data.encode('utf-8-sig'),
            file_name=csv_filename,
            mime='text/csv',
            use_container_width=True
        )
        
        st.success(f"✅ 分析完成！共处理 {len(st.session_state.video_data)} 个视频")

if __name__ == "__main__":
    main()
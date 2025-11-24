import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import re
from datetime import datetime
import csv
from zoneinfo import ZoneInfo
try:
    from audio_analyzer import detect_voice_in_video
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    st.warning("⚠️ 音频分析功能不可用，请安装: pip install librosa pytube")

st.set_page_config(
    page_title="📊 YouTube Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 紧凑黑白样式
st.markdown("""
<style>
    .main { background-color: #ffffff; padding-top: 1rem; }
    .stApp { background-color: #ffffff; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stButton > button {
        background-color: #000000; color: #ffffff; border: 2px solid #000000;
        border-radius: 4px; font-weight: bold; height: 2.5rem;
    }
    .stButton > button:hover { background-color: #ffffff; color: #000000; }
    .stTextInput > div > div > input { border: 2px solid #000000; border-radius: 4px; height: 2.5rem; }
    .stSelectbox > div > div > div { height: 2.5rem; }
    h1 { color: #000000; text-align: center; margin-bottom: 0.5rem; font-size: 2rem; }
    h3 { margin-bottom: 0.3rem; font-size: 1rem; }
    .metric-card {
        background-color: #f8f9fa; padding: 0.5rem; border-radius: 4px;
        border: 1px solid #000000; text-align: center; margin-bottom: 0.5rem;
    }
    .metric-card h3 { font-size: 0.8rem; margin-bottom: 0.2rem; }
    .metric-card h2 { font-size: 1.2rem; margin: 0; }
    .stMarkdown { margin-bottom: 0.5rem; }
    hr { margin: 0.5rem 0; }
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

def detect_voiceover(title, description, video_url=None, use_audio_analysis=False):
    """增强的人声配音检测（基于关键词和音频分析）"""
    # 先进行关键词检测
    voice_keywords = [
        'voiceover', 'voice over', 'narration', 'narrator', 'commentary', 'spoken', 'talking',
        'guided', 'meditation', 'story', 'storytelling', 'reading', 'audiobook', 'podcast',
        'interview', 'conversation', 'discussion', 'lecture', 'tutorial', 'explanation',
        'teaching', 'instruction', 'speaking', 'talk', 'voice', 'audio', 'sound',
        '配音', '解说', '讲解', '教学', '教程', '故事', '导览', '冥想', '引导',
        '讲话', '讲座', '访谈', '对话', '讨论', '声音', '音频'
    ]
    
    non_voice_keywords = [
        'instrumental', 'music only', 'no voice', 'no talking', 'silent', 'ambient',
        'nature sounds', 'rain sounds', 'ocean sounds', 'white noise', 'background music',
        'piano only', 'guitar only', 'orchestral', 'classical music', 'jazz instrumental',
        '纯音乐', '无人声', '背景音乐', '环境声', '自然声', '雨声', '海洋声'
    ]
    
    text = (title + ' ' + description).lower()
    
    # 检查非人声关键词
    if any(keyword in text for keyword in non_voice_keywords):
        return {'has_voice': False, 'method': 'keyword', 'confidence': 0.9}
    
    # 检查人声关键词
    keyword_result = any(keyword in text for keyword in voice_keywords)
    
    # 如果启用音频分析且可用
    if use_audio_analysis and AUDIO_ANALYSIS_AVAILABLE and video_url:
        try:
            audio_result = detect_voice_in_video(video_url)
            if audio_result.get('has_voice') is not None:
                return {
                    'has_voice': audio_result['has_voice'],
                    'method': 'audio',
                    'confidence': audio_result.get('confidence', 0.5)
                }
        except:
            pass  # 音频分析失败，使用关键词结果
    
    return {'has_voice': keyword_result, 'method': 'keyword', 'confidence': 0.7 if keyword_result else 0.3}

def main():
    st.title("📊 YouTube频道分析器")
    
    # 紧凑输入区域
    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
    
    with col1:
        channel_url = st.text_input("🔗 YouTube频道链接", 
                                   value="https://www.youtube.com/@jasonstephensonmeditation",
                                   placeholder="频道链接")
        
    with col2:
        api_key = st.text_input("🔑 API密钥", 
                               value="AIzaSyDrb_aKdgPLfinkgVJfzdKA9F1fgdF2yrg",
                               type="password")
    
    with col3:
        timezone_options = {
            "PT": "America/Los_Angeles", "ET": "America/New_York", 
            "CST": "Asia/Shanghai", "JST": "Asia/Tokyo",
            "GMT": "Europe/London", "UTC": "UTC"
        }
        selected_tz = st.selectbox("🌍 时区", list(timezone_options.keys()))
        timezone_str = timezone_options[selected_tz]
    
    with col4:
        use_audio = st.checkbox("🎧 音频分析", value=False, disabled=not AUDIO_ANALYSIS_AVAILABLE)
    
    with col5:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 分析", use_container_width=True)
    
    if analyze_btn:
        if not api_key:
            st.error("❌ 请填写API密钥")
            return
        
        # 如果没有输入频道链接，使用默认频道
        if not channel_url:
            channel_url = "https://www.youtube.com/@jasonstephensonmeditation"
        
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
                
                st.success(f"✅ {channel_title}")
                
                # 紧凑统计显示
                col1, col2, col3 = st.columns(3)
                subscriber_count = int(channel_info['statistics']['subscriberCount'])
                view_count = int(channel_info['statistics']['viewCount'])
                
                with col1:
                    st.markdown(f'<div class="metric-card"><h3>📺 视频</h3><h2>{video_count:,}</h2></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="metric-card"><h3>👥 订阅</h3><h2>{subscriber_count:,}</h2></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="metric-card"><h3>👀 观看</h3><h2>{view_count:,}</h2></div>', unsafe_allow_html=True)
            
            with st.spinner("📊 正在分析视频数据..."):
                # 确定要获取的视频数量
                max_videos = min(100, video_count)
                videos = get_videos(youtube, channel_id, max_videos)
                
                # 处理视频数据
                video_data = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, video in enumerate(videos):
                    snippet = video['snippet']
                    statistics = video['statistics']
                    content_details = video['contentDetails']
                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                    
                    # 更新进度
                    progress = (i + 1) / len(videos)
                    progress_bar.progress(progress)
                    status_text.text(f"处理视频 {i+1}/{len(videos)}: {snippet['title'][:50]}...")
                    
                    # 解析发布日期时间
                    pub_datetime_utc = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
                    if timezone_str == 'UTC':
                        pub_datetime_local = pub_datetime_utc
                        tz_abbr = 'UTC'
                    else:
                        pub_datetime_local = pub_datetime_utc.astimezone(ZoneInfo(timezone_str))
                        tz_abbr = selected_tz
                    
                    weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][pub_datetime_local.weekday()]
                    formatted_date = f"{pub_datetime_local.strftime('%Y-%m-%d %H:%M')} {tz_abbr} ({weekday_cn})"
                    
                    # 人声检测
                    voice_result = detect_voiceover(
                        snippet['title'], 
                        snippet.get('description', ''),
                        video_url if use_audio else None,
                        use_audio
                    )
                    
                    video_data.append({
                        'title': snippet['title'],
                        'link': video_url,
                        'view_count': int(statistics.get('viewCount', 0)),
                        'duration': parse_duration(content_details['duration']),
                        'published_date': formatted_date,
                        'description': snippet.get('description', '')[:500],
                        'hashtags': extract_hashtags(snippet.get('description', '')),
                        'is_voiceover': voice_result['has_voice'],
                        'voice_confidence': voice_result['confidence'],
                        'detection_method': voice_result['method']
                    })
                
                progress_bar.empty()
                status_text.empty()
                
                # 存储数据到session state
                st.session_state.video_data = video_data
                st.session_state.channel_title = channel_title
                st.session_state.analysis_complete = True
                
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")
                
    # 如果分析完成，显示结果和排序选项
    if hasattr(st.session_state, 'analysis_complete') and st.session_state.analysis_complete:
        df = pd.DataFrame(st.session_state.video_data)
        
        # 紧凑结果显示
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**📋 视频列表 ({len(st.session_state.video_data)} 个)**")
        with col2:
            sort_options = {
                "观看量↓": ("view_count", False), "观看量↑": ("view_count", True),
                "最新": ("published_date", False), "最早": ("published_date", True),
                "有配音": ("is_voiceover", False), "无配音": ("is_voiceover", True)
            }
            selected_sort = st.selectbox("📊 排序", list(sort_options.keys()), key="sort_selector")
            sort_column, ascending = sort_options[selected_sort]
            df_sorted = df.sort_values(by=sort_column, ascending=ascending)
        with col3:
            csv_data = df_sorted.to_csv(index=False, encoding='utf-8-sig')
            csv_filename = f"{st.session_state.channel_title.replace(' ', '_')}_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            st.download_button("📥 CSV", csv_data.encode('utf-8-sig'), csv_filename, "text/csv", use_container_width=True)
        
        # 排序后重新设置索引从1开始
        df_display = df_sorted.copy().reset_index(drop=True)
        df_display.index = df_display.index + 1
        
        # 紧凑表格显示
        st.dataframe(
            df_display[['title', 'link', 'view_count', 'duration', 'published_date', 'is_voiceover']],
            use_container_width=True, height=400,
            column_config={
                'title': st.column_config.TextColumn('标题', width='large'),
                'link': st.column_config.LinkColumn('🔗', width='small'),
                'view_count': st.column_config.NumberColumn('观看量', width='small'),
                'duration': st.column_config.TextColumn('时长', width='small'),
                'published_date': st.column_config.TextColumn('发布日期', width='medium'),
                'is_voiceover': st.column_config.CheckboxColumn('🎤人声', width='small')
            }
        )

if __name__ == "__main__":
    main()
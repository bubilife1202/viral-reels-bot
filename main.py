#!/usr/bin/env python3
"""
Viral Reels Dashboard - Reddit에서 인기 영상 수집 및 Gemini AI 분석
"""

import os
import json
import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
import re

# 설정
SUBREDDITS = ["TikTokCringe", "funny"]
TOP_N = 3  # 각 서브레딧에서 가져올 영상 수
GEMINI_MODEL = "gemini-2.5-flash"  # Google Gemini 2.5 Flash
HTML_FILE = "index.html"


def get_reddit_top_posts(subreddit, limit=3):
    """Reddit에서 인기 게시물 가져오기 (RSS 피드 사용, xml.etree로 파싱)"""
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit={limit}"

    try:
        # 요청 간 딜레이 추가 (Reddit API 정책 준수)
        time.sleep(2)

        # HTTP 요청으로 RSS 피드 가져오기
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ViralReelsBot/1.0)'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # XML 파싱
        root = ET.fromstring(response.content)

        # Atom 네임스페이스 정의
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/'
        }

        # entry 요소들 찾기
        entries = root.findall('atom:entry', ns)

        if not entries:
            print(f"   ⚠️  피드가 비어있습니다.")
            return []

        posts = []
        for entry in entries[:limit]:
            # 제목과 링크 추출
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text if title_elem is not None else ""

            link_elem = entry.find('atom:link', ns)
            reddit_url = link_elem.get('href', '') if link_elem is not None else ""

            # 콘텐츠에서 영상 URL 추출
            content_elem = entry.find('atom:content', ns)
            content = content_elem.text if content_elem is not None else ""

            video_url = None

            # HTML 콘텐츠에서 영상 링크 찾기
            if content:
                soup = BeautifulSoup(content, 'html.parser')

                # 1. <a> 태그에서 영상 도메인 찾기
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if any(domain in href for domain in ["v.redd.it", "youtube.com", "youtu.be", "tiktok.com", "imgur.com/", "gfycat.com"]):
                        video_url = href
                        break

                # 2. 없으면 Reddit 자체 링크 사용
                if not video_url and "v.redd.it" in reddit_url:
                    video_url = reddit_url

            # 영상이 없어도 일단 수집 (Gemini가 텍스트로도 분석 가능)
            if not video_url:
                video_url = reddit_url  # Reddit 페이지 링크라도 추가

            posts.append({
                "title": title,
                "url": video_url,
                "reddit_url": reddit_url,
                "score": 0,  # RSS에는 점수 정보 없음
                "subreddit": subreddit
            })

        return posts
    except Exception as e:
        print(f"Error fetching from r/{subreddit}: {e}")
        return []


def analyze_with_gemini(posts):
    """Gemini AI로 영상 분석 (JSON 구조 반환)"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다!")

    # Gemini 클라이언트 초기화
    client = genai.Client(api_key=api_key)

    # 프롬프트 구성
    posts_summary = "\n\n".join([
        f"[영상 {i+1}]\n제목: {p['title']}\n출처: r/{p['subreddit']}\nURL: {p['url']}"
        for i, p in enumerate(posts)
    ])

    prompt = f"""너는 인스타 릴스 100만 팔로워 크리에이터야. Reddit 영상들을 분석해서 한국 릴스로 만들 때 필요한 정보를 JSON으로 출력해.

{posts_summary}

**각 영상마다 다음 JSON 형식으로 분석해:**

{{
  "videos": [
    {{
      "title": "15초로 요약한 릴스 제목 (한국어, 임팩트 있게)",
      "virality_score": 8,
      "difficulty": "Easy",
      "category": "Faceless",
      "hook_point": "첫 3초에 OO한 심리를 자극해서 터짐 (한 줄)",
      "korean_patch": "한국에서는 이런 밈/음원/상황으로 바꾸면 좋음",
      "script": "장면1: (0-3초) 후크 문구\\n장면2: (3-10초) 핵심 전개\\n장면3: (10-15초) 마무리 펀치라인\\n\\n자막: '핵심 자막 1-2줄'\\n해시태그: #태그1 #태그2 #태그3",
      "original_url": "원본 Reddit URL",
      "video_url": "영상 URL"
    }}
  ]
}}

**중요 규칙:**
- virality_score: 1~10 (AI가 판단한 바이럴 가능성)
- difficulty: "Easy" (초보 가능), "Medium" (연기 필요), "Hard" (편집 기술 필요)
- category: "Faceless" (얼굴 노출 X), "Skit" (상황극), "Trend" (챌린지), "Info" (정보성)
- 반드시 유효한 JSON만 출력 (추가 설명 금지)
- 각 필드는 실행 가능한 구체적 정보로 작성
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        # JSON 파싱
        content = response.text.strip()

        print(f"📥 Gemini AI 응답 길이: {len(content)} 문자")

        # JSON 추출 (```json 마크다운 제거)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        print(f"📝 JSON 추출 후 길이: {len(content)} 문자")

        data = json.loads(content)
        videos = data.get("videos", [])

        print(f"✅ JSON 파싱 성공: {len(videos)}개 영상 데이터")
        return videos
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        print(f"📄 응답 내용 (처음 1000자):")
        print(response.text[:1000])
        print("\n... (생략) ...")
        return None
    except Exception as e:
        print(f"❌ Gemini API 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def remove_old_updates(html_content, current_time, days=7):
    """7일 이상 된 업데이트 섹션 삭제"""
    import re

    # 모든 Update 주석과 날짜 찾기
    update_pattern = r'<!-- Update: ([\d\-: ]+) -->'
    matches = list(re.finditer(update_pattern, html_content))

    if len(matches) <= 1:
        # 업데이트가 1개 이하면 삭제하지 않음
        return html_content

    cutoff_date = current_time - timedelta(days=days)
    sections_to_remove = []

    for i, match in enumerate(matches):
        update_time_str = match.group(1)
        try:
            # 업데이트 시간 파싱 (KST)
            kst = timezone(timedelta(hours=9))
            update_time = datetime.strptime(update_time_str, "%Y-%m-%d %H:%M:%S")
            update_time = update_time.replace(tzinfo=kst)

            # 7일 이상 된 경우
            if update_time < cutoff_date:
                # 이 섹션의 시작과 끝 찾기
                section_start = match.start()

                # 다음 Update 주석 또는 "여기에 새로운 콘텐츠가 추가됩니다" 주석까지
                if i + 1 < len(matches):
                    section_end = matches[i + 1].start()
                else:
                    # 마지막 섹션인 경우, "여기에 새로운 콘텐츠가 추가됩니다" 주석까지
                    footer_marker = html_content.find("<!-- 여기에 새로운 콘텐츠가 추가됩니다 -->", section_start)
                    if footer_marker != -1:
                        section_end = footer_marker
                    else:
                        section_end = len(html_content)

                sections_to_remove.append((section_start, section_end))
                print(f"🗑️  7일 이상 된 업데이트 삭제: {update_time_str}")

        except Exception as e:
            print(f"⚠️  날짜 파싱 오류: {update_time_str} - {e}")
            continue

    # 뒤에서부터 삭제 (인덱스가 변하지 않도록)
    for start, end in reversed(sections_to_remove):
        html_content = html_content[:start] + html_content[end:]

    return html_content


def generate_video_cards(videos):
    """비디오 JSON 데이터로 HTML 카드 생성"""
    cards_html = ""

    difficulty_colors = {
        "Easy": "success",
        "Medium": "warning",
        "Hard": "danger"
    }

    category_icons = {
        "Faceless": "🎭",
        "Skit": "🎬",
        "Trend": "🔥",
        "Info": "💡"
    }

    for video in videos:
        difficulty = video.get("difficulty", "Medium")
        category = video.get("category", "Trend")
        color = difficulty_colors.get(difficulty, "secondary")
        icon = category_icons.get(category, "🎬")

        # 스크립트를 이스케이프 처리
        script_escaped = video.get("script", "").replace("'", "\\'").replace("\n", "\\n")

        cards_html += f"""
        <div class="reel-card" data-category="{category}" data-difficulty="{difficulty}">
            <div class="card-header">
                <div class="badges">
                    <span class="badge badge-{color}">{difficulty}</span>
                    <span class="badge badge-score">바이럴 {video.get('virality_score', 5)}/10</span>
                </div>
                <span class="category-icon">{icon}</span>
            </div>
            <h3 class="card-title">{video.get('title', '제목 없음')}</h3>

            <div class="card-section">
                <h4>🎯 바이럴 포인트</h4>
                <p>{video.get('hook_point', '분석 중...')}</p>
            </div>

            <div class="card-section">
                <h4>🇰🇷 한국화 제안</h4>
                <p>{video.get('korean_patch', '원본 그대로 사용 가능')}</p>
            </div>

            <div class="card-section script-section">
                <div class="script-header">
                    <h4>📝 스크립트</h4>
                    <button class="copy-btn" onclick="copyScript('{script_escaped}')">
                        📋 복사
                    </button>
                </div>
                <pre class="script-content">{video.get('script', '스크립트 없음')}</pre>
            </div>

            <div class="card-footer">
                <a href="{video.get('original_url', '#')}" class="btn btn-secondary" target="_blank">원본 보기</a>
                <a href="{video.get('video_url', '#')}" class="btn btn-primary" target="_blank">영상 보기</a>
            </div>
        </div>
"""

    return cards_html


def update_html(videos):
    """index.html 파일 업데이트 (최신 내용을 상단에 추가)"""

    # HTML 파일이 없으면 초기 템플릿 생성
    if not os.path.exists(HTML_FILE):
        create_initial_html()

    # 기존 HTML 읽기
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 현재 날짜 생성 (한국 시간대)
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)

    # 한국어 요일
    weekdays_kr = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    weekday_kr = weekdays_kr[now.weekday()]

    date_str = now.strftime(f"%Y년 %m월 %d일 {weekday_kr}")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 비디오 카드 생성
    cards_html = generate_video_cards(videos)

    # 새로운 콘텐츠 블록 생성
    new_content = f"""
    <!-- Update: {timestamp} -->
    <div class="date-section">
      <h2 class="date-badge">{date_str}</h2>
      <div class="cards-grid">
{cards_html}
      </div>
    </div>
"""

    # <!-- CONTENT_START --> 마커 다음에 새 콘텐츠 삽입
    if "<!-- CONTENT_START -->" in html_content:
        html_content = html_content.replace(
            "<!-- CONTENT_START -->",
            f"<!-- CONTENT_START -->\n{new_content}"
        )
    else:
        # 마커가 없으면 container 안에 추가
        html_content = html_content.replace(
            '<div id="content">',
            f'<div id="content">\n{new_content}'
        )

    # 7일 이상 된 콘텐츠 삭제
    html_content = remove_old_updates(html_content, now, days=7)

    # 파일 저장
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ {HTML_FILE} 업데이트 완료!")


def create_initial_html():
    """초기 HTML 템플릿 생성 (Dark 테마 + 필터링)"""
    initial_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>바이럴 릴스 분석 대시보드</title>

    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8245597797545485"
     crossorigin="anonymous"></script>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: #0a0a0a;
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
        }

        .header {
            background: #121212;
            border-bottom: 1px solid #1f1f1f;
            padding: 2rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: #888;
            font-size: 0.9rem;
        }

        .filters {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 2rem;
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            color: #e0e0e0;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }

        .filter-btn:hover {
            background: #2a2a2a;
            border-color: #3a3a3a;
        }

        .filter-btn.active {
            background: #2563eb;
            border-color: #2563eb;
            color: #fff;
        }

        #content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem 4rem;
        }

        .date-section {
            margin-bottom: 3rem;
        }

        .date-badge {
            display: inline-block;
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 1.5rem;
        }

        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
        }

        .reel-card {
            background: #121212;
            border: 1px solid #1f1f1f;
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s;
        }

        .reel-card:hover {
            border-color: #2a2a2a;
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .badges {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge-success {
            background: #10b981;
            color: #000;
        }

        .badge-warning {
            background: #f59e0b;
            color: #000;
        }

        .badge-danger {
            background: #ef4444;
            color: #fff;
        }

        .badge-score {
            background: #6366f1;
            color: #fff;
        }

        .category-icon {
            font-size: 1.5rem;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 1rem;
            line-height: 1.4;
        }

        .card-section {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #1f1f1f;
        }

        .card-section:last-of-type {
            border-bottom: none;
        }

        .card-section h4 {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .card-section p {
            font-size: 0.9rem;
            color: #d0d0d0;
            line-height: 1.5;
        }

        .script-section {
            background: #0a0a0a;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #1f1f1f;
        }

        .script-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .copy-btn {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            color: #e0e0e0;
            padding: 0.4rem 0.8rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }

        .copy-btn:hover {
            background: #2a2a2a;
        }

        .script-content {
            background: transparent;
            border: none;
            color: #b0b0b0;
            font-size: 0.85rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'SF Mono', Monaco, monospace;
        }

        .card-footer {
            display: flex;
            gap: 0.75rem;
            margin-top: 1rem;
        }

        .btn {
            flex: 1;
            padding: 0.6rem 1rem;
            border: none;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
            transition: all 0.2s;
            display: inline-block;
        }

        .btn-primary {
            background: #2563eb;
            color: #fff;
        }

        .btn-primary:hover {
            background: #1d4ed8;
        }

        .btn-secondary {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            color: #e0e0e0;
        }

        .btn-secondary:hover {
            background: #2a2a2a;
        }

        footer {
            background: #121212;
            border-top: 1px solid #1f1f1f;
            padding: 2rem;
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }

        footer a {
            color: #888;
            text-decoration: none;
            margin: 0 1rem;
        }

        footer a:hover {
            color: #e0e0e0;
        }

        @media (max-width: 768px) {
            .cards-grid {
                grid-template-columns: 1fr;
            }

            .filters {
                padding: 0 1rem;
            }

            #content {
                padding: 0 1rem 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>🎬 바이럴 릴스 분석 대시보드</h1>
            <p class="subtitle">실전 활용 가능한 릴스 아이디어 · 매일 오전 8시 업데이트</p>
        </div>
    </div>

    <div class="filters">
        <button class="filter-btn active" onclick="filterCards('all')">전체</button>
        <button class="filter-btn" onclick="filterCards('Faceless')">🎭 얼굴 노출 X</button>
        <button class="filter-btn" onclick="filterCards('Skit')">🎬 상황극</button>
        <button class="filter-btn" onclick="filterCards('Trend')">🔥 챌린지</button>
        <button class="filter-btn" onclick="filterCards('Info')">💡 정보성</button>
        <button class="filter-btn" onclick="filterCards('Easy')">초보자 추천</button>
    </div>

    <div id="content">
        <!-- CONTENT_START -->

        <!-- 여기에 새로운 콘텐츠가 추가됩니다 -->

    </div>

    <footer>
        <div>
            <a href="https://www.instagram.com/reels_code_official" target="_blank">📷 Instagram</a>
            <a href="https://www.threads.com/@reels_code_official" target="_blank">🧵 Threads</a>
        </div>
        <p style="margin-top: 1rem;">자동 업데이트: 매일 오전 8시 (KST)</p>
    </footer>

    <script>
        // 필터링 기능
        function filterCards(filter) {
            const cards = document.querySelectorAll('.reel-card');
            const buttons = document.querySelectorAll('.filter-btn');

            // 버튼 활성화 상태 변경
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            // 카드 필터링
            cards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else if (filter === 'Easy') {
                    card.style.display = card.dataset.difficulty === 'Easy' ? 'block' : 'none';
                } else {
                    card.style.display = card.dataset.category === filter ? 'block' : 'none';
                }
            });
        }

        // 스크립트 복사 기능
        function copyScript(text) {
            navigator.clipboard.writeText(text).then(() => {
                event.target.textContent = '✅ 복사됨';
                setTimeout(() => {
                    event.target.textContent = '📋 복사';
                }, 2000);
            }).catch(err => {
                console.error('복사 실패:', err);
                alert('복사에 실패했습니다.');
            });
        }
    </script>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(initial_html)

    print(f"✅ 초기 {HTML_FILE} 생성 완료!")


def main():
    """메인 실행 함수"""
    print("🚀 Viral Reels Dashboard 시작...")
    print(f"📅 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Reddit에서 영상 수집
    all_posts = []
    for subreddit in SUBREDDITS:
        print(f"\n📡 r/{subreddit}에서 데이터 수집 중...")
        posts = get_reddit_top_posts(subreddit, TOP_N)
        all_posts.extend(posts)
        print(f"   ✅ {len(posts)}개 게시물 수집 완료")

    if not all_posts:
        print("❌ 수집된 게시물이 없습니다.")
        return

    print(f"\n📊 총 {len(all_posts)}개 영상 수집 완료")

    # 2. Gemini AI로 분석
    print("\n🤖 Gemini AI 분석 시작...")
    analysis = analyze_with_gemini(all_posts)

    if analysis is None:
        print("❌ AI 분석 실패")
        return

    if not analysis or len(analysis) == 0:
        print("⚠️  분석 결과가 비어있습니다 (videos 배열이 빔)")
        return

    print(f"✅ AI 분석 완료 ({len(analysis)}개 영상)")

    # 3. HTML 업데이트
    print("\n📝 HTML 업데이트 중...")
    update_html(analysis)

    print("\n🎉 모든 작업 완료!")


if __name__ == "__main__":
    main()

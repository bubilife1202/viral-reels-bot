#!/usr/bin/env python3
"""
Viral Reels Dashboard - Reddit에서 인기 영상 수집 및 Gemini AI 분석
"""

import os
import json
import requests
import time
import feedparser
from datetime import datetime
from langchain_groq import ChatGroq
from bs4 import BeautifulSoup
import re

# 설정
SUBREDDITS = ["TikTokCringe", "funny"]
TOP_N = 3  # 각 서브레딧에서 가져올 영상 수
GROQ_MODEL = "llama3-70b-8192"  # 무료 티어: 하루 14,400 요청
HTML_FILE = "index.html"


def get_reddit_top_posts(subreddit, limit=3):
    """Reddit에서 인기 게시물 가져오기 (RSS 피드 사용)"""
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit={limit}"

    try:
        # 요청 간 딜레이 추가 (Reddit API 정책 준수)
        time.sleep(2)

        # RSS 피드 파싱
        feed = feedparser.parse(url)

        if not feed.entries:
            print(f"   ⚠️  피드가 비어있습니다.")
            return []

        posts = []
        for entry in feed.entries[:limit]:
            # 제목과 링크 추출
            title = entry.get("title", "")
            reddit_url = entry.get("link", "")

            # 콘텐츠에서 영상 URL 추출
            content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

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


def analyze_with_groq(posts):
    """Groq AI로 영상 분석"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY 환경변수가 설정되지 않았습니다!")

    llm = ChatGroq(
        model=GROQ_MODEL,
        groq_api_key=api_key,
        temperature=0.7
    )

    # 프롬프트 구성
    posts_summary = "\n\n".join([
        f"[영상 {i+1}]\n제목: {p['title']}\n출처: r/{p['subreddit']}\n인기도: {p['score']} 👍\nURL: {p['url']}"
        for i, p in enumerate(posts)
    ])

    prompt = f"""너는 100만 유튜버의 PD야. 아래 Reddit에서 오늘 인기있는 영상들을 분석해서, 한국 인스타그램 릴스에서 터질만한 콘텐츠 아이디어를 제안해줘.

{posts_summary}

**다음 형식으로 각 영상마다 분석 결과를 작성해줘:**

<div class='card mb-4 shadow-sm'>
  <div class='card-body'>
    <div class='d-flex justify-content-between align-items-center mb-3'>
      <h5 class='card-title mb-0'>🎬 [릴스 제목]</h5>
      <span class='badge bg-danger'>HOT</span>
    </div>

    <h6 class='text-muted mb-3'>📌 핵심 포인트</h6>
    <p class='card-text'>[이 영상의 바이럴 포인트와 한국에서 통할 이유]</p>

    <h6 class='text-muted mb-2'>🎭 각본 및 대본</h6>
    <p class='card-text'>[구체적인 장면 구성과 대사 예시]</p>

    <h6 class='text-muted mb-2'>📸 촬영 팁</h6>
    <p class='card-text'>[앵글, 편집 포인트, 효과 등]</p>

    <h6 class='text-muted mb-2'>🎵 추천 BGM</h6>
    <p class='card-text'>[분위기에 맞는 음악 제안]</p>

    <div class='mt-3'>
      <a href='[원본 Reddit URL]' class='btn btn-sm btn-outline-primary' target='_blank'>원본 보기</a>
      <a href='[영상 URL]' class='btn btn-sm btn-outline-success' target='_blank'>영상 보기</a>
    </div>
  </div>
</div>

**중요:**
- 반드시 위 HTML 구조를 정확히 따라서 작성해줘
- 각 영상마다 하나의 카드를 만들어줘
- [원본 Reddit URL]과 [영상 URL]은 실제 링크로 대체해줘
- 한국어로 자연스럽게 작성해줘
"""

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"Groq API 오류: {e}")
        return None


def update_html(analysis_html):
    """index.html 파일 업데이트 (최신 내용을 상단에 추가)"""

    # HTML 파일이 없으면 초기 템플릿 생성
    if not os.path.exists(HTML_FILE):
        create_initial_html()

    # 기존 HTML 읽기
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 현재 날짜 생성
    now = datetime.now()
    date_str = now.strftime("%Y년 %m월 %d일 %A")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 새로운 콘텐츠 블록 생성
    new_content = f"""
    <!-- Update: {timestamp} -->
    <div class="date-section mb-5">
      <h2 class="text-center mb-4">
        <span class="badge bg-primary">{date_str}</span>
      </h2>

      {analysis_html}

      <hr class="my-5">
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
            '<div class="container my-5">',
            f'<div class="container my-5">\n{new_content}'
        )

    # 파일 저장
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ {HTML_FILE} 업데이트 완료!")


def create_initial_html():
    """초기 HTML 템플릿 생성"""
    initial_html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 바이럴 릴스 아이디어 대시보드</title>

    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            padding-bottom: 50px;
        }

        .header {
            background: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 2rem 0;
            margin-bottom: 3rem;
        }

        .header h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
        }

        .container {
            max-width: 900px;
        }

        .card {
            border: none;
            border-radius: 15px;
            transition: transform 0.3s, box-shadow 0.3s;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }

        .card-title {
            color: #667eea;
            font-weight: bold;
        }

        .date-section h2 .badge {
            font-size: 1.2rem;
            padding: 0.6rem 1.5rem;
        }

        .text-muted {
            color: #6c757d !important;
            font-weight: 600;
        }

        .btn {
            border-radius: 20px;
        }

        hr {
            border: 2px solid rgba(255,255,255,0.3);
        }

        footer {
            text-align: center;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1 class="text-center">🔥 바이럴 릴스 아이디어 대시보드</h1>
            <p class="text-center text-muted">매일 아침 업데이트되는 인스타 릴스 콘텐츠 아이디어</p>
        </div>
    </div>

    <div class="container my-5">
        <!-- CONTENT_START -->

        <!-- 여기에 새로운 콘텐츠가 추가됩니다 -->

    </div>

    <footer>
        <p>🤖 Powered by Reddit API + Groq AI (Llama 3)</p>
        <p>자동 업데이트: 매일 오전 8시 (KST)</p>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
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

    # 2. Groq AI로 분석
    print("\n🤖 Groq AI 분석 시작...")
    analysis = analyze_with_groq(all_posts)

    if not analysis:
        print("❌ AI 분석 실패")
        return

    print("✅ AI 분석 완료")

    # 3. HTML 업데이트
    print("\n📝 HTML 업데이트 중...")
    update_html(analysis)

    print("\n🎉 모든 작업 완료!")


if __name__ == "__main__":
    main()

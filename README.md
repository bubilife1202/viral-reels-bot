# 🔥 Viral Reels Dashboard

매일 아침 자동으로 업데이트되는 **인스타그램 릴스 아이디어 대시보드**

Reddit에서 인기 영상을 수집하고, Google Gemini AI로 분석하여 한국 릴스에 최적화된 콘텐츠 아이디어를 제공합니다.

## ✨ 주요 기능

- 🤖 **완전 자동화**: GitHub Actions로 매일 오전 8시(KST) 자동 실행
- 💰 **운영 비용 0원**: Gemini Free API + GitHub Pages 무료 호스팅
- 📱 **모바일 최적화**: Bootstrap 기반 반응형 디자인
- 🎬 **AI 기반 분석**: 100만 유튜버 PD 관점의 콘텐츠 제안
- 🔄 **실시간 업데이트**: 최신 트렌드를 매일 아침 확인

## 🚀 빠른 시작 가이드

### 1️⃣ Google API 키 발급

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **Get API Key** 클릭
3. API 키 복사 (예: `AIzaSy...`)

### 2️⃣ GitHub Repository 설정

#### Secret 등록
1. GitHub 리포지토리 → **Settings** 탭
2. 왼쪽 메뉴에서 **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭
4. Secret 추가:
   - **Name**: `GOOGLE_API_KEY`
   - **Value**: 위에서 복사한 API 키 붙여넣기
5. **Add secret** 클릭

#### GitHub Pages 활성화
1. 리포지토리 → **Settings** 탭
2. 왼쪽 메뉴에서 **Pages** 클릭
3. **Source** 섹션에서:
   - **Branch**: `main` (또는 현재 브랜치) 선택
   - **Folder**: `/ (root)` 선택
4. **Save** 클릭
5. 페이지 상단에 URL 표시됨 (예: `https://username.github.io/viral-reels-dashboard/`)

### 3️⃣ 첫 실행 (수동)

GitHub Actions를 수동으로 실행하여 첫 콘텐츠 생성:

1. 리포지토리 → **Actions** 탭
2. 왼쪽에서 **Update Viral Reels Dashboard** 워크플로우 선택
3. **Run workflow** 버튼 클릭
4. **Run workflow** 확인

약 1~2분 후 `index.html`이 업데이트되고, GitHub Pages에 반영됩니다.

### 4️⃣ 웹사이트 접속

GitHub Pages URL로 접속하면 대시보드를 확인할 수 있습니다!

```
https://[YOUR-USERNAME].github.io/viral-reels-dashboard/
```

## 📂 프로젝트 구조

```
viral-reels-dashboard/
├── .github/
│   └── workflows/
│       └── update-dashboard.yml    # GitHub Actions 자동화 설정
├── main.py                          # 메인 스크립트
├── requirements.txt                 # Python 패키지 목록
├── index.html                       # 웹 대시보드 (자동 생성/업데이트)
├── .gitignore
└── README.md
```

## 🔧 기술 스택

- **Python 3.11**
- **langchain-google-genai**: Google Gemini API 연동
- **requests**: Reddit API 통신
- **Bootstrap 5**: 반응형 웹 디자인
- **GitHub Actions**: 자동화 스케줄링
- **GitHub Pages**: 무료 웹 호스팅

## ⚙️ 설정 변경

### 수집 소스 변경

`main.py` 파일에서 수정:

```python
SUBREDDITS = ["TikTokCringe", "funny"]  # 원하는 서브레딧 추가
TOP_N = 3  # 각 서브레딧에서 가져올 게시물 수
```

### 실행 시간 변경

`.github/workflows/update-dashboard.yml` 파일에서 cron 수정:

```yaml
schedule:
  - cron: '0 23 * * *'  # UTC 23시 = KST 08시
```

**시간 계산**: 한국시간(KST) - 9시간 = UTC 시간

예시:
- KST 07:00 → UTC 22:00 → `cron: '0 22 * * *'`
- KST 12:00 → UTC 03:00 → `cron: '0 3 * * *'`

## 🎨 커스터마이징

### 디자인 변경
`index.html`의 `<style>` 섹션에서 CSS 수정

### AI 프롬프트 변경
`main.py`의 `analyze_with_gemini()` 함수에서 `prompt` 변수 수정

## 🛠️ 로컬 테스트

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
export GOOGLE_API_KEY="your-api-key-here"

# 3. 스크립트 실행
python main.py
```

실행 후 `index.html`이 업데이트되며, 브라우저로 열어서 확인 가능합니다.

## 📊 비용 안내

- **Google Gemini 1.5 Flash**: 무료 (분당 15 요청, 하루 1500 요청)
- **GitHub Actions**: 월 2000분 무료 (Public 리포지토리는 무제한)
- **GitHub Pages**: 무료 호스팅

→ **총 운영 비용: 0원** ✅

## ❓ FAQ

### Q: GitHub Actions가 실행되지 않아요
A:
1. Settings → Actions → General에서 "Allow all actions" 확인
2. Workflow permissions를 "Read and write permissions"으로 설정

### Q: 웹사이트가 안 열려요
A:
1. Settings → Pages에서 Source가 올바른 브랜치로 설정되었는지 확인
2. 첫 배포는 최대 5분 소요될 수 있음
3. URL이 `https://username.github.io/repo-name/` 형식인지 확인

### Q: Gemini API 에러가 발생해요
A:
1. API 키가 올바르게 설정되었는지 확인
2. [Google AI Studio](https://aistudio.google.com/)에서 API 할당량 확인
3. 무료 할당량 초과 시 다음날까지 대기

## 📝 라이선스

MIT License - 자유롭게 사용하세요!

## 🙌 기여

이슈 및 PR 환영합니다!

---

**Made with ❤️ using Google Gemini AI + GitHub**

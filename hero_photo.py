"""주요 지역 신고가 1위 '사진 카드' 만들기 (PC 실행기용, hero_photo.yml – '매일 실거래 갱신'이 끝나면 자동 실행).
- 브이월드는 해외(GitHub 서버) 접속을 막아서, 한국 IP 인 사장님 PC 에서 단지 위성 사진을 받아 카드를 다시 만듭니다.
- 사이트의 오늘 summary.json 으로 make_hero.py 를 HERO_PHOTO_ONLY=1 로 실행 → 사진을 받았을 때만
  cards/rt/<날짜>_hero.png / .jpg / .json 을 GitHub API 로 저장소에 올립니다 (git 설치 불필요).
  · 블로그 글의 1위 이미지는 이 png 주소를 그대로 쓰므로 자동으로 사진 카드로 바뀜
  · 인스타·스레드(08시)는 이 jpg 가 있으면 그걸 올림 / 카톡은 hero_kakao.py 가 보냄
- 사진을 못 받으면 아무것도 올리지 않음 → 새벽에 만든 일반 배경 카드를 그대로 씀
환경변수: GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_REF_NAME, VWORLD_KEY
"""
import os, sys, json, base64, subprocess, time, urllib.request, urllib.error

TOKEN = os.environ['GITHUB_TOKEN']
REPO = os.environ['GITHUB_REPOSITORY']
BRANCH = os.environ.get('GITHUB_REF_NAME') or 'main'
SITE = 'https://gogokimbiz-spec.github.io/sudogwon-rt/'
H = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'hero-photo'}
OUT = 'hero_out'

S = json.load(urllib.request.urlopen(f'{SITE}summary.json?t={int(time.time())}', timeout=30))
json.dump(S, open('hero_summary.json', 'w', encoding='utf-8'), ensure_ascii=False)
D = S['day']
print('오늘 요약 날짜:', D)

# 3년 거래 그래프: PC 에는 rt_data.json 이 없어서 새벽 카드(사이트 cards/hero.json)가 저장한 거래 목록을 씀
try:
    _hj = json.load(urllib.request.urlopen(f'{SITE}cards/hero.json?t={int(time.time())}', timeout=30))
    if _hj.get('day') == D and _hj.get('series'):
        json.dump(_hj['series'], open('hero_series.json', 'w', encoding='utf-8'))
except Exception as e:
    print('그래프 자료 못 받음 (저장소 hist 로 대신):', e)
env = dict(os.environ, HERO_PHOTO_ONLY='1', HERO_3D='1', HERO_SERIES='hero_series.json')
res = subprocess.run([sys.executable, 'make_hero.py', 'hero_summary.json', OUT], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
print(res.stdout); print(res.stderr)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'make_hero_log.txt'), 'w', encoding='utf-8') as f:
    f.write(res.stdout + '\n' + res.stderr)


def put(local, path):
    url = f'https://api.github.com/repos/{REPO}/contents/{path}'
    data, sha = open(local, 'rb').read(), None
    try:
        with urllib.request.urlopen(urllib.request.Request(f'{url}?ref={BRANCH}', headers=H)) as r:
            sha = json.load(r).get('sha')
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
    body = {'message': f'{path} (PC 실행기 – 1위 사진 카드)', 'branch': BRANCH, 'content': base64.b64encode(data).decode()}
    if sha: body['sha'] = sha
    with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=H, method='PUT')) as r:
        print('저장:', path, r.status)


# 3D 시험 기록 (찍힌 화면·로그) – 각도 맞추기용. 로그에서 API 키는 지움
_k = os.environ.get('VWORLD_KEY', '').strip()
_txt = ''
for _f in ('make_hero_log.txt', '3d_log.txt'):
    if os.path.exists(os.path.join(OUT, _f)):
        _txt += f'===== {_f}\n' + open(os.path.join(OUT, _f), encoding='utf-8', errors='replace').read() + '\n'
if _k: _txt = _txt.replace(_k, '***')
open(os.path.join(OUT, '3d_log.txt'), 'w', encoding='utf-8').write(_txt)
for f, dst in (('3d_debug.png', 'cards/rt/_hero3d_debug.png'), ('3d_log.txt', 'cards/rt/_hero3d_log.txt')):
    if os.path.exists(os.path.join(OUT, f)):
        try: put(os.path.join(OUT, f), dst)
        except Exception as e: print('시험 기록 저장 실패:', e)
if not os.path.exists(os.path.join(OUT, 'hero.png')):
    print('사진 카드를 만들지 않았습니다 (신고가 없음 또는 사진 실패)'); sys.exit(0)

# json 을 마지막에 올림 → json 이 있으면 png·jpg 도 이미 있다는 뜻 (카톡·인스타가 이걸 보고 판단)
put(os.path.join(OUT, 'hero.png'), f'cards/rt/{D}_hero.png')
put(os.path.join(OUT, 'hero.jpg'), f'cards/rt/{D}_hero.jpg')
put(os.path.join(OUT, 'hero.json'), f'cards/rt/{D}_hero.json')
print('1위 사진 카드 저장 완료')

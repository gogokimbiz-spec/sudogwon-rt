"""fin_data.json, fin_cache.json 을 GitHub API 로 저장소에 올립니다 (PC 실행기용, git 설치 불필요).
환경변수: GITHUB_TOKEN, GITHUB_REPOSITORY, GITHUB_REF_NAME (Actions 가 자동으로 넣어 줌)
"""
import os, sys, json, base64, datetime, urllib.request, urllib.error

TOKEN = os.environ['GITHUB_TOKEN']
REPO = os.environ['GITHUB_REPOSITORY']
BRANCH = os.environ.get('GITHUB_REF_NAME') or 'main'
H = {'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'fin-fetch'}
day = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()


def put(path):
    url = f'https://api.github.com/repos/{REPO}/contents/{path}'
    sha, old = None, None
    data = open(path, 'rb').read()
    try:
        with urllib.request.urlopen(urllib.request.Request(f'{url}?ref={BRANCH}', headers=H)) as r:
            j = json.load(r); sha = j.get('sha'); old = j.get('content')
        if old and base64.b64decode(old) == data:
            print('변경 없음:', path); return
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
    body = {'message': f'{path} {day} (PC 실행기)', 'branch': BRANCH,
            'content': base64.b64encode(data).decode()}
    if sha: body['sha'] = sha
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=H, method='PUT')
    with urllib.request.urlopen(req) as r:
        print('저장:', path, r.status)


ok = True
for p in ('fin_cache.json', 'fin_data.json', 'region_cache.json', 'region_data.json'):
    if os.path.exists(p):
        try: put(p)
        except Exception as e:
            ok = False; print('저장 실패:', p, e)
    else:
        print('파일 없음:', p); ok = ok and p != 'fin_data.json'
sys.exit(0 if ok else 1)

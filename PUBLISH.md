# PyPI 배포 가이드

## TestPyPI vs PyPI 차이점

**TestPyPI (https://test.pypi.org):**
- 테스트용 저장소 (실제 사용자들이 사용하지 않음)
- 패키지 이름이 실제 PyPI와 독립적 (같은 이름 사용 가능)
- 실수해도 문제 없음 (테스트 환경)
- 설치 시 `--index-url https://test.pypi.org/simple/` 필요

**PyPI (https://pypi.org):**
- 실제 프로덕션 저장소 (전 세계 사용자들이 사용)
- 패키지 이름이 고유해야 함 (이미 있으면 사용 불가)
- 업로드한 버전은 삭제 불가 (yank만 가능)
- 일반 `pip install`로 설치 가능

**요약:** TestPyPI는 테스트용, PyPI는 실제 배포용입니다.

## 사전 준비

1. **PyPI 계정 생성**
   - https://pypi.org/account/register/ 에서 계정 생성
   - TestPyPI도 생성: https://test.pypi.org/account/register/ (선택사항)

2. **API 토큰 생성**
   
   **PyPI 토큰:**
   - https://pypi.org/manage/account/token/ 접속
   - "Add API token" 클릭
   - Token name: `eps-estimates-collector` (또는 원하는 이름)
   - Scope: "Entire account" 또는 "Project: eps-estimates-collector" 선택
   - "Add token" 클릭
   - **생성된 토큰을 복사** (예: `pypi-AgEIcGh...` 형식, 한 번만 보여줌!)
   
   **TestPyPI 토큰:**
   - https://test.pypi.org/manage/account/token/ 접속
   - 동일한 과정 반복
   - TestPyPI는 별도 계정이 필요할 수 있음
   
   ⚠️ **주의**: 토큰은 생성 시 한 번만 표시되므로 반드시 복사해두세요!

3. **인증 설정 (두 가지 방법 중 선택)**

   **방법 A: 환경변수 사용 (권장)**
   ```bash
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-AgEIcGh...  # 생성한 토큰 전체 (pypi- 포함)
   ```

   **방법 B: ~/.pypirc 파일 사용**
   
   홈 디렉토리에 `~/.pypirc` 파일을 생성하거나 수정:
   ```ini
   [pypi]
   username = __token__
   password = pypi-AgEIcGh...  # 생성한 토큰 전체 (pypi- 포함)
   
   [testpypi]
   username = __token__
   password = pypi-AgEIcGh...  # TestPyPI 토큰 (pypi- 포함)
   ```
   
   ⚠️ **중요**: 
   - 사용자 이름은 반드시 `__token__` (언더스코어 2개씩)
   - 비밀번호는 `pypi-` 접두사를 포함한 전체 토큰 값
   - 파일 권한 설정: `chmod 600 ~/.pypirc` (보안)

4. **pyproject.toml 수정**
   - `authors` 섹션에 본인 정보 입력
   - 필요시 `keywords`, `classifiers` 수정

## 빌드 및 배포

### 방법 1: uv 사용 (권장)

#### 1. 빌드

```bash
uv build
```

이 명령은 `dist/` 디렉토리에 다음 파일들을 생성합니다:
- `eps_estimates_collector-0.2.0-py3-none-any.whl` (wheel)
- `eps_estimates_collector-0.2.0.tar.gz` (source distribution)

#### 2. TestPyPI에 배포 (선택사항, 첫 배포 시 권장)

**uv 사용:**
```bash
# 토큰을 환경변수로 설정
export UV_PUBLISH_TOKEN=pypi-xxxxxxxxxxxxx  # TestPyPI 토큰

# TestPyPI에 업로드
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

**twine 사용 (환경변수 방식):**
```bash
uv pip install twine
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxx  # TestPyPI 토큰
twine upload --repository testpypi dist/*
```

**twine 사용 (.pypirc 파일 방식):**
```bash
uv pip install twine
# ~/.pypirc 파일이 설정되어 있다면 환경변수 없이 바로 사용 가능
twine upload --repository testpypi dist/*
```

**TestPyPI에서 설치 (pip 사용 가능):**
```bash
# 방법 1: TestPyPI를 우선, PyPI를 fallback으로 사용 (권장)
pip install --extra-index-url https://test.pypi.org/simple/ eps-estimates-collector

# 방법 2: TestPyPI에서만 설치 (의존성은 PyPI에서)
pip install --index-url https://test.pypi.org/simple/ --no-deps eps-estimates-collector
pip install boto3 google-cloud-vision pandas ...  # 의존성 수동 설치
```

**참고:** 
- TestPyPI는 별도 저장소이므로, TestPyPI에 배포한 패키지는 실제 PyPI와 독립적입니다.
- `--extra-index-url`을 사용하면 TestPyPI를 먼저 확인하고, 없으면 PyPI에서 가져옵니다 (권장 방법).
- `--index-url`을 사용하면 TestPyPI만 사용하므로, 의존성도 TestPyPI에서 찾습니다 (보통 없으므로 `--no-deps` 필요).

#### 3. PyPI에 배포

```bash
# PyPI 토큰으로 변경
export UV_PUBLISH_TOKEN=pypi-xxxxxxxxxxxxx  # PyPI 토큰

# PyPI에 업로드
uv publish dist/*
```

또는 twine 사용:
```bash
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxx  # PyPI 토큰
twine upload dist/*
```

### 방법 2: 전통적인 방법 (build + twine)

#### 1. 빌드 도구 설치

```bash
uv pip install build twine
# 또는
pip install build twine
```

#### 2. 빌드

```bash
python -m build
```

#### 3. 배포

TestPyPI:
```bash
twine upload --repository testpypi dist/*
```

PyPI:
```bash
twine upload dist/*
```

### 5. 설치 확인

```bash
pip install eps-estimates-collector
python -c "from eps_estimates_collector import calculate_pe_ratio; print('Success!')"
```

## 버전 업데이트

새 버전을 배포할 때:

1. `pyproject.toml`의 `version` 업데이트
2. `src/eps_estimates_collector/__init__.py`의 `__version__` 업데이트
3. 빌드 및 배포 반복

## 주의사항

- 버전 번호는 반드시 증가해야 합니다
- TestPyPI는 선택사항이지만, 첫 배포 시 테스트를 권장합니다
- **패키지 삭제**: PyPI 웹사이트에서 패키지 설정 페이지에서 삭제 가능합니다
- **버전 삭제**: 특정 버전은 삭제할 수 없지만 yank(사용 중단) 처리 가능합니다

## 패키지 이름 변경 또는 삭제

잘못된 이름으로 올렸다면:

1. **PyPI 웹사이트에서 삭제**
   - 패키지 페이지 → Settings → Delete project
   - 또는 패키지 관리 페이지에서 삭제 가능

2. **새 패키지 이름으로 올리기**
   ```bash
   # pyproject.toml에서 이름 확인
   name = "eps-estimates-collector"  # 올바른 이름
   
   # 빌드 및 업로드
   uv build
   uv run twine upload dist/*
   ```


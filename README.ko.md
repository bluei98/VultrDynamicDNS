# VULTR Dynamic DNS Updater

VULTR API를 통해 도메인의 DNS를 자동으로 업데이트하는 Python 프로그램입니다.

## 기능

- **자동 IP 감지**: 서버의 공용 IP 주소를 자동으로 감지
- **IP 변경 모니터링**: 주기적으로 IP 변경 사항을 확인
- **자동 DNS 업데이트**: IP가 변경되면 VULTR DNS 레코드를 자동 업데이트
- **멀티 도메인 지원**: 여러 도메인 및 서브도메인 동시 관리
- **안정적인 IP 감지**: 여러 공용 IP 서비스를 통한 신뢰성 있는 IP 감지
- **로깅 지원**: 상세한 로그 기록 및 로테이션

## 설치

### 1. 요구사항

- Python 3.7 이상
- VULTR API 키

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

## 설정

### 1. 설정 파일 생성

샘플 설정 파일을 생성합니다:

```bash
python main.py init
```

### 2. 설정 파일 편집

`config.sample.json`을 `config.json`으로 복사하고 편집합니다:

```json
{
  "api_key": "YOUR_VULTR_API_KEY_HERE",
  "domains": [
    {
      "domain": "example.com",
      "subdomain": "",
      "record_type": "A",
      "ttl": 300
    },
    {
      "domain": "example.com",
      "subdomain": "blog",
      "record_type": "A",
      "ttl": 300
    }
  ],
  "check_interval": 300,
  "retry_interval": 60,
  "max_retries": 3
}
```

#### 설정 옵션

- **api_key**: VULTR API 키 (https://my.vultr.com/settings/#settingsapi 에서 발급)
- **domains**: 관리할 도메인 목록
  - **domain**: 기본 도메인 (예: example.com)
  - **subdomain**: 서브도메인 (루트 도메인의 경우 빈 문자열)
  - **record_type**: DNS 레코드 타입 (기본값: "A")
  - **ttl**: Time To Live in seconds (기본값: 300)
- **check_interval**: IP 확인 간격 (초, 기본값: 300)
- **retry_interval**: 실패 시 재시도 간격 (초, 기본값: 60)
- **max_retries**: 최대 재시도 횟수 (기본값: 3)

## 사용법

### 자동 설정 리로드 기능

프로그램은 실행 중에도 설정 파일의 변경사항을 자동으로 감지하고 적용합니다:

- **설정 파일 모니터링**: 10초마다 `config.json` 파일 변경 확인
- **자동 리로드**: 파일이 변경되면 새 설정을 자동으로 적용
- **API 키 변경 감지**: API 키가 변경되면 새 연결을 테스트 후 적용
- **도메인 목록 업데이트**: 도메인 추가/제거 시 즉시 반영
- **에러 복구**: 잘못된 설정일 경우 이전 설정으로 자동 복구

> **주의**: 설정 파일을 편집할 때는 유효한 JSON 형식을 유지하세요.

### 데몬 모드 (기본)

백그라운드에서 계속 실행되며 주기적으로 IP를 확인하고 업데이트합니다:

```bash
python main.py daemon
```

또는 단순히:

```bash
python main.py
```

### 단일 실행 모드

한 번만 확인하고 종료합니다:

```bash
python main.py once
```

강제 업데이트 (IP가 변경되지 않아도 업데이트):

```bash
python main.py once --force
```

### DNS 레코드 확인

현재 DNS 레코드를 확인합니다:

```bash
python main.py verify
```

### 로깅 옵션

로그 레벨 설정:

```bash
python main.py --log-level DEBUG daemon
```

로그 파일 저장:

```bash
python main.py --log-file logs/vultr-ddns.log daemon
```

### 사용자 정의 설정 파일

```bash
python main.py --config /path/to/custom-config.json daemon
```

## 서비스로 실행

### PM2 (권장 - Node.js Process Manager)

PM2를 사용하면 프로세스 관리, 자동 재시작, 로그 관리 등을 쉽게 할 수 있습니다.

#### PM2 설치

```bash
# npm을 통한 설치
npm install -g pm2

# 또는 yarn을 통한 설치
yarn global add pm2
```

#### PM2 로그 로테이션 설정

PM2는 기본적으로 로그를 계속 쌓기 때문에, 로그 로테이션 설정이 필요합니다:

```bash
# 로그 로테이션 자동 설정 (Linux/Mac)
./pm2-logrotate-setup.sh

# 로그 로테이션 자동 설정 (Windows)
pm2-logrotate-setup.bat

# 또는 수동 설정
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 30
pm2 set pm2-logrotate:compress true
```

#### PM2로 서비스 등록

1. PM2 설정 파일 생성 (`ecosystem.config.js`):

```javascript
module.exports = {
  apps: [{
    name: 'vultr-ddns',
    script: 'python3',
    args: 'main.py daemon',
    cwd: '/path/to/VultrDynamicDNS',
    interpreter: '/usr/bin/python3',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      PYTHONUNBUFFERED: 1
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_file: 'logs/pm2-combined.log',
    time: true
  }]
};
```

2. PM2로 서비스 시작:

```bash
# 설정 파일을 사용하여 시작
pm2 start ecosystem.config.js

# 또는 직접 실행
pm2 start main.py --name vultr-ddns --interpreter python3 -- daemon
```

3. PM2 관리 명령어:

```bash
# 서비스 상태 확인
pm2 status vultr-ddns

# 로그 확인
pm2 logs vultr-ddns

# 서비스 재시작
pm2 restart vultr-ddns

# 서비스 중지
pm2 stop vultr-ddns

# 서비스 삭제
pm2 delete vultr-ddns

# 모니터링 (실시간)
pm2 monit
```

4. 시스템 부팅 시 자동 시작 설정:

```bash
# startup 스크립트 생성
pm2 startup

# 현재 PM2 프로세스 목록 저장
pm2 save

# 저장된 프로세스 목록 복원
pm2 resurrect
```

5. PM2 웹 대시보드 (선택사항):

```bash
# PM2 Plus 모니터링 연결 (무료 플랜 가능)
pm2 link <secret_key> <public_key>

# 또는 로컬 웹 인터페이스
pm2 install pm2-web
pm2 web
```

### Linux (systemd)

1. 서비스 파일 생성:

```bash
sudo nano /etc/systemd/system/vultr-ddns.service
```

2. 다음 내용 추가:

```ini
[Unit]
Description=VULTR Dynamic DNS Updater
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/VultrDynamicDNS
ExecStart=/usr/bin/python3 /path/to/VultrDynamicDNS/main.py daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. 서비스 시작:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vultr-ddns
sudo systemctl start vultr-ddns
```

4. 상태 확인:

```bash
sudo systemctl status vultr-ddns
```

### Windows (Task Scheduler)

1. Task Scheduler 열기
2. "Create Basic Task" 선택
3. 이름과 설명 입력
4. Trigger: "When the computer starts"
5. Action: "Start a program"
6. Program: `python.exe` 경로
7. Arguments: `C:\path\to\VultrDynamicDNS\main.py daemon`
8. Start in: `C:\path\to\VultrDynamicDNS`

## 프로그램 구조

- **main.py**: 메인 엔트리 포인트
- **config.py**: 설정 관리
- **vultr_api.py**: VULTR API 클라이언트
- **ip_monitor.py**: IP 주소 모니터링
- **dns_updater.py**: DNS 업데이트 로직

## 문제 해결

### API 키 오류

- VULTR 대시보드에서 API 키가 활성화되어 있는지 확인
- API 키에 DNS 권한이 있는지 확인

### IP 감지 실패

- 인터넷 연결 확인
- 방화벽이 아웃바운드 HTTPS 연결을 차단하지 않는지 확인

### DNS 업데이트 실패

- 도메인이 VULTR DNS를 사용하는지 확인
- 도메인 설정이 올바른지 확인

## 라이선스

MIT License
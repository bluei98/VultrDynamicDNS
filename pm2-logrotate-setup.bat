@echo off
echo PM2 로그 로테이션 설정 스크립트
echo ================================

REM PM2 logrotate 모듈 설치
echo 1. PM2 logrotate 모듈 설치 중...
pm2 install pm2-logrotate

REM 로그 로테이션 설정
echo 2. 로그 로테이션 설정 중...

REM 최대 파일 크기 설정 (10MB)
pm2 set pm2-logrotate:max_size 10M

REM 보관할 로그 파일 개수 (30개 = 30일치)
pm2 set pm2-logrotate:retain 30

REM 로그 압축 활성화
pm2 set pm2-logrotate:compress true

REM 로테이션 간격 (매일 자정)
pm2 set pm2-logrotate:rotateInterval "0 0 * * *"

REM 날짜 형식 설정
pm2 set pm2-logrotate:dateFormat YYYY-MM-DD

REM 워커 체크 간격 (30초)
pm2 set pm2-logrotate:workerInterval 30

REM 로테이션할 로그 경로 패턴
pm2 set pm2-logrotate:retain_path_pattern true

echo 3. 설정 완료!
echo.
echo 현재 설정:
pm2 conf pm2-logrotate

echo.
echo PM2 재시작 중...
pm2 restart all

echo.
echo 로그 로테이션 설정이 완료되었습니다!
echo - 최대 파일 크기: 10MB
echo - 보관 기간: 30일
echo - 압축: 활성화
echo - 로테이션 주기: 매일 자정
pause
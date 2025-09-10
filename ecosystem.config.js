module.exports = {
  apps: [{
    name: 'vultr-ddns',
    script: 'main.py',
    interpreter: 'python3',
    interpreter_args: '',
    args: 'daemon',
    cwd: __dirname,
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    min_uptime: '10s',
    max_restarts: 10,
    env: {
      PYTHONUNBUFFERED: 1
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_file: 'logs/pm2-combined.log',
    time: true,
    merge_logs: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    // 로그 로테이션 설정
    log_rotate_options: {
      max_size: '10M',           // 파일당 최대 크기 10MB
      retain: 30,                // 최대 30개 파일 보관 (30일치)
      compress: true,            // 오래된 로그 압축
      dateFormat: 'YYYY-MM-DD',  // 로그 파일 날짜 형식
      workerInterval: 30,        // 로테이션 체크 간격 (초)
      rotateInterval: '0 0 * * *' // 매일 자정에 로테이션 (cron 형식)
    }
  }]
};
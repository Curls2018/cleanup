@echo off
setlocal

set BACKUP=D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup
set TASKNAME=DeleteSogouBackup

echo [1] 终止搜狗进程...
taskkill /F /IM SogouCloud.exe /IM SogouPY.exe /IM SogouPYIme.exe 2>nul

echo [2] 创建 SYSTEM 计划任务（直接执行命令）...
schtasks /create /sc once /tn "%TASKNAME%" /tr "cmd /c rd /s /q %BACKUP%" /ru "SYSTEM" /st 00:00 /f

echo [3] 立即运行...
schtasks /run /tn "%TASKNAME%"

echo [4] 等待执行完成...
timeout /t 5 /nobreak >nul

echo [5] 检查结果...
if exist "%BACKUP%" (
    echo 失败：目录仍存在
) else (
    echo 成功：目录已删除
)

echo [6] 清理计划任务...
schtasks /delete /tn "%TASKNAME%" /f >nul 2>nul

pause
endlocal

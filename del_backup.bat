@echo off
setlocal

set BACKUP=D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup
set BATFILE=C:\Windows\Temp\_del_backup_sys.bat
set TASKNAME=DeleteSogouBackup

echo [1] 终止搜狗进程...
taskkill /F /IM SogouCloud.exe /IM SogouPY.exe /IM SogouPYIme.exe 2>nul

echo [2] 写入删除脚本...
echo @echo off > "%BATFILE%"
echo rd /s /q "%BACKUP%" >> "%BATFILE%"

echo [3] 创建 SYSTEM 计划任务并立即执行...
schtasks /create /sc once /tn "%TASKNAME%" /tr "%BATFILE%" /ru "SYSTEM" /st 00:00 /f
schtasks /run /tn "%TASKNAME%"

echo [4] 等待执行完成...
timeout /t 5 /nobreak >nul

echo [5] 检查结果...
if exist "%BACKUP%" (
    echo 失败：目录仍存在
) else (
    echo 成功：目录已删除
)

echo [6] 清理任务和临时文件...
schtasks /delete /tn "%TASKNAME%" /f >nul 2>nul
del "%BATFILE%" >nul 2>nul

pause
endlocal

import ctypes
import ctypes.wintypes as wintypes
import os
import glob
import sys
import subprocess


# ── Shell API 结构体（备用方案） ─────────────────────────────────────────────
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd",                  wintypes.HWND),
        ("wFunc",                 wintypes.UINT),
        ("pFrom",                 wintypes.LPCWSTR),
        ("pTo",                   wintypes.LPCWSTR),
        ("fFlags",                wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings",         ctypes.c_void_p),
        ("lpszProgressTitle",     wintypes.LPCWSTR),
    ]

FO_DELETE          = 3
FOF_ALLOWUNDO      = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT         = 0x0004
FOF_NOERRORUI      = 0x0400


def kill_sogou():
    """强制终止搜狗输入法进程，释放文件句柄"""
    procs = ["SogouPY.exe", "SogouPYIme.exe", "SogouCloud.exe",
             "PinyinUp.exe", "SGTool.exe"]
    killed = []
    for p in procs:
        r = subprocess.call(
            ["taskkill", "/F", "/IM", p],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if r == 0:
            killed.append(p)
    return killed


def delete_as_system(path):
    """用 PsExec 以 SYSTEM 身份执行 rd /s /q，绕过所有用户态锁"""
    # 在 exe 同级目录、PATH、C:\Windows\System32 中查找 PsExec
    candidates = [
        os.path.join(os.path.dirname(sys.executable), "PsExec.exe"),
        os.path.join(os.path.dirname(sys.executable), "psexec.exe"),
        r"C:\Windows\System32\PsExec.exe",
        "PsExec.exe",   # PATH
    ]
    psexec = next((p for p in candidates if os.path.isfile(p)), None)
    if not psexec:
        # 尝试 PATH 里有没有
        psexec = "PsExec.exe"

    cmd = [psexec, "-accepteula", "-s", "-i",
           "cmd", "/c", 'rd /s /q "%s"' % path]
    print("      执行: %s" % " ".join(cmd))
    r = subprocess.call(cmd)
    return r


def delete_files(pattern):
    """删除匹配 glob 的文件"""
    deleted = 0
    for f in glob.glob(pattern):
        if os.path.isfile(f):
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                print("  跳过: %s -> %s" % (f, e))
    return deleted


if __name__ == "__main__":
    try:
        # ── 步骤 1：删除 SocketTest 文件 ──────────────────────────────────
        SOCKETTEST = r"D:\SocketTest\*.*"
        print("[1/3] 删除 %s ..." % SOCKETTEST)
        n = delete_files(SOCKETTEST)
        print("      已删除 %d 个文件" % n)

        # ── 步骤 2：删除 SogouPY Backup ───────────────────────────────────
        BACKUP = r"D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup"
        print("[2/3] 删除目录: %s" % BACKUP)

        if not os.path.exists(BACKUP):
            print("      目录不存在，跳过")
        else:
            # 先杀搜狗进程
            killed = kill_sogou()
            if killed:
                print("      已终止进程: %s" % ", ".join(killed))
            else:
                print("      未检测到搜狗进程（或已关闭）")

            # 用 PsExec SYSTEM 权限删除
            print("      以 SYSTEM 权限执行 rd /s /q ...")
            ret = delete_as_system(BACKUP)
            if ret == 0 and not os.path.exists(BACKUP):
                print("      成功：目录已删除")
            else:
                print("      PsExec 返回码: %d，目录是否仍存在: %s"
                      % (ret, os.path.exists(BACKUP)))

        # ── 步骤 3：清空回收站 ────────────────────────────────────────────
        print("[3/3] 清空回收站 ...")
        SHERB = 0x00000001 | 0x00000002 | 0x00000004
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB)
        print("      SHEmptyRecycleBin 返回: 0x%X" % (ret & 0xFFFFFFFF))

        print("\n全部完成。")

    except Exception:
        import traceback
        print("\n[异常]\n" + traceback.format_exc())

    finally:
        os.system("pause")

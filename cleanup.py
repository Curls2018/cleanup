import ctypes
import ctypes.wintypes as wintypes
import os
import glob
import sys
import subprocess

MOVEFILE_DELAY_UNTIL_REBOOT = 0x00000004


def kill_sogou():
    """强制终止搜狗输入法用户态进程"""
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


def try_rd_as_system(path):
    """先尝试 PsExec SYSTEM 直接删（快速路径，对用户态锁有效）"""
    if getattr(sys, 'frozen', False):
        psexec = os.path.join(sys._MEIPASS, "PsExec.exe")
    else:
        psexec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PsExec.exe")

    if not os.path.isfile(psexec):
        return False

    bat = r"C:\Windows\Temp\_cleanup_system.bat"
    with open(bat, "w") as f:
        f.write("@echo off\n")
        f.write('rd /s /q "%s"\n' % path)
    try:
        r = subprocess.call(
            [psexec, "-accepteula", "-s", bat],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return r == 0 and not os.path.exists(path)
    finally:
        try:
            os.remove(bat)
        except Exception:
            pass


def schedule_delete_on_reboot(path):
    """将单个文件或目录注册到 PendingFileRenameOperations，下次开机前删除"""
    ret = ctypes.windll.kernel32.MoveFileExW(path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
    if ret:
        return True, 0
    return False, ctypes.windll.kernel32.GetLastError()


def schedule_tree_delete_on_reboot(root):
    """递归将整个目录树注册为开机删除（底层到顶层顺序）"""
    success, fail, errors = 0, 0, []

    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            ok, err = schedule_delete_on_reboot(fpath)
            if ok:
                success += 1
            else:
                fail += 1
                errors.append("    文件注册失败 0x%X: %s" % (err, fpath))

        ok, err = schedule_delete_on_reboot(dirpath)
        if ok:
            success += 1
        else:
            fail += 1
            errors.append("    目录注册失败 0x%X: %s" % (err, dirpath))

    # 注册根目录本身
    ok, err = schedule_delete_on_reboot(root)
    if ok:
        success += 1
    else:
        fail += 1
        errors.append("    根目录注册失败 0x%X: %s" % (err, root))

    return success, fail, errors


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
    need_reboot = False
    try:
        # ── 步骤 1：删除 SocketTest 文件 ──────────────────────────────────
        SOCKETTEST = r"D:\SocketTest\*.*"
        print("[1/3] 删除 %s ..." % SOCKETTEST)
        n = delete_files(SOCKETTEST)
        print("      已删除 %d 个文件" % n)

        # ── 步骤 2：删除 SogouPY Backup ───────────────────────────────────
        BACKUP = r"D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup"
        print("[2/3] 处理目录: %s" % BACKUP)

        if not os.path.exists(BACKUP):
            print("      目录不存在，跳过")
        else:
            # 先终止搜狗用户态进程
            killed = kill_sogou()
            if killed:
                print("      已终止进程: %s" % ", ".join(killed))

            # 快速路径：PsExec SYSTEM 直接删（对用户态锁有效）
            print("      尝试直接删除 ...")
            if try_rd_as_system(BACKUP):
                print("      成功：目录已删除")
            else:
                # 内核态锁：注册开机删除（正确解法）
                print("      直接删除失败（内核驱动持有句柄），注册开机删除 ...")
                ok, fail, errors = schedule_tree_delete_on_reboot(BACKUP)
                print("      已注册 %d 项，失败 %d 项" % (ok, fail))
                for e in errors:
                    print(e)
                if ok > 0 and fail == 0:
                    need_reboot = True
                    print("      下次重启时将自动删除（重启前目录仍存在属正常）")

        # ── 步骤 3：清空回收站 ────────────────────────────────────────────
        print("[3/3] 清空回收站 ...")
        SHERB = 0x00000001 | 0x00000002 | 0x00000004
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB)
        if ret == 0:
            print("      回收站已清空")
        else:
            print("      回收站返回 0x%X（可能已为空）" % (ret & 0xFFFFFFFF))

        if need_reboot:
            print("\n>>> 请重启计算机，重启后 Backup 目录将被自动删除 <<<")
        else:
            print("\n全部完成。")

    except Exception:
        import traceback
        print("\n[异常]\n" + traceback.format_exc())

    finally:
        os.system("pause")

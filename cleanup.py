import ctypes
import ctypes.wintypes as wintypes
import os
import glob
import sys
import subprocess


# ── SHFileOperationW 结构体 ────────────────────────────────────────────────
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
FOF_ALLOWUNDO      = 0x0040   # 发送到回收站
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT         = 0x0004
FOF_NOERRORUI      = 0x0400

MOVEFILE_DELAY_UNTIL_REBOOT = 0x00000004


def send_file_to_recycle(filepath):
    """将单个文件发送到回收站，返回是否成功"""
    op = SHFILEOPSTRUCTW()
    op.wFunc  = FO_DELETE
    op.pFrom  = filepath + '\0'
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return ret == 0


def schedule_delete_on_reboot(path):
    """将文件注册为开机删除（用于无法移入回收站的锁定文件）"""
    ret = ctypes.windll.kernel32.MoveFileExW(path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
    return ret != 0


def recycle_tree(root):
    """
    逐文件将目录树移入回收站：
    - 可删的文件 → 回收站
    - 锁定的文件 → 注册开机删除
    - 清空后的目录 → os.rmdir 直接删
    """
    recycled, scheduled, failed = 0, 0, []

    # 自底向上遍历：先处理文件，再处理目录
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if send_file_to_recycle(fpath):
                recycled += 1
            else:
                failed.append(fpath)
                print("      跳过(锁定): %s" % fpath)

        # 文件处理完后尝试删除目录（如果已空）
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
            except Exception:
                pass

    # 最后尝试根目录
    if os.path.exists(root) and not os.listdir(root):
        try:
            os.rmdir(root)
        except Exception:
            pass

    return recycled, scheduled, failed


def kill_sogou():
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


def delete_files(pattern):
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

        # ── 步骤 2：逐文件移入回收站 ──────────────────────────────────────
        BACKUP = r"D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup"
        print("[2/3] 处理目录: %s" % BACKUP)

        if not os.path.exists(BACKUP):
            print("      目录不存在，跳过")
        else:
            killed = kill_sogou()
            if killed:
                print("      已终止进程: %s" % ", ".join(killed))

            # 诊断：打印目录树结构
            print("      [诊断] 目录内容:")
            total_diag = 0
            for dp, dns, fns in os.walk(BACKUP, topdown=True):
                level = dp.replace(BACKUP, '').count(os.sep)
                indent = '  ' * (level + 4)
                print("%s%s\\" % (indent, os.path.basename(dp)))
                for fn in fns:
                    print("%s  %s" % (indent, fn))
                    total_diag += 1
            print("      [诊断] os.walk 共发现 %d 个文件" % total_diag)
            # 用 dir /a /s 列出所有文件（包括隐藏/系统）
            print("      [诊断] dir /a /s 输出:")
            subprocess.call(
                'dir /a /s "%s"' % BACKUP,
                shell=True
            )

            recycled, scheduled, failed = recycle_tree(BACKUP)
            print("      已移入回收站: %d 个文件" % recycled)
            if failed:
                print("      已跳过(锁定): %d 个文件" % len(failed))

            if os.path.exists(BACKUP):
                print("      目录仍存在（含锁定文件已跳过）")
            else:
                print("      目录已完全删除")

        # ── 步骤 3：清空回收站 ────────────────────────────────────────────
        print("[3/3] 清空回收站 ...")
        SHERB = 0x00000001 | 0x00000002 | 0x00000004
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB)
        if ret == 0:
            print("      回收站已清空")
        else:
            print("      回收站返回 0x%X（可能已为空）" % (ret & 0xFFFFFFFF))

        print("\n全部完成。")

    except Exception:
        import traceback
        print("\n[异常]\n" + traceback.format_exc())

    finally:
        os.system("pause")

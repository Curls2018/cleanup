import ctypes
import ctypes.wintypes as wintypes
import os
import glob
import sys


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd",                 wintypes.HWND),
        ("wFunc",                wintypes.UINT),
        ("pFrom",                wintypes.LPCWSTR),
        ("pTo",                  wintypes.LPCWSTR),
        ("fFlags",               wintypes.WORD),
        ("fAnyOperationsAborted",wintypes.BOOL),
        ("hNameMappings",        ctypes.c_void_p),
        ("lpszProgressTitle",    wintypes.LPCWSTR),
    ]


FO_DELETE        = 3
FOF_ALLOWUNDO    = 0x0040   # 发送到回收站而非直接删除
FOF_NOCONFIRMATION = 0x0010 # 不弹确认框
FOF_SILENT       = 0x0004   # 不显示进度
FOF_NOERRORUI    = 0x0400   # 不显示错误框


def send_to_recycle(path):
    """调用 SHFileOperationW 将路径发送到回收站（与 Explorer 删除完全一致）"""
    # SHFileOperation 要求路径以双 null 结尾，c_wchar_p 自动加一个，再手动加一个
    op = SHFILEOPSTRUCTW()
    op.wFunc  = FO_DELETE
    op.pFrom  = path + '\0'
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return ret


def empty_recycle_bin():
    """调用 SHEmptyRecycleBinW 清空回收站（兼容 WinXP+）"""
    SHERB_NOCONFIRMATION = 0x00000001
    SHERB_NOPROGRESSUI   = 0x00000002
    SHERB_NOSOUND        = 0x00000004
    flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
    return ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)


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
    # ── 步骤 1：删除 SocketTest 文件 ──────────────────────────────────
    SOCKETTEST = r"D:\SocketTest\*.*"
    print("[1/3] 删除 %s ..." % SOCKETTEST)
    n = delete_files(SOCKETTEST)
    print("      已删除 %d 个文件" % n)

    # ── 步骤 2：将 SogouPY Backup 发送到回收站 ─────────────────────────
    BACKUP = r"D:\sangforupm\Users\Administrator\AppData\LocalLow\SogouPY\Backup"
    print("[2/3] 发送到回收站: %s" % BACKUP)
    if not os.path.exists(BACKUP):
        print("      目录不存在，跳过")
    else:
        ret = send_to_recycle(BACKUP)
        if ret == 0:
            print("      成功发送到回收站")
        else:
            print("      失败，错误码: %d" % ret)
            sys.exit(1)

    # ── 步骤 3：清空回收站 ────────────────────────────────────────────
    print("[3/3] 清空回收站 ...")
    ret = empty_recycle_bin()
    if ret == 0:
        print("      回收站已清空")
    else:
        print("      注意: SHEmptyRecycleBin 返回 %d" % ret)

    print("\n全部完成。")
    os.system("pause")

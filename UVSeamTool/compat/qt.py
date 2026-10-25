"""
PySide6 / PySide2 の違い。

ほかのモジュールは PySide / shiboken を直接 import せず、ここの `QtCore` / `QtGui` / `QtWidgets` / `wrap_instance` を使う。
Maya 2025 からは PySide6、2022〜2024 は PySide2。
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import getCppPointer, wrapInstance
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import getCppPointer, wrapInstance


def wrap_instance(pointer, qt_class):
    """Maya が返すウィジェットのポインタ (数) -> Qt のオブジェクト。"""
    return wrapInstance(int(pointer), qt_class)


def pointer_of(qt_object):
    """Qt のオブジェクトの C++ のポインタ (数)。同じウィジェットかどうかは、これで比べる。"""
    return int(getCppPointer(qt_object)[0])

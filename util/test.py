import tkinter as tk
from tkinter import ttk


def _empty_callback(row_id, col_name, old_value, new_value):
    """默认空回调函数，返回成功"""
    return True


class EditableTreeview(ttk.Treeview):
    """
    扩展 Treeview，实现双击编辑单元格（支持 Enter 保存、Esc 取消、失焦保存），
    并支持外部回调失败时自动回滚原值。
    """

    def __init__(self, master=None, editable_columns=None, on_edit_done=None, **kw):
        """
        :param on_edit_done:
            回调函数：on_edit_done(row_id, col_name, old_value, new_value) -> bool
            返回 True：更新成功
            返回 False：更新失败，Treeview 自动回滚 old_value
        """
        super().__init__(master, **kw)

        self._editor = None
        self._all_columns = list(self["columns"])

        # 过滤出 Treeview 实际存在的列
        if editable_columns:
            self.editable_columns = [
                col for col in editable_columns if col in self._all_columns
            ]
        else:
            self.editable_columns = []

        self._on_edit_done = on_edit_done or _empty_callback

        # 绑定双击事件
        self.bind("<Double-1>", self._start_edit)

    # ----------------------------------------------------------
    # 进入编辑
    # ----------------------------------------------------------
    def _start_edit(self, event):
        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)

        if not row_id or col_id == "#0":
            return

        col_index = int(col_id[1:]) - 1
        col_name = self._all_columns[col_index]

        # 不可编辑列跳过
        if col_name not in self.editable_columns:
            return

        old_value = self.set(row_id, col_name)

        # 获取单元格位置
        bbox = self.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox

        # 若已有编辑器，销毁
        if self._editor:
            self._editor.destroy()

        # 创建编辑框
        editor = tk.Entry(self)
        editor.place(x=x, y=y, width=w, height=h)
        editor.insert(0, old_value)
        editor.focus()

        # 保存编辑状态
        self._editor = editor
        self._edit_row_id = row_id
        self._edit_col_name = col_name
        self._edit_old_value = old_value

        # 绑定事件
        editor.bind("<Return>", self._save_edit)
        editor.bind("<Escape>", self._cancel_edit)
        editor.bind("<FocusOut>", self._save_edit)

    # ----------------------------------------------------------
    # 保存编辑
    # ----------------------------------------------------------
    def _save_edit(self, event=None):
        if not self._editor:
            return

        new_value = self._editor.get()
        row_id = self._edit_row_id
        col_name = self._edit_col_name
        old_value = self._edit_old_value

        # 销毁编辑器
        self._editor.destroy()
        self._editor = None

        # 值未变，不触发回调
        if new_value == old_value:
            return

        # 调用外部回调（可能失败）
        success = True
        if callable(self._on_edit_done):
            try:
                success = self._on_edit_done(row_id, col_name, old_value, new_value)
            except:
                success = False

        # DB 更新成功 → 写入新值
        if success:
            self.set(row_id, col_name, new_value)
        else:
            # ❗失败 → 回滚 UI
            self.set(row_id, col_name, old_value)

    # ----------------------------------------------------------
    # Esc 取消编辑
    # ----------------------------------------------------------
    def _cancel_edit(self, event=None):
        if not self._editor:
            return
        self._editor.destroy()
        self._editor = None

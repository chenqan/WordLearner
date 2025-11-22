import tkinter as tk
from tkinter import ttk


def _empty_callback(row_id, col_name, new_value):
    """默认空回调函数，返回成功"""
    return True

class EditableTreeview(ttk.Treeview):
    """
    扩展 Treeview，实现双击编辑单元格（支持 Enter 保存、Esc 取消、保存后触发回调）。
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
        print(self.editable_columns)
        print(on_edit_done)
        self._on_edit_done = on_edit_done or _empty_callback

        # 绑定双击事件
        self.bind("<Double-1>", self._start_edit)

    def _start_edit(self, event):
        """双击进入编辑模式：创建 Entry 覆盖到单元格位置"""
        # 点击到哪一行哪一列
        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)

        if not row_id or col_id == "#0":
            return

        # Treeview 的 column 名
        col_index = int(col_id[1:]) - 1
        col_name = self._all_columns[col_index]

        # ⛔ 不可编辑列直接返回
        if col_name not in self.editable_columns:
            return

        # 单元格原始值
        old_value = self.set(row_id, col_name)

        # 单元格位置
        x, y, w, h = self.bbox(row_id, col_name)

        # 若已有 editor，从安全角度销毁一次
        if self._editor:
            self._editor.destroy()

        # 创建 Entry
        editor = tk.Entry(self)
        editor.place(x=x, y=y, width=w, height=h)
        editor.insert(0, old_value) # pyright: ignore[reportArgumentType]
        editor.focus()

        # 保存必要信息
        self._editor = editor
        self._edit_row_id = row_id
        self._edit_col_name = col_name
        self._edit_old_value = old_value

        # 绑定事件：Enter = 保存，Esc = 取消，FocusOut = 自动完成保存
        editor.bind("<Return>", self._save_edit)
        editor.bind("<Escape>", self._cancel_edit)
        editor.bind("<FocusOut>", self._save_edit)

    def _save_edit(self, event=None):
        """保存编辑（Enter 或失焦）"""
        print("保存编辑")
        if not self._editor:
            return
        print("保存编辑2")
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
                success = self._on_edit_done(row_id, col_name, new_value) # pyright: ignore[reportCallIssue]
            except Exception as e:
                print("EditableTreeview: on_edit_done 回调异常", e)
                success = False
        print(f"编辑结果: {success}")

        # DB 更新成功 → 写入新值
        if success:
            self.set(row_id, col_name, new_value)
        else:
            # ❗失败 → 回滚 UI
            self.set(row_id, col_name, old_value)

    def _cancel_edit(self, event=None):
        """Esc 取消编辑（不保存）"""
        if not self._editor:
            return
        self._editor.destroy()
        self._editor = None

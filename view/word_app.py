import copy
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from service.file_service import FileService
from service.word_service import WordService, WordDisplay
from util.editable_treeview import EditableTreeview

PAGE_SIZE = 30

class WordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("单词学习助手 (ORM)")
        self.current_file_id = None
        self.current_page = 0
        self.words_cache = {} # {iid: WordDisplay}
        # service层（全部为静态类）
        self.file_service = FileService
        self.word_service = WordService

        # 初始化界面
        self.setup_ui()
        self.load_file_list()

    # ------------------- UI 初始化 -------------------
    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # 顶部区域
        top_frame = ttk.Frame(frame)
        top_frame.pack(pady=5, fill="x")

        ttk.Button(top_frame, text="导入文件", command=self.import_file).pack(side="left", padx=5)
        ttk.Label(top_frame, text="选择文件:").pack(side="left", padx=5)

        self.file_combo = ttk.Combobox(top_frame, state="readonly")
        self.file_combo.pack(side="left", padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", self.on_file_selected)

        ttk.Button(top_frame, text="上一页", command=self.prev_page).pack(side="left", padx=5)
        self.page_label = ttk.Label(top_frame, text="第 1 / 1 页")
        self.page_label.pack(side="left", padx=5)
        ttk.Button(top_frame, text="下一页", command=self.next_page).pack(side="left", padx=5)
        ttk.Button(top_frame, text="显示全部已学会", command=self.show_all_learned).pack(side="left", padx=5)

        # 进度条
        self.progress = ttk.Progressbar(frame, length=400, mode="determinate")
        self.progress.pack(pady=5)

        # 表格显示
        columns = ("word", "trans", "ipa", "sound", "status", "learned")
        editable_cols = ("word", "trans", "ipa")
        self.tree = EditableTreeview(
                        frame,
                        columns=columns,
                        editable_columns=editable_cols,
                        show="headings",
                        height=20,
                        on_edit_done=self.on_cell_edited  # 绑定回调
                    )
        self.tree.pack(fill="both", expand=True)
        for col, text, width in zip(columns,
                                    ["单词/短语", "中文翻译", "音标", "🔊播放", "状态", "结果"],
                                    [200, 250, 150, 80, 100, 100]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")

        # 事件绑定
        self.tree.bind("<ButtonRelease-1>", self.on_click)
        self.root.bind("<space>", self.on_space_key)
        self.root.bind("<Key-1>", self.on_key_1)
        self.root.bind("<Key-2>", self.on_key_2)
        self.root.bind("<Left>", self.on_space_key)
        self.root.bind("<Right>", self.on_key_1)

    # ------------------- 文件导入 -------------------
    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("TSV文件", "*.tsv"),
            ("TXT文件", "*.txt"),
            ("所有文件", "*.*")
        ])
        if not path:
            return
        threading.Thread(target=self._import_file_thread, args=(path,), daemon=True).start()

    def _import_file_thread(self, path):
        try:
            for idx, total in self.file_service.import_file(path):
                self.root.after(0, lambda i=idx, t=total: self.progress.config(value=i, maximum=t))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("导入失败", str(e)))
        else:
            self.root.after(0, self._on_import_finished)

    def _on_import_finished(self):
        self.load_file_list()
        self.progress.config(value=0)
        messagebox.showinfo("完成", "文件导入完成！")

    # ------------------- 文件列表 -------------------
    def load_file_list(self):
        self.file_combo["values"] = self.file_service.list_files()

    def on_file_selected(self, event):
        filename = self.file_combo.get()
        file_id = self.file_service.get_file_id(filename)
        if file_id:
            self.current_file_id = file_id
            self.current_page = 0
            self.refresh_table()

    # ------------------- 分页 -------------------
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not self.current_file_id:
            return

        offset = self.current_page * PAGE_SIZE
        self.words_cache = self.word_service.get_displays_by_page(self.current_file_id, PAGE_SIZE, offset)

        for display in self.words_cache.values():
            self.upsert_word_display(display, False)

        total = self.word_service.count_displays(self.current_file_id)
        total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
        self.page_label.config(text=f"第 {self.current_page + 1} / {total_pages} 页")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        total = self.word_service.count_displays(self.current_file_id)
        total_pages = max((total - 1) // PAGE_SIZE + 1, 1)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh_table()

    # ------------------- 点击事件 -------------------
    def on_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        display = self.words_cache.get(item)
        if not display:
            return

        if col == "#4" and display.gtts:
            # 播放音频
            display.audio.play()
        elif col == "#5":
            self.upsert_word_display(display)
        elif col == "#6":
            new_display = self.word_service.toggle_unlearned(display)
            self.words_cache[item] = new_display
            self.upsert_word_display(new_display, False)

    # ------------------- 键盘事件 -------------------
    def on_key_1(self, event):
        """按 1 键切换显示/隐藏"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        d = self.words_cache.get(iid)
        if d:
            self.upsert_word_display(d)
    
    def on_key_2(self, event):
        """按 1 键切换显示/隐藏"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        d = self.words_cache.get(iid)
        if d:
            new_display = self.word_service.toggle_unlearned(d)
            self.words_cache[iid] = new_display
            self.upsert_word_display(new_display, False)

    def on_space_key(self, event):
        """按空格播放当前选中行的语音"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        display = self.words_cache.get(iid)
        if display and display.gtts:
            display.audio.play()

    # ------------------- 状态切换 -------------------
    def upsert_word_display(self, display: WordDisplay, toggle_status=True):
        """
        控制单词显示/隐藏状态，并更新 TreeView 视图。

        :param display: WordDisplay 对象，包含单词的显示数据
        :param is_insert: 是否是新插入的数据（导入时使用）
        :param switch: 是否触发显示状态切换
        """

        def show_word(d: WordDisplay):
            """显示单词详细信息"""
            return (d.word, d.trans, d.ipa, "播放", "隐藏", d.is_unlearned)

        def hide_word(d: WordDisplay):
            """隐藏单词详细信息"""
            return ("", "", "", "播放", "显示", d.is_unlearned)

        # 如果是导入时插入且该单词未学习，则插入一行
        if not self.tree.exists(display.iid):
             # 初始显示状态根据 is_unlearned 决定
            init_values = hide_word(display) if display.is_unlearned else show_word(display)
            self.tree.insert("", "end", iid=display.iid, values=init_values)
            return
        
        if toggle_status:
            # 读取当前行的显示状态
            current = self.tree.item(display.iid, "values")
            is_hidden = current and current[0] == ""
            # 普通点击：切换显示 / 隐藏
            new_values = show_word(display) if is_hidden else hide_word(display)
        else:
            new_values = hide_word(display) if display.is_unlearned else show_word(display)

        self.tree.item(display.iid, values=new_values)

    def show_all_learned(self):
        """恢复所有为可见状态"""
        for iid, display in self.words_cache.items():
            self.tree.item(iid, values=(display.word, display.trans, display.ipa, "播放", "隐藏", display.is_unlearned))

    def on_cell_edited(self, row_id, col_name, new_value):
        """
        单元格编辑完成后的回调
        """
        print(f"[INFO] 单元格编辑完成: row_id={row_id}, col_name={col_name}, new_value={new_value}")

        wd_original = self.words_cache.get(row_id)
        if not wd_original:
            return False
        
        old_value = getattr(wd_original, col_name)
        if old_value == new_value:
            return True  # 值未改变，不做任何操作

        # --- 创建副本 ---
        wd_copy = copy.deepcopy(wd_original)
        setattr(wd_copy, col_name, new_value)

        print(f"[INFO] 尝试更新 row_id={row_id}, col={col_name} 从 '{old_value}' -> '{new_value}'")

        # 调用统一的数据库更新方法
        try:
            new_display = WordService.update_display(wd_copy, col_name)
        except Exception as e:
            print(f"[ERROR] 更新失败: {e}")
            self._show_update_failed(col_name)
            return False

        if new_display:
            # 更新缓存
            self.words_cache[row_id] = new_display
            return True
        else:
            self._show_update_failed(col_name)
            return False
        

        # # 刷新 UI，例如重绘状态栏/某个统计区域
        # self.refresh_some_ui_if_needed()


    def _show_update_failed(self, col_name):
        """失败提示（避免重复写 messagebox）"""
        try:
            messagebox.showerror("更新失败", f"无法更新字段 {col_name}，请重试。")
        except Exception:
            pass

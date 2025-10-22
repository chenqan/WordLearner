"""
Tkinter UI front-end that uses orm_models.py for database operations.
This file provides a WordApp class similar to your original app but using SQLAlchemy ORM.

Requirements:
  pip install sqlalchemy pydub gTTS simpleaudio

Note:
  - token2voice() is a helper that attempts to generate TTS bytes via gTTS.
  - play_voice() will try to play mp3 bytes using pydub + simpleaudio. If those
    packages are not available in your environment, replace implementations with
    your preferred audio playback method.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from io import BytesIO

import numpy as np
import time

from model.orm_models import Session, File, Word, Display, DB_FILE

# Optional: TTS and audio playback helpers
try:
    from gtts import gTTS, gTTSError
except Exception:
    gTTS = None

try:
    from pydub import AudioSegment
    import sounddevice as sd
except Exception:
    AudioSegment = None



PAGE_SIZE = 30


def token2voice(text, retries=3, base_sleep=1) -> bytes:
    """Return mp3 bytes for the given text using gTTS if available.
    If gTTS isn't available or fails, return None.
    """
    if gTTS is None:
        return None
    mp3_io = BytesIO()
    for attempt in range(1, retries + 1):
        try:
            tts = gTTS(text=text.strip(), lang='en', tld='co.uk')
            for decoded in tts.stream():
                mp3_io.write(decoded)
            mp3_io.flush()
            return mp3_io.getvalue()
        except gTTSError as e:
            if attempt < retries:
                time.sleep(base_sleep * (2 ** (attempt - 1)))
            else:
                print(f"token2voice error: {e}")
                return None

def play_voice(mp3_bytes:bytes, format="mp3", is_wait=False):
    """Play mp3 bytes. Use pydub if available, otherwise write to temp file and
    try to open with default system player as a fallback.
    """
    if not mp3_bytes:
        return
    
    audio = AudioSegment.from_file(BytesIO(mp3_bytes), format=format)
    samples = np.array(audio.get_array_of_samples())
    if audio.channels == 2:
        samples = samples.reshape((-1,2))
    samples = samples / 2**15
    sd.play(samples, samplerate=audio.frame_rate)
    if is_wait:
        sd.wait()

class AudioPlayer:

    """Play mp3 bytes. Use pydub if available, otherwise write to temp file and
    try to open with default system player as a fallback.
    """

    def __init__(self, mp3_bytes:bytes, format="mp3"):
        
        if not mp3_bytes:
            return
    
        audio = AudioSegment.from_file(BytesIO(mp3_bytes), format=format)
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            samples = samples.reshape((-1,2))
        self.postproc_samples = samples / 2**15
        self.frame_rate = audio.frame_rate

    def play(self, is_wait=False):

        sd.play(self.postproc_samples, samplerate=self.frame_rate)
        if is_wait:
            sd.wait()

class WordDisplay:

    def __init__(self, display: Display):
        self.id = display.id
        self.iid = display.iid
        self.word_id = display.word_id
        self.file_id = display.file_id
        self.word = display.word_ref.word
        self.trans = display.word_ref.trans
        self.ipa = display.word_ref.ipa
        self.gtts = display.word_ref.gtts
        self.is_unlearned = display.word_ref.is_unlearned
        self.audio = AudioPlayer(self.gtts)


class WordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("单词学习助手 (ORM)")
        self.current_file_id = None
        self.current_page = 0
        self.words_cache = {}  # {iid: (iid, word_id, word, trans, ipa)}
        self.setup_ui()
        self.load_file_list()

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

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

        self.root.bind("<space>", self.on_space_key)
        root.bind("<Key-1>", self.on_key_1)
        # self.root.bind("<Up>", self.on_arrow_key)
        # self.root.bind("<Down>", self.on_arrow_key)

        self.progress = ttk.Progressbar(frame, length=400, mode="determinate")
        self.progress.pack(pady=5)

        columns = ("word", "trans", "ipa", "sound", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        self.tree.pack(fill="both", expand=True)
        self.tree.heading("word", text="单词/短语")
        self.tree.heading("trans", text="中文翻译")
        self.tree.heading("ipa", text="音标")
        self.tree.heading("sound", text="🔊播放")
        self.tree.heading("status", text="状态")
        self.tree.heading("learned", text="结果")
        for col, w in zip(columns, [200, 250, 150, 80, 100, 100]):
            self.tree.column(col, width=w, anchor="center")
        self.tree.bind("<ButtonRelease-1>", self.on_click)

    # ---------------- 文件导入 ----------------
    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("TSV文件", "*.tsv"), ("TXT文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        threading.Thread(target=self._import_file_thread, args=(path,), daemon=True).start()

    def _import_file_thread(self, path):
        session = Session()
        filename = os.path.basename(path)
        file_obj = session.query(File).filter_by(filename=filename).first()
        if not file_obj:
            file_obj = File(filename=filename)
            session.add(file_obj)
            session.commit()

        self.current_file_id = file_obj.id

        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        total = len(lines)
        # update progressbar on main thread
        self.root.after(0, lambda: self.progress.config(maximum=total))

        for idx, line in enumerate(lines, 1):
            parts = line.split("\t")
            if len(parts) >= 2:
                word, trans = parts[:2]
                ipa = parts[2] if len(parts) > 2 else None
                # check existing word
                w = session.query(Word).filter_by(word_lower=word.lower(), trans=trans).first()
                if w:
                    word_obj = w
                else:
                    gtts_bin = None
                    try:
                        gtts_bin = token2voice(word)
                    except Exception as e:
                        print(f"{word} TTS 失败: {e}")
                    word_obj = Word(word=word, word_lower=word.lower(), trans=trans, ipa=ipa, gtts=gtts_bin)
                    session.add(word_obj)
                    session.commit()

                iid = f"{file_obj.id}_{word_obj.id}"
                if not session.query(Display).filter_by(iid=iid).first():
                    display = Display(iid=iid, word_ref=word_obj, file=file_obj)
                    session.add(display)
                    session.commit()

            # update progress value on UI thread
            self.root.after(0, lambda v=idx: self.progress.config(value=v))

        session.close()
        self.root.after(0, lambda: (self.load_file_list(), self.progress.config(value=0)))

    # ---------------- 文件列表 ----------------
    def load_file_list(self):
        session = Session()
        files = [row.filename for row in session.query(File).order_by(File.id).all()]
        self.file_combo['values'] = files
        session.close()

    def on_file_selected(self, event):
        filename = self.file_combo.get()
        session = Session()
        file_obj = session.query(File).filter_by(filename=filename).first()
        session.close()
        if file_obj:
            self.current_file_id = file_obj.id
            self.current_page = 0
            self.refresh_table()

    # ---------------- 分页 ----------------
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not self.current_file_id:
            return
        session = Session()
        offset = self.current_page * PAGE_SIZE
        displays = (session.query(Display)
                    .filter(Display.file_id == self.current_file_id)
                    .order_by(Display.id)
                    .offset(offset)
                    .limit(PAGE_SIZE)
                    .all())
        self.words_cache = { d.iid: WordDisplay(d) for d in displays}
        for iid, display in self.words_cache.items():
            self.tree.insert("", "end", iid=iid, values=("", "", "", "播放", "显示", display.is_unlearned))

        total = session.query(Display).filter(Display.file_id == self.current_file_id).count()
        total_pages = max((total-1)//PAGE_SIZE+1,1)
        self.page_label.config(text=f"第 {self.current_page+1} / {total_pages} 页")
        session.close()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        session = Session()
        total = session.query(Display).filter(Display.file_id == self.current_file_id).count()
        total_pages = max((total-1)//PAGE_SIZE+1,1)
        if self.current_page < total_pages-1:
            self.current_page += 1
            self.refresh_table()
        session.close()

    # ---------------- 点击事件 ----------------
    def on_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        iid = item
        # session = Session()
        # d = session.query(Display).filter_by(iid=iid).first()

        d = self.words_cache.get(iid)
        if not d:
            # session.close()
            return
        
        word, trans, ipa, gtts_bin, is_unlearned = d.word, d.trans, d.ipa, d.gtts, d.is_unlearned

        if col == "#4" and gtts_bin:
            # play voice in background
            play_voice(gtts_bin)
        elif col == "#5":
            self.toggle_status(iid, word, trans, ipa, is_unlearned)
        elif col == "#6":
        # session.close()

    def on_key_1(self, event):
        """按空格播放当前选中行的语音"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        d = self.words_cache.get(iid)
        if not d:
            # session.close()
            return
        
        word, trans, ipa, gtts_bin = d.word, d.trans, d.ipa, d.gtts
        self.toggle_status(iid, word, trans, ipa)

    def on_space_key(self, event):
        """按空格播放当前选中行的语音"""
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        
        audio = self.words_cache.get(iid).audio
        if audio:
            audio.play()

    def toggle_status(self, iid, word, trans, ipa, is_unlearned):
        values = self.tree.item(iid, "values")
        if values[0] == "":
            self.tree.item(iid, values=(word, trans, ipa, "播放", "隐藏", is_unlearned))
        else:
            self.tree.item(iid, values=("", "", "", "播放", "显示", is_unlearned))

    def show_all_learned(self):
        for iid, display in self.words_cache.items():
            self.tree.item(iid, values=(display.word, display.trans, display.ipa, "播放", "显示", display.is_unlearned))


if __name__ == "__main__":
    root = tk.Tk()
    app = WordApp(root)
    root.mainloop()
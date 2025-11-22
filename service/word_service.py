from model.orm_models import Word, Display, File
from service.db_utils import auto_session
from service.audio_service import AudioPlayer
from util.audio_util import token2voice

class WordDisplay:
    """UI 层显示所需的封装"""
    def __init__(self, display: Display):
        self.id = display.id
        self.iid = display.iid
        self.word_id = display.word_id
        self.file_id = display.file_id
        self.from_word(display.word_ref)
    
    def from_word(self, word: Word):
        self.word = word.word
        self.trans = word.trans
        self.ipa = word.ipa
        self.gtts = word.gtts
        self.is_unlearned = word.is_unlearned
        self.audio = AudioPlayer(self.gtts)

class WordService:
    """管理单词的查询与状态更新"""

    @staticmethod
    def get_displays_by_page(file_id, page_size, offset):
        with auto_session() as session:
            displays = (
                session.query(Display)
                .filter(Display.file_id == file_id) # pyright: ignore[reportOptionalCall]
                .order_by(Display.id)
                .offset(offset)
                .limit(page_size)
                .all()
            )
            return {d.iid: WordDisplay(d) for d in displays}

    @staticmethod
    def count_displays(file_id):
        with auto_session() as session:
            return session.query(Display).filter(Display.file_id == file_id).count() # pyright: ignore[reportOptionalCall]

    @staticmethod
    def toggle_unlearned(word_display: WordDisplay) -> WordDisplay:
        new_status = not word_display.is_unlearned
        with auto_session() as session:
            d = session.query(Display).filter_by(iid=word_display.iid).first()
            d.word_ref.is_unlearned = new_status
            session.flush()
            return WordDisplay(d)
        
    @staticmethod
    def update_display(word_display: WordDisplay, field: str):
        """
        根据 WordDisplay 对象更新数据库。
        UI 层只需要给我 display + 哪个字段被改了即可。
        """
        # 获取字段值
        field_val = getattr(word_display, field, None)
        if field_val is None:
            return None

        with auto_session() as session:
            d = session.query(Display).filter_by(iid=word_display.iid).first()
            if not d:
                return None

            # 特殊逻辑：修改 word 时生成 gtts
            if field == "word":
                try:
                    d.word_ref.gtts = token2voice(field_val)
                except Exception as e:
                    print(f"TTS 生成失败: {field_val} ({e})")

            setattr(d.word_ref, field, field_val)
            session.flush()
            return WordDisplay(d)

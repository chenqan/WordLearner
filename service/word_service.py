from model.orm_models import Word, Display
from service.db_utils import auto_session
from service.audio_service import AudioPlayer

class WordDisplay:
    """UI 层显示所需的封装"""
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

class WordService:
    """管理单词的查询与状态更新"""

    @staticmethod
    def get_displays_by_page(file_id, page_size, offset):
        with auto_session() as session:
            displays = (
                session.query(Display)
                .filter(Display.file_id == file_id)
                .order_by(Display.id)
                .offset(offset)
                .limit(page_size)
                .all()
            )
            return {d.iid: WordDisplay(d) for d in displays}

    @staticmethod
    def count_displays(file_id):
        with auto_session() as session:
            return session.query(Display).filter(Display.file_id == file_id).count()

    @staticmethod
    def toggle_unlearned(word_display: WordDisplay) -> WordDisplay:
        new_status = not word_display.is_unlearned
        with auto_session() as session:
            d = session.query(Display).filter_by(iid=word_display.iid).first()
            d.word_ref.is_unlearned = new_status
            session.flush()
            return WordDisplay(d)

import os
from model.orm_models import File, Word, Display
from service.db_utils import auto_session
from util.audio_util import token2voice

class FileService:
    """处理文件导入与文件数据加载"""

    @staticmethod
    def file_exists(filename: str) -> bool:
        with auto_session() as session:
            return session.query(File).filter_by(filename=filename).first() is not None

    @staticmethod
    def read_file(path: str):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    word, trans = parts[:2]
                    ipa = parts[2] if len(parts) > 2 else None
                    data.append((word, trans, ipa))
        return data, len(data)

    @staticmethod
    def import_file(path: str):
        filename = os.path.basename(path)
        if FileService.file_exists(filename):
            print(f"文件 {filename} 已存在，跳过。")
            return

        data, total = FileService.read_file(path)
        print(f"读取到 {total} 条记录，准备导入数据库...")

        with auto_session() as session:
            file_obj = File(filename=filename)
            session.add(file_obj)
            session.flush()

            display_batch = []
            word_cache = {}

            for idx, (word, trans, ipa) in enumerate(data, 1):
                key = (word.lower(), trans)
                word_obj = word_cache.get(key)
                if not word_obj:
                    existing = session.query(Word).filter_by(word_lower=word.lower(), trans=trans).first()
                    if not existing:
                        try:
                            gtts_bin = token2voice(word)
                        except Exception as e:
                            print(f"TTS 生成失败: {word} ({e})")
                            gtts_bin = None
                        existing = Word(word=word, word_lower=word.lower(), trans=trans, ipa=ipa, gtts=gtts_bin)
                        session.add(existing)
                        session.flush()
                    word_cache[key] = existing
                    word_obj = existing

                iid = f"{file_obj.id}_{word_obj.id}"
                if not session.query(Display).filter_by(iid=iid).first():
                    display_batch.append(Display(iid=iid, word_ref=word_obj, file=file_obj))

                if idx % 5 == 0:
                    session.add_all(display_batch)
                    session.commit()
                    display_batch.clear()
                    yield idx, total  # 用于进度反馈

            if display_batch:
                session.add_all(display_batch)
            session.commit()
            yield total, total

    @staticmethod
    def list_files():
        with auto_session() as session:
            return [f.filename for f in session.query(File).order_by(File.id).all()]

    @staticmethod
    def get_file_id(filename):
        with auto_session() as session:
            file = session.query(File).filter_by(filename=filename).first()
            return file.id if file else None

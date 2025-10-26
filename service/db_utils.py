from contextlib import contextmanager
from model.orm_models import Session

@contextmanager
def auto_session():
    """自动提交/回滚/关闭 session"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

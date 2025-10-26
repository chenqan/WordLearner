# 🧠 WordLearner —— 单词学习助手

一个基于 Tkinter + SQLAlchemy 的本地英语单词学习工具。
支持文件导入、分页显示、单词显示/隐藏切换、音标与音频播放、学习状态管理等功能。

## 📁 项目结构
```shell
WordLearner/
├─ model/
│   └─ orm_models.py           # ORM 模型定义（Word、File、Display、数据库连接等）
│
├─ service/
│   ├─ db_utils.py             # 数据库基础工具，如 auto_session
│   ├─ file_service.py         # 文件导入与管理逻辑
│   ├─ word_service.py         # 单词显示与学习状态逻辑
│   └─ audio_service.py        # 音频播放与语音合成（gTTS + pydub）
│
├─ view/
│   └─ word_app.py             # Tkinter 前端主程序（UI 界面逻辑）
│
└─ util/
    └─ audio_util.py           # 音频相关的辅助函数
```

## ⚙️ 环境依赖

建议使用 Python 3.8+，并在虚拟环境中安装以下依赖包：

```shell
pip install sqlalchemy pydub gTTS simpleaudio numpy
```

如需更快音频播放，可额外安装：
```shell
pip install sounddevice
```

## 🧩 核心模块说明


```
1. model/orm_models.py

定义数据库模型类：
Word：单词与翻译信息
File：单词来源文件信息
Display：单词在学习界面中的展示状态

建立数据库连接：

engine = create_engine(f"sqlite:///{DB_FILE}", echo=False, future=True)
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()

2. service/db_utils.py

提供自动化的数据库会话管理器：

@contextmanager
def auto_session(session):
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

确保每次数据库操作自动提交、异常回滚、资源释放。

3. service/file_service.py

实现文件导入功能（支持 .txt / .tsv）
将文件内容解析为 Word 实体并写入数据库
提供文件下拉框所需的文件列表接口

4. service/word_service.py

根据分页加载单词记录
负责切换单词学习状态（未学/已学）
管理界面中单词显示状态（显示/隐藏）

5. service/audio_service.py

基于 gTTS 生成英语语音
基于 pydub 或 sounddevice 播放音频
提供缓存机制，避免重复生成音频

6. view/word_app.py

主界面逻辑，功能包括：
文件导入与进度条显示
文件列表选择与分页加载
单词的显示 / 隐藏切换
空格键播放语音
1 键切换学习状态
一键显示全部已学单词

核心 UI 元素：

TreeView 表格展示单词
Combobox 文件选择器
Progressbar 文件导入进度

```

## 💡 快速开始


### 初始化数据库
```shell
python -m model.orm_models
```

### 启动程序
```shell
python main_app.py
```

### 导入文件

支持 .txt 或 .tsv 文件格式

```python
#文件格式示例：

word	transcription	translation
apple	ˈæpl	苹果
book	bʊk	书
```

### 操作说明

1. 空格键：播放当前单词语音
2. 数字 1 键：切换当前单词“已学/未学”状态
3. 显示全部已学会 按钮：显示所有隐藏单词
4. 点击“播放”列：播放单词语音
5. 点击“隐藏/显示”列：切换单词显示状态

## 🔊 音频播放机制

程序优先尝试使用以下顺序播放：

pydub + sounddevice（首选）

## 🧰 可扩展方向

支持用户自定义发音引擎（如 Azure TTS）

增加“按标签学习”或“复习计划”功能

将进度记录保存到云端

使用 PyQt 或 Web 前端重构 UI

## 🧑‍💻 作者

Chenqan
项目定位：个人英语学习与听力记忆辅助工具
语言环境：Python + Tkinter + SQLAlchemy
数据库：SQLite 本地数据库

## 📜 许可证

本项目基于 MIT License 开源。你可以自由修改与分发，但请保留原作者署名。
# WordLearner

A simple English vocabulary learning app built with Tkinter.

## ✨ Features

1. Import words from files or external sources
2. Toggle word visibility (show/hide meanings & IPA)
3. Mark words as learned or unlearned
4. Play pronunciation audio
5. Auto-save learning progress

## 🧩 Project Structure

```shell
WordLearner/
├─ model/
│   └─ orm_models.py           # ORM Model(Word, File, and Display)
│
├─ service/
│   ├─ db_utils.py             # auto_session
│   ├─ file_service.py         
│   ├─ word_service.py         
│   └─ audio_service.py        # gTTS + pydub
│
├─ view/
│   └─ word_app.py             # UI 
│
└─ util/
    └─ audio_util.py
```

## 🚀 Run
```shell
git clone https://github.com/chenqan/WordLearner.git
cd WordLearner
python python main_app.py
```

## 📜 License

MIT License © 2025 chenqan
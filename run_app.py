import os
import sys
import multiprocessing

def main():
    # Предохранитель для Windows
    multiprocessing.freeze_support()

    # Отключаем запрос email и сбор статистики Streamlit
    os.environ["STREAMLIT_GATHER_USAGE_STATS"] = "false"

    # Переход в папку с распакованными файлами .exe
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)

    import streamlit.web.cli as stcli
    
    # Запускаем Streamlit
    sys.argv = [
        "streamlit", 
        "run", 
        "dashboard.py", 
        "--global.developmentMode=false", 
        "--server.port=8501", 
        "--server.headless=false"
    ]
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()

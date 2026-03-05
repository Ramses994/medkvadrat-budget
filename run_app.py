import os
import sys
import multiprocessing

def main():
    # Предохранитель для Windows
    multiprocessing.freeze_support()

    # Переход в папку с распакованными файлами .exe
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)

    import streamlit.web.cli as stcli
    
    # Запускаем Streamlit с явным отключением режима разработчика
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

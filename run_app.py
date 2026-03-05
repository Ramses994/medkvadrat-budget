import os
import sys
import multiprocessing

def main():
    # 1. Предохранитель для Windows: останавливает бесконечный запуск процессов
    multiprocessing.freeze_support()

    # 2. Указываем программе искать dashboard.py внутри распакованного .exe
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)

    # 3. Запускаем Streamlit напрямую через его внутренний модуль
    import streamlit.web.cli as stcli
    
    # Имитируем команду "streamlit run dashboard.py"
    sys.argv = ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.headless=false"]
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()

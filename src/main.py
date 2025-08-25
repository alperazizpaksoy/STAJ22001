from ttkbootstrap import Window
from gui.main_window import URLExtractorGUI


def main():
    """Ana uygulama başlatma fonksiyonu"""
    root = Window(themename="flatly")
    app = URLExtractorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


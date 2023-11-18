import gui
from utils import ReadApiKeys


if __name__ == "__main__":
    
    API_KEY = ReadApiKeys.youtube_api_key()
    gui_handler = gui.gui_builder(API_KEY)
    gui_handler.start()
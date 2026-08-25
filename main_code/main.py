import sys, os

# If using windows
if sys.platform.startswith("win"):
    import ctypes

    try:
        # try to use windows newest dots per inch (DPI) scaling
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        # otherwise disable windows DPI scaling
        ctypes.windll.user32.SetProcessDPIAware()

os.environ["SDL_VIDEO_HIGHDPI_DISABLED"] = "1"

import pygame, asyncio, random, datetime
from gui.assets import Assets
from gui.menu_window import MenuWindow
from gui.game_window import GameWindow
from core.controller import OfflineController, KuhnController

BASE_RESOLUTION = (1600, 900)
FPS = 60

x = datetime.datetime.now()
random.seed(x.year * x.day * x.microsecond)

class PokerApp:
    def __init__(self, testing=False):
        # pygame.init()
        pygame.font.init()
        pygame.display.init()
        pygame.display.set_caption("Poker")
        self.set_initial_size()
        self.assets = Assets(self.screen, BASE_RESOLUTION)
        self.__controller = None
        self.testing = testing
        self.set_menu_window()

    def set_initial_size(self):
        scale = (
            min(
                pygame.display.Info().current_w / BASE_RESOLUTION[0],
                pygame.display.Info().current_h / BASE_RESOLUTION[1],
            )
            * 0.9
        )

        width = scale * BASE_RESOLUTION[0]
        height = scale * BASE_RESOLUTION[1]

        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

        # For pygbag
        # self.screen = pygame.display.set_mode((3200, 1800), pygame.RESIZABLE)

    def set_menu_window(self):
        self.current_window = MenuWindow(
            screen=self.screen,
            assets=self.assets,
        )

    # Add Ip address 3 lines below here e.g
    # def start_game(self, mode="Offline", host_ip='171.35.61.2'):

    def start_game(self, mode="Offline", host_ip=None): #Replace None to your 'ip address' on this line
        """Instantiates correct controller depending on button clicked
        and instantiates the game window"""
        try:
            if mode == "Kuhn":
                self.__controller = KuhnController()
            elif mode == "Online":
                from core.controller import OnlineController

                self.__controller = OnlineController(host_ip=host_ip)
            else:
                self.__controller = OfflineController(testing=self.testing)

        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.current_window.set_window("")
            return

        self.current_window = GameWindow(
            screen=self.screen,
            assets=self.assets,
            controller=self.__controller,
            testing=self.testing,
            mode="Kuhn" if mode == "Kuhn" else "Poker",
        )

    def quit_game(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def resize(self, event):
        new_size = (event.w, event.h)
        self.screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
        self.assets.rescale(new_size)
        self.current_window.resize(new_size)

    def check_window_change(self):
        """Checks if the current window has requested to change window and if so changes the window"""
        new_window = self.current_window.new_window

        if new_window:
            if new_window == "Offline Poker":
                self.start_game(mode="Offline")
            elif new_window == "Kuhn Poker":
                self.start_game(mode="Kuhn")
            elif new_window == "Online Poker":
                self.start_game(mode="Online")  
            elif new_window == "Menu":
                self.set_menu_window()

    async def run(self):
        running = True
        while running:

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.resize(event)
                else:
                    self.current_window.handle_event(event)

            self.check_window_change()
            self.current_window.update()
            self.current_window.draw()
            if self.__controller is not None:
                self.__controller.tick()

            pygame.display.flip()
            await asyncio.sleep(0)

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    arg = sys.argv
    app = PokerApp(testing=arg[1] if len(arg) > 1 and arg[1][0] in "th" else False)
    asyncio.run(app.run())

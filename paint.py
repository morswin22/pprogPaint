import tkinter as tk
from tkinter import colorchooser, filedialog, ttk
import configparser, os, shutil
import re

from pprint import pprint

import pygame
import platform

def hex_to_rgb(value):
    h = value.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

class MainWindow(tk.Frame):
    config = {}
    windows = {"tools": None, "layers": None, "settings": None}
    layers = []
    layer = None
    layerID = None
    pressed = False
    listening = False
    tool = 'brush'

    def __init__(self, config):
        super().__init__()

        self.configurate(config)
        self.initUI()
        self.master.bind("<Configure>", self.sync_windows)
        self.embed.bind('<Enter>', lambda _: self.c_listening(True))
        self.embed.bind('<Leave>', lambda _: self.c_listening(False))


        os.environ['SDL_WINDOWID'] = str(self.embed.winfo_id())
        if platform.system() == "Windows":
            os.environ['SDL_VIDEODRIVER'] = 'windib'
        self.canvas = pygame.display.set_mode((self.config['cwidth'], self.config['cheight']))
        self.canvas.fill(pygame.Color(255, 255, 255))
        pygame.display.init()

        self.c_add_layer()
        self.master.after(100,self.c_update)
        
        self.c_colors = { 
            'white':  (255, 255, 255), 
            'black':  (0,   0,   0), 
            'red':    (255, 0,   0), 
            'green':  (0,   255, 0), 
            'blue':   (0,   0,   255),
            'cyan':   (0,   255, 255),
            'yellow': (255, 255, 0),
            'magenta':(255, 0,   255)
        }
        self.c_set_color('black')
        self.c_size=1

    def configurate(self, config):
        self.config['width'] = int(config['MainWindow']['width']) or 800
        self.config['height'] = int(config['MainWindow']['height']) or 600
        self.config['cwidth'] = int(config['Canvas']['width']) or 600
        self.config['cheight'] = int(config['Canvas']['height']) or 400
        if config['Tools']['open'] == 'yes': self.config['open_tools'] = True 
        else: self.config['open_tools'] = False
        if config['Layers']['open'] == 'yes': self.config['open_layers'] = True 
        else: self.config['open_layers'] = False
        self.config['colors'] = []
        for i in range(20):
            self.config['colors'].append(config['Tools']['c%d' % i])

    def initUI(self):
        self.master.title("Paint")
        self.master.geometry("%dx%d" % (self.config['width'],self.config['height']))
        self.pack(expand=True)

        self.embed = tk.Frame(self, width=self.config['cwidth'], height=self.config['cheight'], background="white")
        self.embed.pack()

        # Tools aside
        tools = tk.Toplevel(self)
        if not self.config['open_tools']: tools.wm_withdraw()
        tools.wm_title('Narzędzia')
        tools.geometry("150x%d" % self.config['height'])
        tools.protocol("WM_DELETE_WINDOW",lambda: self.close_window('tools'))

        tools_colors = tk.LabelFrame(tools, text="Kolory")
        tools_colors.pack(expand=True)

        row = 0
        column = 0
        colors = {}
        for color in self.config['colors']:
            btn = tk.Button(tools_colors, bg=color, width=2, height=1)
            btn.bind("<Button-1>", lambda e: self.c_set_color(colors[e.widget]))
            btn.grid(row=row, column=column, padx=2, pady=2)
            colors[btn] = color
            column += 1
            if (column == 2):
                row += 1
                column = 0

        tools_colors_custom = tk.Button(tools_colors, bg="#ed5a53", text="?", fg="white", width=2, height=1)
        tools_colors_custom.bind("<Button-1>", lambda e: self.c_add_color(colorchooser.askcolor()))
        tools_colors_custom.grid(row=0, column=2, padx=2, pady=2)

        self.custom_colors = {}
        self.next_custom_color = 0
        for i in range(1,10):
            btn = tk.Button(tools_colors, bg="white", width=2, height=1)
            btn.bind("<Button-1>", lambda e: self.c_set_color(self.custom_colors[e.widget]))
            btn.grid(row=i, column=2, padx=2, pady=2)
            self.custom_colors[btn] = None

        tools_size = tk.LabelFrame(tools, text="Grubość")
        tools_size.pack(expand=True)

        tools_size_combobox = ttk.Combobox(tools_size, values=["1px", "2px", "4px", "8px", "16px", '24px', '32px', '40px', '48px'])
        tools_size_combobox.bind('<<ComboboxSelected>>', self.c_set_size)
        tools_size_combobox.pack()

        tools_tool = tk.LabelFrame(tools, text="Narzędzia")
        tools_tool.pack(expand=True)
        
        row = 0
        column = 0
        values = {}
        for tool in ('brush','bucket'):
            btn = tk.Button(tools_tool, text=tool.capitalize())
            btn.bind("<Button-1>", lambda e: self.c_set_tool(values[e.widget]))
            btn.grid(row=row, column=column, padx=2, pady=2)
            values[btn] = tool
            column += 1
            if (column == 2):
                row += 1
                column = 0

        self.windows['tools'] = tools

        # Layers aside
        layers = tk.Toplevel(self)
        if not self.config['open_layers']: layers.wm_withdraw()
        layers.wm_title('Warstwy')
        layers.geometry("150x%d" % self.config['height'])
        layers.protocol("WM_DELETE_WINDOW", lambda: self.close_window('layers'))
        self.windows['layers'] = layers

        # Settings
        global config

        settings = tk.Toplevel(self)
        settings.wm_withdraw()
        settings.wm_title('Ustawienia')
        settings.protocol("WM_DELETE_WINDOW", lambda: self.close_window('settings'))

        settings_size = tk.LabelFrame(settings, text="Domyślna wielkość okna", padx=5, pady=5)
        settings_size.pack(padx=10, pady=10)

        settings_size_wl = tk.Label(settings_size, text="Szerokość")
        settings_size_wl.grid(row=0, column=0, sticky='E', padx=5, pady=2)

        settings_size_we_sv = tk.StringVar()
        settings_size_we_sv.set(self.config['width'])
        settings_size_we = tk.Entry(settings_size, textvariable=settings_size_we_sv)
        settings_size_we.bind('<Return>', (lambda _: self.change_config('MainWindow','width',settings_size_we.get())))
        settings_size_we.grid(row=0, column=1, sticky='W', padx=5, pady=2)

        settings_size_hl = tk.Label(settings_size, text="Wysokość")
        settings_size_hl.grid(row=1, column=0, sticky='E', padx=5, pady=2)

        settings_size_he_sv = tk.StringVar()
        settings_size_he_sv.set(self.config['height'])
        settings_size_he = tk.Entry(settings_size, textvariable=settings_size_he_sv)
        settings_size_he.bind('<Return>', (lambda _: self.change_config('MainWindow','height',settings_size_he.get())))
        settings_size_he.grid(row=1, column=1, sticky='W', padx=5, pady=2)

        settings_csize = tk.LabelFrame(settings, text="Domyślna wielkość płótna", padx=5, pady=5)
        settings_csize.pack(padx=10, pady=10)

        settings_csize_wl = tk.Label(settings_csize, text="Szerokość")
        settings_csize_wl.grid(row=0, column=0, sticky='E', padx=5, pady=2)

        settings_csize_we_sv = tk.StringVar()
        settings_csize_we_sv.set(self.config['cwidth'])
        settings_csize_we = tk.Entry(settings_csize, textvariable=settings_csize_we_sv)
        settings_csize_we.bind('<Return>', (lambda _: self.change_config('Canvas','width',settings_csize_we.get())))
        settings_csize_we.grid(row=0, column=1, sticky='W', padx=5, pady=2)

        settings_csize_hl = tk.Label(settings_csize, text="Wysokość")
        settings_csize_hl.grid(row=1, column=0, sticky='E', padx=5, pady=2)

        settings_csize_he_sv = tk.StringVar()
        settings_csize_he_sv.set(self.config['cheight'])
        settings_csize_he = tk.Entry(settings_csize, textvariable=settings_csize_he_sv)
        settings_csize_he.bind('<Return>', (lambda _: self.change_config('Canvas','height',settings_csize_he.get())))
        settings_csize_he.grid(row=1, column=1, sticky='W', padx=5, pady=2)

        settings_windows = tk.LabelFrame(settings, text="Widok okien", padx=5, pady=5)
        settings_windows.pack(padx=10, pady=10)

        settings_windows_tc_sv = tk.StringVar()
        settings_windows_tc_sv.set(config['Tools']['open'])
        settings_windows_tc = tk.Checkbutton(settings_windows, text="Otwieraj narzędzia", \
            variable=settings_windows_tc_sv, onvalue="yes", offvalue="no", command=(lambda: self.change_config('Tools','open',settings_windows_tc_sv.get())))
        settings_windows_tc.grid(row=0, sticky='W', padx=5, pady=2)

        settings_windows_lc_sv = tk.StringVar()
        settings_windows_lc_sv.set(config['Layers']['open'])
        settings_windows_lc = tk.Checkbutton(settings_windows, text="Otwieraj warstwy", \
            variable=settings_windows_lc_sv, onvalue="yes", offvalue="no", command=(lambda: self.change_config('Layers','open',settings_windows_lc_sv.get())))
        settings_windows_lc.grid(row=1, sticky='W', padx=5, pady=2)

        settings_info = tk.Label(settings, text="Aby zapisać zmiany pól tekstowych, wciśnij klawisz Enter")
        settings_info.pack(padx=5, pady=5)

        self.windows['settings'] = settings

        # Menu
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        fileMenu = tk.Menu(menubar)
        # fileMenu.add_command(label="Zapisz", command=lambda: self.save_canvas(filedialog.asksaveasfilename(title = "Wybierz plik",filetypes = (("pliki jpeg","*.jpg"),("wszystkie pliki","*.*")))))
        fileMenu.add_command(label="Wyjście", command=self.on_exit)
        menubar.add_cascade(label="Plik", menu=fileMenu)

        viewMenu = tk.Menu(menubar)
        viewMenu.add_command(label="Narzędzia", command=lambda: self.open_window('tools'))
        viewMenu.add_command(label="Warstwy", command=lambda: self.open_window('layers'))
        menubar.add_cascade(label="Widok", menu=viewMenu)

        menubar.add_command(label="Ustawienia", command=lambda: self.open_window('settings'))

    def c_use_tool_start(self, pos):
        if self.tool == 'brush':
            self.c_point(pos)
        elif self.tool == 'bucket':
            self.c_bucket(pos)

    def c_use_tool(self, pos):
        if self.tool == 'brush':
            self.c_line(pos)

    def c_set_tool(self, tool):
        self.tool = tool

    def c_point(self, pos):
        pygame.draw.circle(self.layer['surface'], self.c_color, pos, self.c_size//2)
        self.c_mouse_last = pos

    def c_line(self, pos):
        if self.c_size > 4:
            pygame.draw.circle(self.layer['surface'], self.c_color, pos, self.c_size//2)
        pygame.draw.line(self.layer['surface'], self.c_color, self.c_mouse_last, pos, self.c_size)
        self.c_mouse_last = pos

    def c_bucket(self, pos):
        pass

    def c_set_color(self, color):
        if color != None:
            if color not in self.c_colors.keys():
                self.c_colors[color] = hex_to_rgb(color)
            self.c_color = self.c_colors[color]

    def c_set_size(self, event):
        self.c_size = int(re.search(r'\d+', event.widget.get()).group())

    def c_add_color(self, values):
        h = values[1]
        if h != None:
            i = 0
            for btn in self.custom_colors:
                if i==self.next_custom_color:
                    self.custom_colors[btn] = h
                    btn.config(bg=h)
                    self.c_color = h
                    self.next_custom_color += 1
                    if self.next_custom_color == 9:
                        self.next_custom_color = 0
                    break
                i+=1

    def c_listening(self, value):
        self.listening = value

    def c_update(self):
        if self.listening:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.pressed = True
                    self.c_use_tool_start(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEMOTION and self.pressed:
                    self.c_use_tool(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.pressed = False

        for layer in self.layers:
            self.canvas.blit(layer['surface'], (0,0))
        pygame.display.update()
        self.master.after(1,self.c_update)

    def c_add_layer(self):
        layer = pygame.Surface([self.config['cwidth'], self.config['cheight']], pygame.SRCALPHA, 32)
        self.layerID = len(self.layers)
        self.layers.append({'name': 'Warstwa %d' % (self.layerID + 1), 'surface': layer})
        self.layer = self.layers[self.layerID]

    def open_window(self, id):
        self.windows[id].wm_deiconify()

    def close_window(self, id):
        self.windows[id].wm_withdraw()

    def sync_windows(self, event=None):
        x = self.master.winfo_x()
        y = self.master.winfo_y()
        self.windows['tools'].geometry("+%d+%d" % (x + self.master.winfo_width() + 4 ,y))
        self.windows['layers'].geometry("+%d+%d" % (x - self.windows['layers'].winfo_width() - 4 ,y))

    def change_config(self, master, key, value):
        global config
        config[master][key] = value
        with open('./user.cfg', 'w') as configfile:
            config.write(configfile)

    def on_exit(self):
        self.quit()

if __name__ == '__main__':
    config = configparser.ConfigParser()
    if not os.path.isfile('./user.cfg'):
        shutil.copyfile('./assets/default.cfg', './user.cfg')
    config.read_file(open('./user.cfg'))

    root = tk.Tk()
    app = MainWindow(config)
    root.mainloop()
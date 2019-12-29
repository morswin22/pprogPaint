import tkinter as tk
import configparser, os, shutil

class MainWindow(tk.Frame):
    config = {}
    windows = {"tools": None, "layers": None, "settings": None}

    def __init__(self, config):
        super().__init__()

        self.configurate(config)
        self.initUI()
        self.master.bind("<Configure>", self.sync_windows)
        
        for key in config:  
            print(key)

    def configurate(self, config):
        self.config['width'] = int(config['MainWindow']['width']) or 600
        self.config['height'] = int(config['MainWindow']['height']) or 400
        if config['Tools']['open'] == 'yes': self.config['open_tools'] = True 
        else: self.config['open_tools'] = False
        if config['Layers']['open'] == 'yes': self.config['open_layers'] = True 
        else: self.config['open_layers'] = False

    def initUI(self):
        self.master.title("Paint")
        self.master.geometry("%dx%d" % (self.config['width'],self.config['height']))

        # Tools aside
        tools = tk.Toplevel(self)
        if not self.config['open_tools']: tools.wm_withdraw()
        tools.wm_title('Narzędzia')
        tools.geometry("150x%d" % self.config['height'])
        tools.protocol("WM_DELETE_WINDOW", self.close_tools)
        self.windows['tools'] = tools

        # Layers aside
        layers = tk.Toplevel(self)
        if not self.config['open_layers']: layers.wm_withdraw()
        layers.wm_title('Warstwy')
        layers.geometry("150x%d" % self.config['height'])
        layers.protocol("WM_DELETE_WINDOW", self.close_layers)
        self.windows['layers'] = layers

        # Settings
        settings = tk.Toplevel(self)
        settings.wm_withdraw()
        settings.wm_title('Ustawienia')
        settings.protocol("WM_DELETE_WINDOW", self.close_settings)

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

        self.windows['settings'] = settings

        # Menu
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        fileMenu = tk.Menu(menubar)
        fileMenu.add_command(label="Wyjście", command=self.on_exit)
        menubar.add_cascade(label="Plik", menu=fileMenu)

        viewMenu = tk.Menu(menubar)
        viewMenu.add_command(label="Narzędzia", command=self.open_tools)
        viewMenu.add_command(label="Warstwy", command=self.open_layers)
        menubar.add_cascade(label="Widok", menu=viewMenu)

        menubar.add_command(label="Ustawienia", command=self.open_settings)

    def open_layers(self):
        self.open_window('layers')

    def open_tools(self):
        self.open_window('tools')

    def open_settings(self):
        self.open_window('settings')

    def open_window(self, id):
        self.windows[id].wm_deiconify()

    def close_layers(self):
        self.close_window('layers')

    def close_tools(self):
        self.close_window('tools')

    def close_settings(self):
        self.close_window('settings')

    def close_window(self, id):
        self.windows[id].wm_withdraw()

    def sync_windows(self, event=None):
        x = self.master.winfo_x()
        y = self.master.winfo_y()
        self.windows['tools'].geometry("+%d+%d" % (x + self.master.winfo_width() + 4,y))
        self.windows['layers'].geometry("+%d+%d" % (x - self.windows['layers'].winfo_width() - 4,y))

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
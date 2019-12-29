import tkinter as tk
import tkinter.colorchooser
import configparser, os, shutil
import re

from pprint import pprint

class MainWindow(tk.Frame):
    config = {}
    windows = {"tools": None, "layers": None, "settings": None}

    def __init__(self, config):
        super().__init__()

        self.configurate(config)
        self.initUI()
        self.master.bind("<Configure>", self.sync_windows)
        self.canvas.bind("<Button-1>", self.c_point)
        self.canvas.bind('<B1-Motion>', self.c_line)
        
        self.c_clear()
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

        self.canvas = tk.Canvas(self, width=self.config['cwidth'], height=self.config['cheight'])
        self.canvas.pack()

        # Tools aside
        tools = tk.Toplevel(self)
        if not self.config['open_tools']: tools.wm_withdraw()
        tools.wm_title('Narzędzia')
        tools.geometry("150x%d" % self.config['height'])
        tools.protocol("WM_DELETE_WINDOW", self.close_tools)

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
        tools_colors_custom.bind("<Button-1>", lambda e: self.c_add_color(tkinter.colorchooser.askcolor()))
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

        tools_size_listbox = tk.Listbox(tools_size)
        tools_size_listbox.bind('<<ListboxSelect>>', self.c_set_size)
        tools_size_listbox.pack()

        for item in ["1px", "2px", "3px", "5px", "10px", '15px', '20px', '25px', '30px']:
            tools_size_listbox.insert(tk.END, item)

        self.windows['tools'] = tools

        # Layers aside
        layers = tk.Toplevel(self)
        if not self.config['open_layers']: layers.wm_withdraw()
        layers.wm_title('Warstwy')
        layers.geometry("150x%d" % self.config['height'])
        layers.protocol("WM_DELETE_WINDOW", self.close_layers)
        self.windows['layers'] = layers

        # Settings
        global config

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
        fileMenu.add_command(label="Wyjście", command=self.on_exit)
        menubar.add_cascade(label="Plik", menu=fileMenu)

        viewMenu = tk.Menu(menubar)
        viewMenu.add_command(label="Narzędzia", command=self.open_tools)
        viewMenu.add_command(label="Warstwy", command=self.open_layers)
        menubar.add_cascade(label="Widok", menu=viewMenu)

        menubar.add_command(label="Ustawienia", command=self.open_settings)

    def c_point(self, event):
        off = self.c_size//2
        x1, y1 = (event.x - off), (event.y - off)
        x2, y2 = (event.x + off), (event.y + off)
        self.canvas.create_oval(x1, y1, x2, y2, width = 0, fill=self.c_color)
        self.c_mouse_last = event

    def c_line(self, event):
        off = self.c_size//2
        x1, y1 = (event.x - off), (event.y - off)
        x2, y2 = (event.x + off), (event.y + off)
        self.canvas.create_oval(x1, y1, x2, y2, width = 0, fill=self.c_color)
        self.canvas.create_line(self.c_mouse_last.x, self.c_mouse_last.y, event.x, event.y, width = self.c_size, fill=self.c_color)
        self.c_mouse_last = event

    def c_set_color(self, color):
        if color != None:
            self.c_color = color

    def c_set_size(self, event):
        w = event.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        self.c_size = int(re.search(r'\d+', value).group())

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

    def c_clear(self):
        self.canvas.delete(tk.ALL)
        self.canvas.create_rectangle(0, 0, self.config['cwidth']+2, self.config['cheight']+2, fill="white")

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
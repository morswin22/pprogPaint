import tkinter as tk
from tkinter import colorchooser, filedialog, ttk
import configparser, os, shutil
import re

import pygame
import platform

from PIL import Image, ImageTk

def hex_to_rgb(value):
    h = value.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def color_distance(col_a, col_b):
    r = (col_a[0] + col_b[0]) / 2
    return (2 + r/256) * (col_a[0] - col_b[0])**2 + 4 * (col_a[1] - col_b[1])**2 + (2 + (255-r)/256) * (col_a[2] - col_b[2])**2

class MainWindow(tk.Frame):
    config = {}
    windows = {"tools": None, "layers": None, "settings": None, "layer_rename": None, "canvas_resize": None}
    layers = []
    layer = None
    layerID = None
    pressed = False
    listening = False
    tool = 'brush'
    tools = {'brush': 'Pędzel','line': 'Linia','ink': 'Pipeta','bucket': 'Wiaderko','square': 'Kwadrat','rectangle': 'Prostokąt','circle': 'Koło','ellipse': 'Elipsa'}

    locked = False
    info_layer = None

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
        self.canvas = pygame.display.set_mode((self.config['cwidth'], self.config['cheight']), pygame.RESIZABLE)
        self.canvas.fill(pygame.Color(255, 255, 255))
        pygame.display.init()

        self.info_layer = pygame.Surface([self.config['cwidth'], self.config['cheight']], pygame.SRCALPHA, 32)

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
            'magenta':(255, 0,   255),
            'blank':  (255, 255, 255, 0)
        }
        self.c_set_color('black')
        self.c_size=2
        self.c_bucket_calculating = False
        self.c_shape_from = None

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
        self.config['status_spacing'] = int(config['MainWindow']['status_spacing']) or 30

    def initUI(self):
        self.master.title("Paint")
        self.master.geometry("%dx%d" % (self.config['width'],self.config['height']))
        self.pack(expand=True)

        self.embed = tk.Frame(self, width=self.config['cwidth'], height=self.config['cheight'], background="white")
        self.embed.pack()

        self.statusbar = tk.Label(self.master, text="Ładowanie...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

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

        self.tools_blank = ImageTk.PhotoImage(Image.open('./assets/blank.png'))
        tools_color_blank = tk.Button(tools_colors, image=self.tools_blank)
        tools_color_blank.bind("<Button-1>", lambda e: self.c_set_color('blank'))
        tools_color_blank.grid(row=0, column=2, padx=2, pady=2)

        tools_colors_custom = tk.Button(tools_colors, bg="#ed5a53", text="?", fg="white", width=2, height=1)
        tools_colors_custom.bind("<Button-1>", lambda e: self.c_add_color(colorchooser.askcolor()))
        tools_colors_custom.grid(row=1, column=2, padx=2, pady=2)

        self.custom_colors = {}
        self.next_custom_color = 0
        for i in range(2,10):
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
        for tool in ('brush','line','ink','bucket','square','rectangle','circle','ellipse'):
            btn = tk.Button(tools_tool, text=self.tools[tool])
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
        layers.geometry("250x%d" % self.config['height'])
        layers.protocol("WM_DELETE_WINDOW", lambda: self.close_window('layers'))

        self.layers_frame = tk.LabelFrame(layers, text="Warstwy")
        self.layers_frame.pack(expand=True)

        self.layers_up = ImageTk.PhotoImage(Image.open('./assets/up.png'))
        self.layers_down = ImageTk.PhotoImage(Image.open('./assets/down.png'))
        self.layers_cursor = ImageTk.PhotoImage(Image.open('./assets/cursor.png'))
        self.layers_cursor_disabled = ImageTk.PhotoImage(Image.open('./assets/cursor_disabled.png'))
        self.layers_visible = ImageTk.PhotoImage(Image.open('./assets/visible.png'))
        self.layers_visible_disabled = ImageTk.PhotoImage(Image.open('./assets/visible_disabled.png'))
        self.layers_rename = ImageTk.PhotoImage(Image.open('./assets/rename.png'))
        self.layers_remove = ImageTk.PhotoImage(Image.open('./assets/delete.png'))

        layers_tools = tk.LabelFrame(layers, text="Narzędzia")
        layers_tools.pack(expand=True)

        layers_tools_add = tk.Button(layers_tools, text="Dodaj warstwę", command=self.c_add_layer)
        layers_tools_add.pack()

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

        # Layer rename
        layer_rename = tk.Toplevel(self)
        layer_rename.wm_withdraw()
        layer_rename.wm_title('Zmień nazwę warstwy')
        layer_rename.geometry('300x180')
        layer_rename.protocol("WM_DELETE_WINDOW", lambda: self.close_window('layer_rename'))

        layer_rename_frame = tk.Frame(layer_rename)
        layer_rename_frame.pack(expand=True)

        self.layer_rename_entry_sv = tk.StringVar()
        self.layer_rename_entry = tk.Entry(layer_rename_frame, textvariable=self.layer_rename_entry_sv, width=30)
        self.layer_rename_entry.pack(pady=10)
        self.layer_rename_button = tk.Button(layer_rename_frame, text="Zmień")
        self.layer_rename_button.pack(pady=10)

        self.windows['layer_rename'] = layer_rename

        # Canvas resize
        canvas_resize = tk.Toplevel(self)
        canvas_resize.wm_withdraw()
        canvas_resize.wm_title('Zmień rozmiar płótna')
        canvas_resize.geometry('300x180')
        canvas_resize.protocol("WM_DELETE_WINDOW", lambda: self.close_window('canvas_resize'))

        canvas_resize_frame = tk.Frame(canvas_resize)
        canvas_resize_frame.pack(expand=True)

        self.canvas_resize_entry_w_sv = tk.StringVar()
        self.canvas_resize_entry_w = tk.Entry(canvas_resize_frame, textvariable=self.canvas_resize_entry_w_sv, width=30)
        self.canvas_resize_entry_w.pack(pady=10)
        self.canvas_resize_entry_h_sv = tk.StringVar()
        self.canvas_resize_entry_h = tk.Entry(canvas_resize_frame, textvariable=self.canvas_resize_entry_h_sv, width=30)
        self.canvas_resize_entry_h.pack(pady=10)
        self.canvas_resize_button = tk.Button(canvas_resize_frame, text="Zmień")
        self.canvas_resize_button.pack(pady=10)

        self.windows['canvas_resize'] = canvas_resize

        # Menu
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        fileMenu = tk.Menu(menubar)
        fileMenu.add_command(label="Nowy", command=self.c_new)
        fileMenu.add_command(label="Otwórz", command=lambda: self.c_open(
            filedialog.askopenfilename(title = "Otwórz plik",filetypes = (("pliki paint","*.paint"),("wszystkie pliki","*.*")))
        ))
        fileMenu.add_command(label="Zapisz", command=lambda: self.c_save(
            filedialog.asksaveasfilename(title = "Wybierz plik",filetypes = (("pliki paint","*.paint"),("wszystkie pliki","*.*")))
        ))
        fileMenu.add_command(label="Eksportuj", command=lambda: self.c_capture(
            filedialog.asksaveasfilename(title = "Wybierz plik",filetypes = (("pliki bmp","*.bmp"),("pliki jpeg","*.jpg"),("pliki png","*.png"),("pliki tga","*.tga"),("wszystkie pliki","*.*")))
        ))
        fileMenu.add_command(label="Wyjście", command=self.on_exit)
        menubar.add_cascade(label="Plik", menu=fileMenu)

        editMenu = tk.Menu(menubar)
        editMenu.add_command(label="Zmień rozmiar", command=self.c_prompt_resize)
        menubar.add_cascade(label="Edytuj", menu=editMenu)

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
        elif self.tool in ('rectangle', 'square','circle','ellipse','line'):
            self.c_shape_start(pos)
        elif self.tool == 'ink':
            self.c_set_color(self.c_get_color(pos))

    def c_use_tool(self, pos):
        if self.tool == 'brush':
            self.c_line(pos)

    def c_set_tool(self, tool):
        if self.locked:
            return 

        self.tool = tool
        if tool in ('rectangle','square','circle','ellipse','line'):
            self.c_shape_from = None

    def c_shape_start(self, pos):
        self.c_shape_from = pos

    def c_shape_stop(self, pos):
        if self.c_shape_from == None:
            return

        if self.tool == 'rectangle':
            pygame.draw.polygon(self.layer['surface'], self.c_color, [(self.c_shape_from[0],self.c_shape_from[1]),(pos[0],self.c_shape_from[1]),(pos[0],pos[1]),(self.c_shape_from[0],pos[1])])
        elif self.tool == 'square':
            w = self.c_shape_from[0] - pos[0]
            h = self.c_shape_from[1] - pos[1]
            wa, ha = abs(w), abs(h)
            if (w <= 0 and h <= 0) or (w > 0 and h > 0):
                if wa >= ha:
                    pygame.draw.polygon(self.layer['surface'], self.c_color, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]-w),(self.c_shape_from[0],self.c_shape_from[1]-w)])
                elif wa < ha:
                    pygame.draw.polygon(self.layer['surface'], self.c_color, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0],self.c_shape_from[1]-h),(self.c_shape_from[0]-h,self.c_shape_from[1]-h),(self.c_shape_from[0]-h,self.c_shape_from[1])])
            elif (w > 0 and h <= 0) or (w <= 0 and h > 0):
                if wa >= ha:
                    pygame.draw.polygon(self.layer['surface'], self.c_color, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]+w),(self.c_shape_from[0],self.c_shape_from[1]+w)])
                elif wa < ha:
                    pygame.draw.polygon(self.layer['surface'], self.c_color, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0],self.c_shape_from[1]-h),(self.c_shape_from[0]+h,self.c_shape_from[1]-h),(self.c_shape_from[0]+h,self.c_shape_from[1])])
        elif self.tool == 'circle':
            w = (pos[0] - self.c_shape_from[0]) // 2
            h = (pos[1] - self.c_shape_from[1]) // 2
            wa, ha = abs(w), abs(h)
            if (w <= 0 and h <= 0) or (w > 0 and h > 0):
                if wa < ha: w, wa = h, ha
                pygame.draw.circle(self.layer['surface'], self.c_color, (self.c_shape_from[0]+w, self.c_shape_from[1]+w), wa)    
            elif (w > 0 and h <= 0) or (w <= 0 and h > 0):
                if wa < ha: w, wa = -h, ha
                pygame.draw.circle(self.layer['surface'], self.c_color, (self.c_shape_from[0]+w, self.c_shape_from[1]-w), wa)
        elif self.tool == 'ellipse':
            w = pos[0] - self.c_shape_from[0]
            h = pos[1] - self.c_shape_from[1]
            wa, ha = abs(w), abs(h)
            x = self.c_shape_from[0] if w > 0 else self.c_shape_from[0] + w
            y = self.c_shape_from[1] if h > 0 else self.c_shape_from[1] + h
            pygame.draw.ellipse(self.layer['surface'], self.c_color, (x, y, wa, ha))     
        elif self.tool == 'line':
            pygame.draw.line(self.layer['surface'], self.c_color, self.c_shape_from, pos, self.c_size)     
        self.c_shape_from = None

    def c_point(self, pos):
        pygame.draw.circle(self.layer['surface'], self.c_color, pos, self.c_size//2)
        self.c_mouse_last = pos

    def c_line(self, pos):
        if self.c_size > 4:
            pygame.draw.circle(self.layer['surface'], self.c_color, pos, self.c_size//2)
        pygame.draw.line(self.layer['surface'], self.c_color, self.c_mouse_last, pos, self.c_size)
        self.c_mouse_last = pos

    def c_bucket(self, pos):
        d = 0.1
        self.c_bucket_replacing = self.layer['surface'].get_at(pos)

        if color_distance(self.c_bucket_replacing, self.c_color) > d:
            self.c_bucket_stack = [pos]
            self.c_bucket_visited = []

            self.c_bucket_calculating = True
            self.locked = True

    def c_bucket_progress(self):
        d = 0.1
        pxarray = pygame.PixelArray(self.layer['surface'])

        z = 0
        while z < 200 and len(self.c_bucket_stack) > 0:
            # TODO: Split this task into 2 subprocesses, first will stack.pop() and second will stack.shift()
            # https://docs.python.org/3/library/multiprocessing.html#sharing-state-between-processes
            pos = self.c_bucket_stack.pop()
            while pos in self.c_bucket_stack:
                self.c_bucket_stack.remove(pos)

            pxarray[pos[0], pos[1]] = self.c_color
            self.c_bucket_visited.append(pos)

            for i in [-1, 0, 1]:
                for j in [-1, 0, 1]:
                    if 0 <= pos[0]+i < pxarray.shape[0]:
                        if 0 <= pos[1]+j < pxarray.shape[1]:
                            if (pos[0]+i, pos[1]+j) in self.c_bucket_visited:
                                continue
                            if color_distance(self.layer['surface'].get_at((pos[0]+i, pos[1]+j)), self.c_bucket_replacing) <= d:
                                self.c_bucket_stack.append((pos[0]+i, pos[1]+j))
            z += 1

        self.c_bucket_visited = []

        if len(self.c_bucket_stack) == 0:
            self.c_bucket_calculating = False
            self.locked = False

    def c_set_color(self, color):
        if self.locked:
            return

        if color != None:
            if color not in self.c_colors.keys():
                self.c_colors[color] = hex_to_rgb(color)
            self.c_color = self.c_colors[color]

    def c_get_color(self, pos):
        r,g,b,_=self.layer['surface'].get_at(pos)
        return "#{0:02x}{1:02x}{2:02x}".format(max(0,min(r,255)),max(0,min(g,255)),max(0,min(b,255)))

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
                    self.c_set_color(h)
                    self.next_custom_color += 1
                    if self.next_custom_color == 8:
                        self.next_custom_color = 0
                    break
                i+=1

    def c_listening(self, value):
        self.listening = value

    def c_update(self):
        if self.c_bucket_calculating:
            self.c_bucket_progress()

        self.info_layer.fill((255,255,255,0))
        pos = pygame.mouse.get_pos()

        if self.listening and not self.locked:
            col = self.c_color if len(self.c_color) == 3 else (255,255,255)
                
            if self.tool == 'brush':
                pygame.draw.circle(self.info_layer,col, pos, self.c_size//2)

            if self.c_shape_from != None:
                if self.tool == 'rectangle':
                    pygame.draw.polygon(self.info_layer, col, [(self.c_shape_from[0],self.c_shape_from[1]),(pos[0],self.c_shape_from[1]),(pos[0],pos[1]),(self.c_shape_from[0],pos[1])])
                elif self.tool == 'square':  
                    w = self.c_shape_from[0] - pos[0]
                    h = self.c_shape_from[1] - pos[1]
                    wa, ha = abs(w), abs(h)
                    if (w <= 0 and h <= 0) or (w > 0 and h > 0):
                        if wa >= ha:
                            pygame.draw.polygon(self.info_layer, col, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]-w),(self.c_shape_from[0],self.c_shape_from[1]-w)])
                        elif wa < ha:
                            pygame.draw.polygon(self.info_layer, col, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0],self.c_shape_from[1]-h),(self.c_shape_from[0]-h,self.c_shape_from[1]-h),(self.c_shape_from[0]-h,self.c_shape_from[1])])
                    elif (w > 0 and h <= 0) or (w <= 0 and h > 0):
                        if wa >= ha:
                            pygame.draw.polygon(self.info_layer, col, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]),(self.c_shape_from[0]-w,self.c_shape_from[1]+w),(self.c_shape_from[0],self.c_shape_from[1]+w)])
                        elif wa < ha:
                            pygame.draw.polygon(self.info_layer, col, [(self.c_shape_from[0],self.c_shape_from[1]),(self.c_shape_from[0],self.c_shape_from[1]-h),(self.c_shape_from[0]+h,self.c_shape_from[1]-h),(self.c_shape_from[0]+h,self.c_shape_from[1])])
                elif self.tool == 'circle':
                    w = (pos[0] - self.c_shape_from[0]) // 2
                    h = (pos[1] - self.c_shape_from[1]) // 2
                    wa, ha = abs(w), abs(h)
                    if (w <= 0 and h <= 0) or (w > 0 and h > 0):
                        if wa < ha: w, wa = h, ha
                        pygame.draw.circle(self.info_layer, col, (self.c_shape_from[0]+w, self.c_shape_from[1]+w), wa)    
                    elif (w > 0 and h <= 0) or (w <= 0 and h > 0):
                        if wa < ha: w, wa = -h, ha
                        pygame.draw.circle(self.info_layer, col, (self.c_shape_from[0]+w, self.c_shape_from[1]-w), wa)  
                elif self.tool == 'ellipse':
                    w = pos[0] - self.c_shape_from[0]
                    h = pos[1] - self.c_shape_from[1]
                    wa, ha = abs(w), abs(h)
                    x = self.c_shape_from[0] if w > 0 else self.c_shape_from[0] + w
                    y = self.c_shape_from[1] if h > 0 else self.c_shape_from[1] + h
                    pygame.draw.ellipse(self.info_layer, col, (x, y, wa, ha))    
                elif self.tool == 'line':
                    pygame.draw.line(self.info_layer, col, self.c_shape_from, pos, self.c_size)    

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.pressed = True
                    self.c_use_tool_start(pos)
                elif event.type == pygame.MOUSEMOTION and self.pressed:
                    self.c_use_tool(pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.pressed = False
                    if self.tool in ('rectangle','square','circle','ellipse','line'):
                        self.c_shape_stop(pos)

        self.canvas.fill(pygame.Color(255, 255, 255))
        for i in range(len(self.layers)):
            if self.layers[i] != None and self.layers[i]['visible']:
                self.canvas.blit(self.layers[i]['surface'], (0,0))
                if i == self.layerID: 
                    self.canvas.blit(self.info_layer, (0,0))   
        pygame.display.update()
        self.statusbar.config(text="%s| %s| %s| %s| %s" % (
            "Narzędzie: {}".format(self.tools[self.tool]).ljust(self.config['status_spacing']), 
            "Grubość: {}px".format(self.c_size).ljust(self.config['status_spacing']),
            "Kolor: {}, {}, {}".format(self.c_color[0], self.c_color[1], self.c_color[2]).ljust(self.config['status_spacing']), 
            "Współrzędne: {}, {}".format(pos[0], pos[1]).ljust(self.config['status_spacing']),
            "Początek: {}, {}".format(*(self.c_shape_from[0], self.c_shape_from[1]) if self.c_shape_from != None else ('?','?')).ljust(self.config['status_spacing']), 
        ))
        self.master.after(1,self.c_update)

    def c_add_layer(self):
        if self.locked:
            return

        layer = pygame.Surface([self.config['cwidth'], self.config['cheight']], pygame.SRCALPHA, 32)
        layer.fill((255,255,255,0))
        i = len(self.layers)
        self.layerID = i
        self.layers.append({'name': 'Warstwa %d' % (self.layerID + 1), 'surface': layer, 'visible': True})
        self.layer = self.layers[self.layerID]

        up = tk.Button(self.layers_frame, image=self.layers_up, command=lambda: self.c_move_layer(i, -1))
        up.grid(row=self.layerID, column=0)

        down = tk.Button(self.layers_frame, image=self.layers_down, command=lambda: self.c_move_layer(i, +1))
        down.grid(row=self.layerID, column=1)

        text = tk.Label(self.layers_frame, text=self.layer['name'])
        text.grid(row=self.layerID, column=2)

        cursor = tk.Button(self.layers_frame, image=self.layers_cursor, command=lambda: self.c_open_layer(i))
        cursor.grid(row=self.layerID, column=3)

        visible = tk.Button(self.layers_frame, image=self.layers_visible, command=lambda: self.c_toggle_show_layer(i))
        visible.grid(row=self.layerID, column=4)

        rename = tk.Button(self.layers_frame, image=self.layers_rename, command=lambda: self.c_prompt_rename_layer(i))
        rename.grid(row=self.layerID, column=5)

        delete = tk.Button(self.layers_frame, image=self.layers_remove, command=lambda: self.c_delete_layer(i))
        delete.grid(row=self.layerID, column=6)

        self.layer['elements'] = [up, down, text, cursor, visible, rename, delete]

        self.c_cursor_layer()
        self.c_update_layers()

    def c_open_layer(self, id):
        if self.locked:
            return

        self.layerID = id
        self.layer = self.layers[self.layerID]
        self.c_cursor_layer()

    def c_cursor_layer(self):
        for i in range(len(self.layers)):
            if self.layers[i] != None:
                self.layers[i]['elements'][3].config(image=self.layers_cursor_disabled)
        self.layers[self.layerID]['elements'][3].config(image=self.layers_cursor)

    def c_toggle_show_layer(self, id):
        if self.layers[id]['visible']:
            self.layers[id]['elements'][4].config(image=self.layers_visible_disabled)
        else:
            self.layers[id]['elements'][4].config(image=self.layers_visible)
        self.layers[id]['visible'] = not self.layers[id]['visible']

    def c_prompt_rename_layer(self, id):
        self.layer_rename_entry_sv.set(self.layers[id]['name'])
        self.layer_rename_button.config(command=lambda: self.c_rename_layer(id, self.layer_rename_entry.get()))
        self.open_window('layer_rename')

    def c_rename_layer(self, id, value):
        self.close_window('layer_rename')
        self.layers[id]['name'] = value
        self.layers[id]['elements'][2].config(text=value)

    def c_move_layer(self, id, direction):
        while self.layers[id+direction] == None:
            direction += direction

        for i in range(len(self.layers[id+direction]['elements'])):
            if i == 0:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_move_layer(id, -1))
            elif i == 1:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_move_layer(id, +1))
            elif i == 3:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_open_layer(id))
            elif i == 4:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_toggle_show_layer(id))
            elif i == 5:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_prompt_rename_layer(id))
            elif i == 6:
                self.layers[id+direction]['elements'][i].config(command=lambda: self.c_delete_layer(id))
            self.layers[id+direction]['elements'][i].grid(row=id, column=i)
  
        for i in range(len(self.layers[id]['elements'])):
            if i == 0:
                self.layers[id]['elements'][i].config(command=lambda: self.c_move_layer(id+direction, -1))
            elif i == 1:
                self.layers[id]['elements'][i].config(command=lambda: self.c_move_layer(id+direction, +1))
            elif i == 3:
                self.layers[id]['elements'][i].config(command=lambda: self.c_open_layer(id+direction))
            elif i == 4:
                self.layers[id]['elements'][i].config(command=lambda: self.c_toggle_show_layer(id+direction))
            elif i == 5:
                self.layers[id]['elements'][i].config(command=lambda: self.c_prompt_rename_layer(id+direction))
            elif i == 6:
                self.layers[id]['elements'][i].config(command=lambda: self.c_delete_layer(id+direction))
            self.layers[id]['elements'][i].grid(row=id+direction, column=i)

        temp = self.layers[id+direction]
        self.layers[id+direction] = self.layers[id]
        self.layers[id] = temp

        if self.layerID == id:
            self.layerID = id+direction
        elif self.layerID == id+direction:
            self.layerID = id

        self.c_update_layers()

    def c_delete_layer(self, id):
        if self.c_len_layers() == 1 or self.locked:
            return

        for el in self.layers[id]['elements']:
            el.grid_forget()
        self.layers[id] = None

        if id == self.layerID:
            for i in range(len(self.layers)):
                if self.layers[i] != None:
                    self.c_open_layer(i)
                    break

        self.c_update_layers()

    def c_update_layers(self):
        cap = self.c_len_layers() - 1
        i = 0
        for layer in self.layers:
            if layer != None:
                if i == 0:
                    layer['elements'][0].config(state=tk.DISABLED)
                else:
                    layer['elements'][0].config(state=tk.NORMAL)
                if i == cap:
                    layer['elements'][1].config(state=tk.DISABLED)
                else:
                    layer['elements'][1].config(state=tk.NORMAL)
                i+=1

    def c_len_layers(self):
        l = 0
        for layer in self.layers:
            if layer != None:
                l += 1
        return l

    def c_prompt_resize(self):
        self.canvas_resize_entry_w_sv.set(self.config['cwidth'])
        self.canvas_resize_entry_h_sv.set(self.config['cheight'])
        self.canvas_resize_button.config(command=lambda: self.c_resize(int(self.canvas_resize_entry_w.get()), int(self.canvas_resize_entry_h.get())))
        self.open_window('canvas_resize')

    def c_resize(self, w, h):
        self.config['cwidth'] = w
        self.config['cheight'] = h
        self.embed.config(width=self.config['cwidth'], height=self.config['cheight'])
        self.canvas = pygame.display.set_mode((self.config['cwidth'], self.config['cheight']), pygame.RESIZABLE)
        for layer in self.layers:
            if layer != None:
                surface = pygame.Surface([self.config['cwidth'], self.config['cheight']], pygame.SRCALPHA, 32)
                surface.fill((255,255,255,0))
                surface.blit(layer['surface'], (0,0))
                layer['surface'] = surface

    def c_capture(self, filename):
        if filename != '':
            pygame.image.save(self.canvas, filename)

    def c_save(self, filename):
        if filename != '':
            file = "%dx%d\n" % (self.config['cwidth'], self.config['cheight'])
            for layer in self.layers:
                file += "{}\t{}\n".format(layer['name'], pygame.image.tostring(layer['surface'], 'RGBA'))
            with open(filename, "w") as paint_file:
                print(file, file=paint_file)

    def c_open(self, filename):
        if filename != '':
            with open(filename, "r") as paint_file:
                lines = paint_file.readlines() 
                w, h = re.search(r'(\d+)x(\d+)\n', lines[0]).groups()
                for layer in self.layers:
                    for el in layer['elements']:
                        el.grid_forget()
                self.layers = []
                self.c_resize(int(w), int(h))
                for line in lines[1:-1]:
                    name, surface_data = re.search(r'(.+)\t(b\'[^\']+\')', line).groups()
                    self.c_add_layer()
                    self.c_rename_layer(self.layerID, name)
                    self.layer['surface'].blit(pygame.image.fromstring(eval(surface_data), (self.config['cwidth'], self.config['cheight']), 'RGBA'), (0,0))

    def c_new(self):
        for layer in self.layers:
            for el in layer['elements']:
                el.grid_forget()
        self.layers = []
        self.c_add_layer()

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
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import image_slicer
import math
import os

class AppFatiadorImagens:
    def __init__(self, root):
        self.root = root
        self.root.title("Slicer Visual Pro - Navegação Avançada")
        self.root.geometry("1024x768")

        # --- Variáveis de Estado ---
        self.caminho_imagem = None
        self.imagem_original = None     # Imagem Full Resolution (na memória RAM)
        self.imagem_base_preview = None # Cópia redimensionada para base do zoom
        self.imagem_exibida = None      # Imagem atualmente no canvas (com zoom aplicado)
        self.tk_image = None            # Referência para o Garbage Collector do Tkinter
        
        self.scale = 1.0                # Escala atual de visualização
        self.tamanho_bloco = 1000       # Padrão solicitado: 1000px

        # --- Layout da Interface (GUI) ---
        
        # Frame de Controle (Topo)
        frame_controle = tk.Frame(root, padx=10, pady=10, bg="#2c3e50") # Cor mais "Pro"
        frame_controle.pack(fill=tk.X)

        btn_style = {"font": ("Segoe UI", 10), "bg": "#ecf0f1", "relief": "flat"}

        btn_abrir = tk.Button(frame_controle, text="📂 Abrir Imagem", command=self.carregar_imagem, **btn_style)
        btn_abrir.pack(side=tk.LEFT, padx=5)

        tk.Label(frame_controle, text="Tamanho do Corte (px):", bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=5)
        self.entrada_tamanho = tk.Entry(frame_controle, width=8)
        self.entrada_tamanho.insert(0, "1000")
        self.entrada_tamanho.pack(side=tk.LEFT)

        btn_grid = tk.Button(frame_controle, text="re-Renderizar Grid", command=self.atualizar_visualizacao, **btn_style)
        btn_grid.pack(side=tk.LEFT, padx=5)

        btn_fatiar = tk.Button(frame_controle, text="✂️ Fatiar e Salvar", command=self.fatiar_imagem, bg="#27ae60", fg="white", font=("Segoe UI", 10, "bold"))
        btn_fatiar.pack(side=tk.RIGHT, padx=5)

        self.lbl_info = tk.Label(frame_controle, text="Dica: Ctrl+Scroll para Zoom | Clique+Arrastar para Mover", bg="#2c3e50", fg="#bdc3c7", font=("Segoe UI", 9))
        self.lbl_info.pack(side=tk.LEFT, padx=20)

        # --- Área de Visualização (Canvas) ---
        self.canvas_frame = tk.Frame(root, bg="#333")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Removemos Scrollbars manuais pois usaremos o Pan (clicar e arrastar)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # --- Bindings (Eventos de Mouse/Teclado) ---
        self.canvas.bind("<ButtonPress-1>", self.start_pan) # Clique esquerdo segura
        self.canvas.bind("<B1-Motion>", self.do_pan)        # Mover mouse arrasta
        
        # Zoom no Windows
        self.canvas.bind("<Control-MouseWheel>", self.do_zoom_windows)
        # Zoom no Linux (geralmente mapeado para Button-4 e Button-5)
        self.canvas.bind("<Control-Button-4>", lambda event: self.do_zoom_linux(event, 1))
        self.canvas.bind("<Control-Button-5>", lambda event: self.do_zoom_linux(event, -1))

    def carregar_imagem(self):
        path = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg;*.jpeg;*.png;*.tif;*.tiff")])
        if not path:
            return

        self.caminho_imagem = path
        try:
            # 1. Carrega original
            self.imagem_original = Image.open(path)
            w_real, h_real = self.imagem_original.size
            self.lbl_info.config(text=f"Carregado: {w_real}x{h_real} px - Use Ctrl+Scroll para Zoom")

            # 2. Cria uma BASE de visualização. 
            # Limitamos a base a 2000px para garantir performance inicial, 
            # mas permitimos zoom a partir dela.
            base_width = 2000
            ratio = base_width / float(w_real)
            base_height = int(float(h_real) * float(ratio))
            
            self.imagem_base_preview = self.imagem_original.resize((base_width, base_height), Image.Resampling.LANCZOS)
            
            # Reset de escala
            self.scale = 1.0
            self.atualizar_visualizacao() # Desenha a imagem e o grid

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar: {str(e)}")

    def start_pan(self, event):
        """Marca o ponto inicial para arrastar a tela"""
        self.canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        """Move a tela baseado no movimento do mouse"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def do_zoom_windows(self, event):
        """Lógica de zoom para Windows (event.delta)"""
        # Delta positivo = Scroll Up (Zoom In), Negativo = Scroll Down (Zoom Out)
        if event.delta > 0:
            self.zoom(1.1) # Aumenta 10%
        else:
            self.zoom(0.9) # Diminui 10%

    def do_zoom_linux(self, event, direction):
        """Lógica de zoom para Linux"""
        if direction > 0:
            self.zoom(1.1)
        else:
            self.zoom(0.9)

    def zoom(self, factor):
        """Aplica o fator de zoom e redesenha"""
        if not self.imagem_base_preview:
            return
        
        # Limites de zoom (para não travar ou sumir)
        novo_scale = self.scale * factor
        if novo_scale < 0.1 or novo_scale > 10: 
            return

        self.scale = novo_scale
        self.atualizar_visualizacao()

    def atualizar_visualizacao(self):
        """Redesenha imagem e grid baseada na escala atual"""
        if not self.imagem_base_preview:
            return
            
        # 1. Calcular novo tamanho da imagem de visualização
        w_base, h_base = self.imagem_base_preview.size
        new_w = int(w_base * self.scale)
        new_h = int(h_base * self.scale)
        
        # 2. Redimensionar (Usamos NEAREST durante zoom para ser rápido)
        self.imagem_exibida = self.imagem_base_preview.resize((new_w, new_h), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.imagem_exibida)

        # 3. Limpar e desenhar Imagem
        self.canvas.delete("all")
        # Centralizar a imagem no canvas virtual seria ideal, mas anchor NW funciona bem
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        
        # 4. Desenhar Grid
        self.desenhar_grid_dinamico(new_w, new_h)
        
        # 5. Ajustar a área de rolagem do canvas
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def desenhar_grid_dinamico(self, w_view, h_view):
        """Calcula onde as linhas devem aparecer na visualização atual"""
        try:
            tamanho_bloco_real = int(self.entrada_tamanho.get())
        except ValueError:
            return

        w_real, h_real = self.imagem_original.size
        
        # A matemática mágica: Relação entre o Pixel Real e o Pixel na Tela
        # Ratio = Tamanho Atual na Tela / Tamanho Original Real
        ratio_x = w_view / w_real
        ratio_y = h_view / h_real

        # Desenhar linhas Verticais
        # Step é o tamanho do bloco ajustado para a tela
        step_x = tamanho_bloco_real * ratio_x
        step_y = tamanho_bloco_real * ratio_y

        # Loop otimizado: desenhamos apenas as linhas necessárias
        # Linhas Verticais
        x = step_x
        while x < w_view:
            self.canvas.create_line(x, 0, x, h_view, fill="#FFFF00", width=1, dash=(4, 4))
            x += step_x

        # Linhas Horizontais
        y = step_y
        while y < h_view:
            self.canvas.create_line(0, y, w_view, y, fill="#FFFF00", width=1, dash=(4, 4))
            y += step_y

    def fatiar_imagem(self):
        """Lógica de fatiamento (Mantida idêntica, pois opera no arquivo original)"""
        if not self.caminho_imagem: return
        try:
            tamanho_bloco = int(self.entrada_tamanho.get())
            w_real, h_real = self.imagem_original.size
            colunas = math.ceil(w_real / tamanho_bloco)
            linhas = math.ceil(h_real / tamanho_bloco)
            total_fatias = colunas * linhas

            if messagebox.askyesno("Confirmar", f"Gerar {total_fatias} fatias de aprox. {tamanho_bloco}px?"):
                output_dir = filedialog.askdirectory()
                if output_dir:
                    tiles = image_slicer.slice(self.caminho_imagem, total_fatias)
                    image_slicer.save_tiles(tiles, directory=output_dir, prefix='slice', format='png')
                    messagebox.showinfo("Sucesso", "Fatiamento concluído!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AppFatiadorImagens(root)
    root.mainloop()
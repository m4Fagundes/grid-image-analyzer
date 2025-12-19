import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import image_slicer
import math
import os

class AppFatiadorImagens:
    def __init__(self, root):
        self.root = root
        self.root.title("Slicer Visual - Ferramenta de Doutorado")
        self.root.geometry("1024x768")

        # --- Variáveis de Estado ---
        self.caminho_imagem = None
        self.imagem_original = None
        self.imagem_preview = None
        self.fator_escala = 1.0
        self.tamanho_bloco = 1000 

        # --- Layout da Interface (GUI) ---
        
        frame_controle = tk.Frame(root, padx=10, pady=10, bg="#f0f0f0")
        frame_controle.pack(fill=tk.X)

        btn_abrir = tk.Button(frame_controle, text="📂 Abrir Imagem", command=self.carregar_imagem, font=("Arial", 11, "bold"))
        btn_abrir.pack(side=tk.LEFT, padx=5)

        tk.Label(frame_controle, text="Tamanho do Corte (px):", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.entrada_tamanho = tk.Entry(frame_controle, width=10)
        self.entrada_tamanho.insert(0, "1000")
        self.entrada_tamanho.pack(side=tk.LEFT)

        btn_grid = tk.Button(frame_controle, text="👁️ Visualizar Grid", command=self.desenhar_grid)
        btn_grid.pack(side=tk.LEFT, padx=5)

        btn_fatiar = tk.Button(frame_controle, text="✂️ Fatiar e Salvar", command=self.fatiar_imagem, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
        btn_fatiar.pack(side=tk.RIGHT, padx=5)

        self.lbl_info = tk.Label(frame_controle, text="Nenhuma imagem carregada.", bg="#f0f0f0", fg="gray")
        self.lbl_info.pack(side=tk.LEFT, padx=20)

        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        v_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        h_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#333", 
                                yscrollcommand=v_scroll.set, 
                                xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=self.canvas.yview)
        h_scroll.config(command=self.canvas.xview)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def carregar_imagem(self):
        """Carrega a imagem e cria um preview leve para não travar o app"""
        path = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg;*.jpeg;*.png;*.tif;*.tiff")])
        if not path:
            return

        self.caminho_imagem = path
        
        try:
            # Carrega imagem original (Pode ser lenta se for gigante, mas necessária para o corte)
            self.imagem_original = Image.open(path)
            largura_real, altura_real = self.imagem_original.size
            
            # Atualiza info
            self.lbl_info.config(text=f"Original: {largura_real}x{altura_real} pixels | Arquivo: {os.path.basename(path)}")

            # Criar Thumbnail para o Canvas (limita visualização a max 1000px de largura para caber na tela)
            max_view_size = 1200
            ratio = min(max_view_size / largura_real, max_view_size / altura_real)
            
            # Se a imagem for menor que a tela, não reduz
            if ratio >= 1:
                self.fator_escala = 1.0
                nova_w, nova_h = largura_real, altura_real
            else:
                self.fator_escala = ratio
                nova_w = int(largura_real * ratio)
                nova_h = int(altura_real * ratio)

            # Redimensiona apenas para exibição (usando LANCZOS para qualidade)
            self.imagem_preview = self.imagem_original.resize((nova_w, nova_h), Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(self.imagem_preview)

            # Coloca no Canvas
            self.canvas.delete("all") # Limpa anterior
            self.canvas.config(scrollregion=(0, 0, nova_w, nova_h))
            self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir imagem: {str(e)}")

    def desenhar_grid(self):
        """Desenha as linhas de corte baseadas na entrada do usuário"""
        if not self.imagem_original:
            return

        self.canvas.delete("grid_line") # Remove linhas anteriores

        try:
            tamanho_corte_real = int(self.entrada_tamanho.get())
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um número válido para o tamanho do corte.")
            return

        w_real, h_real = self.imagem_original.size
        
        # Calcular linhas Verticais
        for x in range(0, w_real, tamanho_corte_real):
            x_view = int(x * self.fator_escala)
            # Desenha linha no canvas visual
            self.canvas.create_line(x_view, 0, x_view, int(h_real * self.fator_escala), fill="yellow", width=2, tags="grid_line")

        # Calcular linhas Horizontais
        for y in range(0, h_real, tamanho_corte_real):
            y_view = int(y * self.fator_escala)
            # Desenha linha no canvas visual
            self.canvas.create_line(0, y_view, int(w_real * self.fator_escala), y_view, fill="yellow", width=2, tags="grid_line")

    def fatiar_imagem(self):
        """Usa a biblioteca image-slicer para cortar"""
        if not self.caminho_imagem:
            return

        try:
            tamanho_bloco = int(self.entrada_tamanho.get())
            w_real, h_real = self.imagem_original.size
            
            # Cálculo matemático de quantas fatias são necessárias
            colunas = math.ceil(w_real / tamanho_bloco)
            linhas = math.ceil(h_real / tamanho_bloco)
            total_fatias = colunas * linhas

            resposta = messagebox.askyesno("Confirmar", f"A imagem será dividida em aproximadamente {total_fatias} arquivos.\nIsso pode levar um tempo. Continuar?")
            
            if resposta:
                # O image-slicer funciona por NUMERO de fatias, não por tamanho de pixel.
                # Precisamos usar a lógica do image_slicer.slice com o numero total calculado.
                # Nota: O image-slicer tenta fazer fatias iguais. Se a divisão não for exata, ele ajusta.
                
                output_dir = filedialog.askdirectory(title="Onde salvar as fatias?")
                if output_dir:
                    # Usando a biblioteca solicitada
                    tiles = image_slicer.slice(self.caminho_imagem, total_fatias)
                    
                    # Salvar as fatias no diretório escolhido
                    image_slicer.save_tiles(tiles, directory=output_dir, prefix='fatia', format='png')
                    
                    messagebox.showinfo("Sucesso", f"Processo concluído! {len(tiles)} fatias salvas em {output_dir}")

        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha ao fatiar: {str(e)}\n\nNota: Imagens extremamente grandes podem estourar a memória com esta biblioteca.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppFatiadorImagens(root)
    root.mainloop()
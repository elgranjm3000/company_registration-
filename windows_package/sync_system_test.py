#!/usr/bin/env python3
"""
TEST SIMPLE - Verificar que el .exe funciona
"""
import tkinter as tk
from tkinter import messagebox

def main():
    root = tk.Tk()
    root.title("Test - Sync System")
    root.geometry("400x200")

    label = tk.Label(root, text="✅ EL EJECUTABLE FUNCIONA\n\nEste es un test", font=("Arial", 16))
    label.pack(expand=True)

    def salir():
        messagebox.showinfo("Test", "El ejecutable funciona correctamente")
        root.destroy()

    btn = tk.Button(root, text="Click para probar", command=salir, font=("Arial", 12))
    btn.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    main()

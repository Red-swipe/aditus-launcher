import customtkinter as ctk

app = ctk.CTk()
app.geometry("800x600")

# Canvas background
canvas = ctk.CTkCanvas(app, bg="#212A3E", highlightthickness=0)
canvas.place(x=0, y=0, relwidth=1, relheight=1)

# Draw some dots
for x in range(0, 800, 30):
    for y in range(0, 600, 30):
        canvas.create_oval(x, y, x+2, y+2, fill="#394867", outline="")

# Add a frame
f = ctk.CTkFrame(app, fg_color="#394867", corner_radius=15)
f.place(relx=0.5, rely=0.5, anchor="center", width=400, height=300)

ctk.CTkLabel(f, text="Hello World", text_color="#F1F6F9").pack(pady=50)

app.after(3000, app.destroy)
app.mainloop()

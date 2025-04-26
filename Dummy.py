import os
import os.path as osp
import glob
import cv2
import numpy as np
import torch
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import RRDBNet_arch as arch

def process_image(path, grayscale, rotate_angle, resize_dims):
    # read image
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    
    if grayscale:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)  # Make it 3-channel again for ESRGAN
    
    if rotate_angle != 0:
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rotate_angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h))
    
    if resize_dims != (0, 0):
        img = cv2.resize(img, resize_dims, interpolation=cv2.INTER_LINEAR)

    img = img * 1.0 / 255
    img = torch.from_numpy(np.transpose(img[:, :, [2, 1, 0]], (2, 0, 1))).float()
    img_LR = img.unsqueeze(0)
    img_LR = img_LR.to(device)

    with torch.no_grad():
        output = model(img_LR).data.squeeze().float().cpu().clamp_(0, 1).numpy()
    
    output = np.transpose(output[[2, 1, 0], :, :], (1, 2, 0))
    output = (output * 255.0).round()
    
    return output

def select_and_process():
    file_path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
    if not file_path:
        return

    grayscale = messagebox.askyesno("Grayscale", "Do you want to convert the image to grayscale?")
    rotate_angle = simpledialog.askfloat("Rotate", "Enter rotation angle (0 for no rotation):", minvalue=-360, maxvalue=360) or 0
    resize_width = simpledialog.askinteger("Resize", "Enter new width (0 for no resize):", minvalue=0)
    resize_height = simpledialog.askinteger("Resize", "Enter new height (0 for no resize):", minvalue=0)
    resize_dims = (resize_width, resize_height) if resize_width and resize_height else (0, 0)

    output = process_image(file_path, grayscale, rotate_angle, resize_dims)
    
    base = osp.splitext(osp.basename(file_path))[0]
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    save_path = osp.join(output_dir, f"{base}_processed.png")
    cv2.imwrite(save_path, output)

    messagebox.showinfo("Done", f"Image processed and saved at:\n{save_path}")

# Load model
model_path = 'models/RRDB_ESRGAN_x4.pth'
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = arch.RRDBNet(3, 3, 64, 23, gc=32)
model.load_state_dict(torch.load(model_path), strict=True)
model.eval()
model = model.to(device)

# GUI
root = tk.Tk()
root.title("Image Preprocessing with ESRGAN")
root.geometry("400x200")

btn = tk.Button(root, text="Select Image and Process", command=select_and_process, font=("Arial", 14), padx=10, pady=10)
btn.pack(expand=True)

root.mainloop()

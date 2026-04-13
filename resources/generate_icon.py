"""
生成XLink应用图标
使用Pillow创建256x256的SSH终端图标
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    def create_icon():
        """创建ICO图标"""
        # 创建256x256的图像
        size = 256
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制黑色圆角矩形背景
        margin = 20
        radius = 30
        draw.rounded_rectangle(
            [margin, margin, size-margin, size-margin],
            radius=radius,
            fill=(30, 30, 30, 255)
        )
        
        # 绘制终端窗口边框
        border_margin = margin + 10
        draw.rounded_rectangle(
            [border_margin, border_margin, size-border_margin, size-border_margin],
            radius=15,
            fill=(50, 50, 50, 255),
            outline=(80, 80, 80, 255),
            width=3
        )
        
        # 绘制标题栏
        title_height = 40
        draw.rectangle(
            [border_margin, border_margin, size-border_margin, border_margin+title_height],
            fill=(60, 60, 60, 255)
        )
        
        # 绘制窗口控制按钮 (红、黄、绿)
        button_y = border_margin + 12
        button_size = 12
        button_spacing = 8
        
        # 红色按钮
        draw.ellipse(
            [border_margin+15, button_y, border_margin+15+button_size, button_y+button_size],
            fill=(255, 95, 86, 255)
        )
        
        # 黄色按钮
        draw.ellipse(
            [border_margin+15+button_size+button_spacing, button_y, 
             border_margin+15+button_size*2+button_spacing, button_y+button_size],
            fill=(255, 189, 46, 255)
        )
        
        # 绿色按钮
        draw.ellipse(
            [border_margin+15+(button_size+button_spacing)*2, button_y,
             border_margin+15+(button_size+button_spacing)*2+button_size, button_y+button_size],
            fill=(39, 201, 63, 255)
        )
        
        # 绘制绿色光标和提示符 ">_"
        try:
            # 尝试使用系统字体
            font_size = 60
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = ">_"
        text_color = (0, 255, 0, 255)  # 绿色
        
        # 计算文本位置 (居中)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (size - text_width) // 2
        text_y = (size - text_height) // 2 + 20
        
        draw.text((text_x, text_y), text, fill=text_color, font=font)
        
        # 保存为ICO文件 (多尺寸)
        output_path = os.path.join(os.path.dirname(__file__), 'xlink.ico')
        
        # 创建不同尺寸的版本
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        images = []
        
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)
        
        # 保存ICO
        images[0].save(
            output_path,
            format='ICO',
            sizes=[(s[0], s[1]) for s in sizes],
            append_images=images[1:]
        )
        
        print(f"Icon generated successfully: {output_path}")
        return True
    
    if __name__ == '__main__':
        create_icon()

except ImportError:
    print("Pillow not installed. Install with: pip install Pillow")
    print("Creating placeholder icon...")
    
    # 创建一个简单的占位图标
    import struct
    
    def create_placeholder_icon():
        """创建简单的占位ICO"""
        output_path = os.path.join(os.path.dirname(__file__), 'xlink.ico')
        
        # 最简单的16x16 ICO
        # ICO Header
        header = struct.pack('<HHH', 0, 1, 1)  # Reserved, Type(1=ICO), Count
        
        # ICO Directory Entry
        width = 16
        height = 16
        colors = 0
        reserved = 0
        planes = 1
        bpp = 32
        size = width * height * 4 + 40  # RGBA + BITMAPINFOHEADER
        offset = 6 + 16  # Header + Directory
        
        directory = struct.pack('<BBBBHHII', 
                               width, height, colors, reserved,
                               planes, bpp, size, offset)
        
        # BITMAPINFOHEADER
        bmp_header = struct.pack('<IiiHHIIiiII',
                                40, width, height*2, 1, 32,
                                0, 0, 0, 0, 0, 0)
        
        # Pixel data (black background with green >_)
        pixels = b''
        for y in range(height):
            for x in range(width):
                if 4 <= x <= 6 and 6 <= y <= 9:  # > symbol
                    pixels += b'\x00\xff\x00\xff'  # Green
                elif 8 <= x <= 9 and 7 <= y <= 8:  # _ symbol
                    pixels += b'\x00\xff\x00\xff'  # Green
                else:
                    pixels += b'\x1e\x1e\x1e\xff'  # Dark background
        
        with open(output_path, 'wb') as f:
            f.write(header)
            f.write(directory)
            f.write(bmp_header)
            f.write(pixels)
        
        print(f"Placeholder icon created: {output_path}")
    
    import os
    create_placeholder_icon()

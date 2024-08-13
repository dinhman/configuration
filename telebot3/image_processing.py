from PIL import Image, ImageFont, ImageDraw
import os
from config import SMS_font, SMS_Wartermark_font

def create_sms_image(result, search_value, template):
    """Create an SMS image based on the provided template."""
    image_size = (500, 450)  
    if template == 2:
        image_size = (500, 265)
    elif template == 3:
        image_size = (500, 440)
    elif template == 4:
        image_size = (500, 800)

    SMS_img = Image.new('RGB', image_size)
    SMS_draw = ImageDraw.Draw(SMS_img)

    SMS_wartermark = result['CrmUser'][0]
    SMS_draw.text((20, 50), SMS_wartermark, font=SMS_Wartermark_font, fill=(0, 65, 0, 30))
    SMS_draw.text((20, 160), SMS_wartermark, font=SMS_Wartermark_font, fill=(0, 65, 0, 30))
    SMS_draw.text((20, 350), SMS_wartermark, font=SMS_Wartermark_font, fill=(65, 0, 0, 30))

    SMS_text = result['SMS'][0].replace('\r\n', '\n')
    SMS_draw.text((10, 20), SMS_text, font=SMS_font)

    full_path = os.path.join('Output', f'{search_value}_SMS{template}.jpg')
    SMS_img.save(full_path)
    return full_path

import os
import pandas as pd
from zipfile import ZipFile
import shutil
from pathlib import Path
from skpy import Skype, SkypeEventLoop, SkypeNewMessageEvent, SkypeContacts
# import pyodbc
import paramiko
import re
from PIL import Image, ImageDraw, ImageFont
import stat
from dotenv import load_dotenv
import pymssql
from docx import Document
from docx2pdf import convert
import glob
from sqlalchemy import create_engine
from skpy.core import SkypeApiException  # Import SkypeApiException

# from sendFile import send_to_user
# # -------------------------------------------------------------------

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# -------------------------------------------------------------------
#font_path = "/usr/share/fonts/truetype/Tahoma.ttf"
# Load environment variables from .env file
load_dotenv()

# Accessing environment variables
myLocalDBConn = os.getenv('LOCAL_DB_CONN')
sftp_host = os.getenv('SFTP_HOST')
sftp_port = os.getenv('SFTP_PORT')
sftp_user = os.getenv('SFTP_USER')
sftp_password = os.getenv('SFTP_PASSWORD')
skype_user = os.getenv('SKYPE_USER')
skype_password = os.getenv('SKYPE_PWD')
skype_group = os.getenv('SKYPE_GROUP')

# Database connection information
db_server = os.getenv('DB_SERVER')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
if not all([db_server, db_user, db_password, db_name]):
    raise ValueError("One or more database connection environment variables are not set.")

#-----------------------------------------------------------------


class SkypeListener(SkypeEventLoop):
    """ Listen to Skype events continuously """


    def __init__(self):

        super().__init__(skype_user, skype_password)

        #LOANEID Pattern:
        self.LOANEID_pattern = re.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')
        #GetInfo Pattern:
        self.GetInfo_pattern = re.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        
        #Group Setup: 
        self.Group_ID = skype_group
        self.Group = self.chats[self.Group_ID]
        self.Group.sendMsg("Hello ! I'm Listening...")

        
        #GetSms Pattern
        self.GetSms_pattern = re.compile(r'^getsms[123]\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        # self.GetSms_pattern = re.compile(r'^(getinfo|getsms[123])\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        
        #SmsTemplate parrtern
        self.SMStemplate_pattern = re.compile('^getsms[123]')
       
        #DK pattern
        self.GetDK_pattern = re.compile(r'^tbkk\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        
        #Font settup
        self.SMS_font = ImageFont.truetype("tahoma.ttf", 14)
        self.SMS_Wartermark_font = ImageFont.truetype("tahoma.ttf", 34)


    def onEvent(self, event):

        if isinstance(event, SkypeNewMessageEvent):
            try:
                message = {"user_id": event.msg.userId,
                        "chat_id": event.msg.chatId,
                        "msg": event.msg.content}

                
                if message["chat_id"] == self.Group_ID:

                    print(message)
                    if self.GetInfo_pattern.match(message["msg"].lower()) != None:

                        SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                        if SearchValue != None:
                            # Kết nối đến cơ sở dữ liệu sử dụng pymssql
                            conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name)

                            self.Group.sendMsg(
                                '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))

                            result = pd.read_sql_query("""
                                    EXEC [localDB].[dbo].[SkypeGetInfo]
                                    @userName = '{}'
                                    ,@Domain = '{}'
                                    ,@SearchKey = {}
                                    ,@SearchValue = '{}'
                                """.format(message["user_id"], 'Inhouse', 1, SearchValue)
                            , conn)


                            rowCount = result['ID'].count()
                            conn.close()

                            if rowCount == 0:
                                # print('Status: "{}" not found'.format(SearchValue))
                                self.Group.sendMsg('@{}: Không tìm thấy hợp đồng "{}"'.format(message["user_id"], SearchValue))
                            else:
                                # print('Path: {}'.format(result["Path"][0]))

                                destinationPath = os.path.join(r"output", SearchValue)

                                if os.path.exists(destinationPath):
                                    shutil.rmtree(destinationPath)

                                Path(destinationPath).mkdir(
                                    parents=True
                                    # ,exist_ok=True
                                )

                                ssh.connect(sftp_host, sftp_port, sftp_user, sftp_password)
                                sftp = ssh.open_sftp()

                                #             # shutil.copy(sourcePath, destinationPath)
                                for path in result["Path"]:
                                    temp = sftp.lstat(path)
                                    if stat.S_ISDIR(temp.st_mode):
                                        for file in sftp.listdir(path):
                                            # shutil.copy(os.path.join(result["Path"], file), destinationPath)
                                            fullSourcePath = path + '/' + file
                                            fullDestPath = destinationPath + '//' + file
                                            sftp.get(fullSourcePath, fullDestPath)
                                            print(fullSourcePath, '-', fullDestPath)
                                    else:
                                        fullSourcePath = path
                                        fullDestPath = destinationPath + '//' + os.path.basename(path)
                                        sftp.get(fullSourcePath, fullDestPath)
                                        print(fullSourcePath, '-', fullDestPath)

                                ssh.close

                                with ZipFile(os.path.join(r"./output", SearchValue + '.zip'), 'w') as zipObj:
                                    for folderName, subfolders, filenames in os.walk(destinationPath):
                                        for filename in filenames:
                                            # create complete filepath of file in directory
                                            filePath = os.path.join(folderName, filename)
                                            # Add file to zip
                                            zipObj.write(filePath, os.path.basename(filePath))

                                zipObj.close()

                                fullPath = os.path.join(r"./output", SearchValue + '.zip')
                                fileName = os.path.basename(fullPath)

                                try:
                                    sent2User = self.contacts[event.msg.userId].chat  # Access the chat of the user
                                    with open(fullPath, "rb") as file:
                                        sent2User.sendFile(file, fileName, image=False)  # Upload and send the file
                                        self.Group.sendMsg(f'@{event.msg.userId}: Hợp đồng "{SearchValue}" đã được gửi cho bạn')

                                except KeyError:
                                    print("Oops! Check your contacts & try again...")
                                    self.Group.sendMsg("There was an error sending the file. Please check the contact and try again.")


                    elif self.GetSms_pattern.match(message["msg"].lower()) != None:
                        SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                        Template = self.SMStemplate_pattern.search(message["msg"].lower()).group()[-1]
                        if SearchValue != None:
                            self.Group.sendMsg(
                                '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))

                            conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name)

                            result = pd.read_sql_query("""
                                EXEC [localDB].[dbo].[SkypeGetSMS]
                                    @SkypeId = '{}'
                                    ,@SkypeGroup = '{}'
                                    ,@SearchValue = '{}'
                                    ,@Template = {}
                                """.format(message["user_id"], message["chat_id"], SearchValue, Template)
                                                        ,conn)

                            conn.close()

                            rowCount = result['Active'].count()


                            if rowCount == 0:
                                self.Group.sendMsg(
                                    'Không tìm thấy hợp đồng "{}"/ Bạn chưa có quyền sử dụng tính năng này'.format(SearchValue))
                            else:
                                if result['UserPermission'][0] == 0:
                                    self.Group.sendMsg(
                                        'Không tìm thấy hợp đồng "{}"/ Bạn chưa có quyền sử dụng tính năng này'.format(SearchValue))
                                    
                                if result['Active'][0] == 0:
                                    self.Group.sendMsg(
                                        'Hợp đồng này đã tất toán')
                                elif ('Inhouse' not in result['AssignedTo'][0] \
                                        and 'Manual' not in result['AssignedTo'][0] \
                                        and 'notAssign' not in result['AssignedTo'][0] \
                                        and 'Waive' not in result['AssignedTo'][0]\
                                        and result['AssignedTo'][0] != 'AiRudder' \
                                        and result['AssignedTo'][0] != 'MFI Potential' \
                                        and result['AssignedTo'][0] != 'Legal Collection'\
                                        and result['AssignedTo'][0] != 'MFI Skip Work' \
                                        and result['AssignedTo'][0] != 'Bank Skip Work' \
                                        and result['AssignedTo'][0] != 'Bank Facebook'\
                                        and result['AssignedTo'][0] != 'Bank Zalo' \
                                        and result['AssignedTo'][0] != 'Additional_Bank'\
                                        and result['AssignedTo'][0] != 'Additional_MFI' \
                                        and result['AssignedTo'][0] != 'MFI Facebook' \
                                        and result['AssignedTo'][0] != 'Low balance' \
                                        and result['AssignedTo'][0] != 'Low_Balance1' \
                                        and 'RBC' not in result['AssignedTo'][0]\
                                        ):
                                    self.Group.sendMsg(
                                        'Hợp đồng này hiện tại không được phân công cho Inhouse')
                                else:

                                    if Template == '1':
                                        SMS_img = Image.new('RGB', (500, 450))
                                    elif Template == '2':
                                        SMS_img = Image.new('RGB', (500, 265))
                                    elif Template == '3':
                                        SMS_img = Image.new('RGB', (500, 440))
                                    else:
                                        SMS_img = Image.new('RGB', (500, 800))

                                    SMS_draw = ImageDraw.Draw(SMS_img)

                                    SMS_Wartermark = result['CrmUser'][0]
                                    SMS_draw.text((20, 50), SMS_Wartermark, font=self.SMS_Wartermark_font,
                                                    fill=(0, 65, 0, 30))
                                    SMS_draw.text((20, 160), SMS_Wartermark, font=self.SMS_Wartermark_font,
                                                    fill=(0, 65, 0, 30))
                                    SMS_draw.text((20, 350), SMS_Wartermark, font=self.SMS_Wartermark_font,
                                                    fill=(65, 0, 0, 30))

                                    SMS_text = result['SMS'][0].replace('\r\n', '\n')
                                    # print(SMS_text)
                                    SMS_draw.text((10, 20), SMS_text, font=self.SMS_font)
                                    # SMS_img = SMS_img.rotate(270, expand=True)

                                    fullPath = os.path.join(r"./output", SearchValue + '_SMS' + Template + '.jpg')
                                    fileName = os.path.basename(fullPath)

                                    SMS_img.save(fullPath)

                                    try:
                                        sent2User = self.contacts[message["user_id"]].chat

                                        sent2User.sendFile(open(fullPath, "rb"), fileName, image=True)  # file upload


                                    except ValueError:
                                        print("Oops! Check your contacts & try again...")

                                    self.Group.sendMsg(
                                        'Tin nhắn mẫu đã được gửi cho bạn')

                    elif self.GetDK_pattern.match(message["msg"].lower()) != None:
                        SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                        print(SearchValue)
                        if SearchValue != None:

                            self.Group.sendMsg(
                                '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))

                            conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name)

                            result = pd.read_sql_query("""                                                 
                                    EXEC [localDB].[dbo].[SkyGetPdf]
                                    @userName = '{}'
                                    ,@SearchValue = '{}'
                                """.format(message["user_id"], SearchValue)
                            , conn)

                            conn.close()

                            rowCount = result['Number'].count()

                            if rowCount == 0:

                                self.Group.sendMsg(
                                    'Không tìm thấy hợp đồng "{}"/ Bạn chưa có quyền sử dụng tính năng này'.format(SearchValue))
                            else:

                                    output_folder_path = r".\pdf_files"
                                    word_file_path = "template_PDF.docx"
                                    template = Document(word_file_path)


                                    for paragraph in template.paragraphs:
                                        if '{{Number}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Number}}', str(result['Number'].iloc[0]))
                                        if '{{Current_day}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Current_day}}',
                                                                                str(result['Current_day'].iloc[0]))
                                        if '{{Current_month}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Current_month}}',
                                                                                str(result['Current_month'].iloc[0]))
                                        if '{{Client_name}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Client_name}}',
                                                                                str(result['Client_name'].iloc[0]))
                                        if '{{Passport}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Passport}}', str(result['Passport'].iloc[0]))
                                        if '{{Address}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Address}}', str(result['Address'].iloc[0]))
                                        if '{{Ngay_vay}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Ngay_vay}}', str(result['Ngay_vay'].iloc[0]))
                                        if '{{Company_name}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Company_name}}',
                                                                                str(result['Company_name'].iloc[0]))
                                        if '{{DPD}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{DPD}}', str(int(result['DPD'].iloc[0])))
                                        if '{{Current_day_1}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Current_day_1}}',
                                                                                str(result['Current_day_1'].iloc[0]))
                                        if '{{Total_debt}}' in paragraph.text:
                                            paragraph.text = paragraph.text.replace('{{Total_debt}}',
                                                                                str(result['Total_debt'].iloc[0].replace(",",
                                                                                                                        ".")))
                                        temp_word_file_path = os.path.join(output_folder_path,
                                                                    f'{str(result["Number_1"].iloc[0])}.docx')
                                        template.save(temp_word_file_path)

                                    word_files_path = r".\pdf_files\*.docx"
                                    word_files = glob.glob(word_files_path)

                                    for word_file_path in word_files:

                                        convert(word_file_path, output_folder_path)


                                        os.remove(word_file_path)

                                    fullPath = os.path.join(r".\pdf_files", SearchValue.upper() + '.pdf')
                                    fileName = os.path.basename(fullPath)

                                    try:
                                        sent2User = self.contacts[message["user_id"]].chat

                                        sent2User.sendFile(open(fullPath, "rb"), fileName, image=False)  # file upload
                                        self.Group.sendMsg(
                                            '@{}: Thông báo KK "{}" đã được gửi cho bạn'.format(message["user_id"], SearchValue))
                                        


                                    except ValueError:
                                        print("Oops! Check your contacts & try again...")
                        else:
                            self.Group.sendMsg(
                                'Không có quyền truy cập !')


            except SkypeApiException as e:
                if e.args[0] == 403:
                    print("Lỗi 403: Bạn không có quyền truy cập hoặc thông tin đăng nhập không hợp lệ.")
                    if self.Group:
                        self.Group.sendMsg("Bạn chưa thêm liên hệ với Bot. Vui lòng thêm liên hệ với Bot trước.")
                else:
                    print(f"SkypeApiException: {e}")
                    if self.Group:
                        #self.Group.sendMsg(f"Lỗi: {e}")
                        self.Group.sendMsg("Bạn chưa thêm liên hệ với Bot. Vui lòng thêm liên hệ với Bot trước.")

            except Exception as e:
                print(f"Lỗi không xác định: {e}")
                if self.Group:
                    self.Group.sendMsg(f"Đã xảy ra lỗi: {e}")
                                            
            

# ----START OF SCRIPT
if __name__ == "__main__":
    SkypeGetInfo = SkypeListener()
    print("I'm Lisenting")
    SkypeGetInfo.loop()

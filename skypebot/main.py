import os
import pandas as pd
from zipfile import ZipFile
import shutil
from pathlib import Path
import credentials
import base64
# from skpy import Skype
from skpy import SkypeEventLoop, SkypeNewMessageEvent
import pyodbc
import paramiko
import re
from PIL import Image, ImageDraw, ImageFont
import stat

# -------------------------------------------------------------------

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# -------------------------------------------------------------------


class SkypeListener(SkypeEventLoop):
    """ Listen to a channel continuously """

    def __init__(self):
        username = credentials.skypeUser
        password = base64.b64decode(credentials.skypePassword).decode("utf-8")
        token_file = '.tokens-app'
        super(SkypeListener, self).__init__(username, password, token_file)

        self.LOANEID_pattern = re.compile(r'((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+')

        self.VID_Something_chatId = '19:87e759e121ac4a37881df996a0cb3015@thread.skype'
        self.VID_Something_Group = self.chats[self.VID_Something_chatId]
        self.GetInfo_pattern = re.compile(r'^getinfo\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        # self.GetInfo_pattern = re.compile(r'^getinfo\s+((mir)|(atm)|(sen))\d+\s*$')

        self.SMS_Zalo_Face_chatId = '19:c93da469a0ac4697a22f9264ad605c40@thread.skype'
        self.SMS_Zalo_Face_Group = self.chats[self.SMS_Zalo_Face_chatId]
        self.GetSMS_pattern = re.compile(r'^getsms[123]\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')
        self.SMStemplate_pattern = re.compile('^getsms[123]')

        self.VID_DataUpdate_chatId = '19:c026dfb7ba81465fabd3ac15ae0da3d8@thread.skype'
        self.VID_DataUpdate_Group = self.chats[self.VID_DataUpdate_chatId]
        self.GetData_pattern = re.compile(r'^getdata\s+((mir)|(vcr)|(ocr)|(atm)|(sen)|(mnc)|(dcr)|(mnv)|(shi)|(tkm))\d+\s*$')

        self.SMS_font = ImageFont.truetype("Tahoma.ttf", 14)
        self.SMS_Wartermark_font = ImageFont.truetype("Tahoma.ttf", 34)

    def onEvent(self, event):
        # for request in self.contacts.requests():
        #     request.accept()

        if isinstance(event, SkypeNewMessageEvent):
            message = {"user_id": event.msg.userId,
                       "chat_id": event.msg.chatId,
                       "msg": event.msg.content}
            #print(message["chat_id"])
            if message["chat_id"] == self.VID_Something_chatId:
            #if message["chat_id"] == "abc":
                print(message)
                if self.GetInfo_pattern.match(message["msg"].lower()) != None:

                    SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                    if SearchValue != None:
                        myDBconn = pyodbc.connect(credentials.myLocalDBConn)

                        # print('\nRequested:', message["user_id"], '-', message["chat_id"], '-', message["msg"])
                        self.VID_Something_Group.sendMsg(
                            '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))

                        result = pd.read_sql_query("""
                                EXEC [localDB].[dbo].[SkypeGetInfo]
                                @userName = '{}'
                                ,@Domain = '{}'
                                ,@SearchKey = {}
                                ,@SearchValue = '{}'
                            """.format(message["user_id"], 'Inhouse', 1, SearchValue)
                        , myDBconn)

                        myDBconn.commit()
                        myDBconn.close()

                        rowCount = result['ID'].count()

                        if rowCount == 0:
                            # print('Status: "{}" not found'.format(SearchValue))
                            self.VID_Something_Group.sendMsg('@{}: Không tìm thấy hợp đồng "{}"'.format(message["user_id"], SearchValue))
                        else:
                            # print('Path: {}'.format(result["Path"][0]))

                            destinationPath = os.path.join(r"Output", SearchValue)

                            if os.path.exists(destinationPath):
                                shutil.rmtree(destinationPath)

                            Path(destinationPath).mkdir(
                                parents=True
                                # ,exist_ok=True
                            )

                            ssh.connect(
                                credentials.sftpHost,
                                credentials.sftpPort,
                                "nguyen.dao",
                                "rYCtjDzpJ5Weh5O"
                               # credentials.sftpUser,
                                #base64.b64decode(credentials.sftpPassword).decode("utf-8")
                            )
                            sftp = ssh.open_sftp()

                            #             # shutil.copy(sourcePath, destinationPath)
                            for path in result["Path"]:
                                temp = sftp.lstat(path)
                                if stat.S_ISDIR(temp.st_mode):
                                    for file in sftp.listdir(path):
                                        # shutil.copy(os.path.join(result["Path"], file), destinationPath)
                                        fullSourcePath = path + '/' + file
                                        fullDestPath = destinationPath + '\\' + file
                                        sftp.get(fullSourcePath, fullDestPath)
                                        print(fullSourcePath, '-', fullDestPath)
                                else:
                                    fullSourcePath = path
                                    fullDestPath = destinationPath + '\\' + os.path.basename(path)
                                    sftp.get(fullSourcePath, fullDestPath)
                                    print(fullSourcePath, '-', fullDestPath)

                            ssh.close

                            with ZipFile(os.path.join(r".\Output", SearchValue + '.zip'), 'w') as zipObj:
                                for folderName, subfolders, filenames in os.walk(destinationPath):
                                    for filename in filenames:
                                        # create complete filepath of file in directory
                                        filePath = os.path.join(folderName, filename)
                                        # Add file to zip
                                        zipObj.write(filePath, os.path.basename(filePath))

                            zipObj.close()

                            fullPath = os.path.join(r".\Output", SearchValue + '.zip')
                            fileName = os.path.basename(fullPath)

                            try:
                                sent2User = self.contacts[message["user_id"]].chat

                                # sent2User = sk.contacts[msg.userId].chat
                                # sent2User.sendMsg('test Msg')

                                sent2User.sendFile(open(fullPath, "rb"), fileName, image=False)  # file upload
                                self.VID_Something_Group.sendMsg('@{}: Hợp đồng "{}" đã được gửi cho bạn'.format(message["user_id"], SearchValue))

                            except ValueError:
                                print("Oops! Check your contacts & try again...")

            elif message["chat_id"] == self.SMS_Zalo_Face_chatId:
                if self.GetSMS_pattern.match(message["msg"].lower()) != None:
                    SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                    Template = self.SMStemplate_pattern.search(message["msg"].lower()).group()[-1]
                    if SearchValue != None:
                        # print(SearchValue)
                        # print(message.userId)
                        # print(message.chatId)
                        # print(message.userId)
                        self.SMS_Zalo_Face_Group.sendMsg(
                            '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))

                        myDBconn = pyodbc.connect(credentials.myLocalDBConn)
                        result = pd.read_sql_query("""
                            EXEC [localDB].[dbo].[SkypeGetSMS]
                                @SkypeId = '{}'
                                ,@SkypeGroup = '{}'
                                ,@SearchValue = '{}'
                                ,@Template = {}
                            """.format(message["user_id"], message["chat_id"], SearchValue, Template)
                                                       , myDBconn)

                        myDBconn.commit()
                        myDBconn.close()

                        rowCount = result['Active'].count()
                        if rowCount == 0:
                            self.SMS_Zalo_Face_Group.sendMsg(
                                'Không tìm thấy hợp đồng "{}"/ Bạn chưa có quyền sử dụng tính năng này'.format(SearchValue))
                        else:
                            if result['UserPermission'][0] == 0:
                                self.SMS_Zalo_Face_Group.sendMsg(
                                    'Không tìm thấy hợp đồng "{}"/ Bạn chưa có quyền sử dụng tính năng này'.format(SearchValue))
                            elif result['Active'][0] == 0:
                                self.SMS_Zalo_Face_Group.sendMsg(
                                    'Hợp đồng này đã tất toán')
                            # elif result['AssignedTo'][0] != 'Inhouse':
                            # elif result['AssignedTo'][0] != 'Inhouse' and result['AssignedTo'][0] != 'ManualCallJune' and result['AssignedTo'][0] != 'ManualCallJuly':
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
                                self.SMS_Zalo_Face_Group.sendMsg(
                                    'Hợp đồng này hiện tại không được phân công cho Inhouse')
                            else:
                                # sent2User = self.contacts[message["user_id"]].chat
                                # sent2User.sendMsg(result['SMS'][0])

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

                                fullPath = os.path.join(r".\Output", SearchValue + '_SMS' + Template + '.jpg')
                                fileName = os.path.basename(fullPath)

                                SMS_img.save(fullPath)

                                try:
                                    sent2User = self.contacts[message["user_id"]].chat

                                    # sent2User = sk.contacts[msg.userId].chat
                                    # sent2User.sendMsg('test Msg')

                                    sent2User.sendFile(open(fullPath, "rb"), fileName, image=True)  # file upload


                                except ValueError:
                                    print("Oops! Check your contacts & try again...")

                                self.SMS_Zalo_Face_Group.sendMsg(
                                    'Tin nhắn mẫu đã được gửi cho bạn')

            elif message["chat_id"] == self.VID_DataUpdate_chatId:
                if self.GetData_pattern.match(message["msg"].lower()) != None:

                    SearchValue = self.LOANEID_pattern.search(message["msg"].lower()).group()
                    if SearchValue != None:
                        myDBconn = pyodbc.connect(credentials.myLocalDBConn)
                        self.VID_DataUpdate_Group.sendMsg(
                            '@{}: Yêu cầu của bạn đang được xử lí'.format(message["user_id"]))
                        result = pd.read_sql_query("""
                                                        EXEC [localDB].[dbo].[SkypeGetDataUpdate]
                                                            @SearchValue = '{}'
                                                            """.format(SearchValue), myDBconn)

                        myDBconn.commit()
                        myDBconn.close()
                        if result['data'].size > 0:
                            resultData = ''
                            for record in result['data']:
                                resultData = resultData + record.replace('\r\n', '\n')
                            # resultData = resultData.replace('"', '')
                            # fullPath = os.path.join(r".\Output", SearchValue + '_data.csv')
                            # print(fullPath)
                            # fileName = os.path.basename(fullPath)
                            # f = open(fullPath, "w+", encoding='utf-8')
                            # f.write('\ufeff')
                            # f.writelines("{}".format(resultData))
                            # f.close()

                            try:
                                sent2User = self.contacts[message["user_id"]].chat
                                sent2User.sendMsg(resultData)

                                # sent2User.sendFile(open(fullPath, "rb"), fileName, image=False)  # file upload
                                self.VID_DataUpdate_Group.sendMsg(
                                    'Thông tin hợp đồng đã được gửi cho bạn')
                            except ValueError:
                                print("Oops! Check your contacts & try again...")
                        else:
                            self.VID_DataUpdate_Group.sendMsg(
                                'Không tìm thấy thông tin hợp đồng')




# ----START OF SCRIPT
if __name__ == "__main__":
    SkypeGetInfo = SkypeListener()
    print("Hello")
    SkypeGetInfo.loop()

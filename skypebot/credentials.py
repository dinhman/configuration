#  Skype

skypeUser = "mmkhoavid@outlook.com"
skypePassword = "QWExMjM0NTY3OTg="

# ---------------------------------------------

# Databse

# myLocalDBConn = """
#     Driver={SQL Server};
#     Server=MSI\SQLEXPRESS;
#     Database=myLocalDB;
#     Trusted_Connection=yes;
# """

#myLocalDBConn = """
#    Driver={SQL Server};
#    Database=localDB;
#    Trusted_Connection=yes;
#
#"""

myLocalDBConn = """
    Driver={SQL Server};
    Server=172.16.1.10;
    Database=localDB;
    UID=phuong.nguyen02;
    PWD=j6y8GU8FmTqFnASZ;
    Trusted_Connection=no;
"""

# ---------------------------------------------

# SFPT
sftpHost = "119.82.135.233"
sftpPort = 2022
#sftpUser = "khoa.ma"
#sftpPassword = "WFhwOUZmUmdLdVhBR1g2"
sftpUser = "nguyen.dao"
sftpPassword = "cllDdGpEenBKNVdlaDVP"



if __name__ == "__main__":
    import base64

    #base64.b64encode('Aa123456798'.encode("utf-8")).decode("utf-8")

    base64.b64encode('nguyen.dao'.encode("utf-8")).decode("utf-8")

    base64.b64decode('cllDdGpEenBKNVdlaDVP').decode("utf-8")
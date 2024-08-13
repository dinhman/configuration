import paramiko
import stat
import shutil
from pathlib import Path
from zipfile import ZipFile
from config import sftp_host, sftp_port, sftp_user, sftp_password
import os
def download_files(result, destination_path):

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(sftp_host, sftp_port, sftp_user, sftp_password)
    
    sftp = ssh.open_sftp()
    Path(destination_path).mkdir(parents=True, exist_ok=True)

    for path in result["Path"]:
        temp = sftp.lstat(path)
        if stat.S_ISDIR(temp.st_mode):
            for file in sftp.listdir(path):
                full_source_path = path + '/' + file
                full_dest_path = destination_path + '//' + file
                sftp.get(full_source_path, full_dest_path)
        else:
            full_source_path = path
            full_dest_path = destination_path + '//' + os.path.basename(path)
            sftp.get(full_source_path, full_dest_path)

    ssh.close()

    with ZipFile(os.path.join('Output', os.path.basename(destination_path) + '.zip'), 'w') as zip_obj:
        for folder_name, subfolders, filenames in os.walk(destination_path):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                zip_obj.write(file_path, os.path.basename(file_path))

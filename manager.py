import subprocess
import time
import datetime

while True:
    p = subprocess.Popen(['python', 'bot.py'])
    time.sleep(3600)
    p.terminate()
    print('Restarted at  ' + datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S'))
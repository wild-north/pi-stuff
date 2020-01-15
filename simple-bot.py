import time, datetime
import picamera
import os
import telepot
from telepot.loop import MessageLoop

def get_ip () :
    return os.popen('hostname -I').read().split('\n')[0].strip()

def on_message(msg):
    chat_id = msg['chat']['id']
    command = msg['text']

    if command == '/ip':
        ip = get_ip()
        message = 'Welcome! My Ip is ' + ip
        message +='\n\nYou can connect to the PI using this command\nssh pi@' + ip
        bot.sendMessage (chat_id, message)
    elif command == '/photo':
        camera = picamera.PiCamera()
        img = 'capture_' + str(time.time() * 10)[:-2] + '.jpg'
        camera.capture('photos/' + img)
        camera.close()
        bot.sendPhoto(chat_id, photo=open('photos/' + img, 'rb'))
    elif command == '/help':
        commands_arr = ['/ip', '/photo']
        help_message = 'Available commands:\n' + '\n'.join(commands_arr)
        bot.sendMessage(chat_id, help_message)



with open('token', 'r') as file:
    TOKEN = file.read().replace('\n', '')

bot = telepot.Bot(TOKEN)
MessageLoop(bot, on_message).run_as_thread()
print('Listening Telegram...')

while 1:
    time.sleep(10)

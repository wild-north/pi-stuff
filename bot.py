#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
#project: home-smart-home.ru

import subprocess
from subprocess import Popen, PIPE
import sys,os
import asyncio
import telepot
import telepot.aio
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.namedtuple import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent


#Тут должны находиться ваши айдишники (для примера я сделал 2 разрешенных)
#Вы можете запустить бота и увидеть при нажатии меню или /start ваш личный айдишник
#Ваши разрешенные айди нужно прописать в переменных chat_allow, заменив None на айдишники 
#chat_allow1=123456789
#chat_allow2=987654321
chat_allow1=None
chat_allow2=None


# Ниже пути расположения скриптов чтения значений датчиков и управление реле.
# Каждый файл - исполняемый питоновский скрипт. 
# Необходимо чтобы все файлы были представлены в системе и были исполняемыми.
# file_read_temp = '/home/pi/telegram/si7021_temp.py'
# file_read_hum = '/home/pi/telegram/si7021_hum.py'
# file_read_water = '/home/pi/telegram/water_read.py'
# file_read_relay = '/home/pi/telegram/relay_state.py'
# file_relay_on = '/home/pi/telegram/relay_on.py'
# file_relay_off = '/home/pi/telegram/relay_off.py'

# Блок переменных ниже - блок файлов-индификаторов (просто айдишник), отвечающиx за состояние сигнализации.
# Для них в директории /home/pi создается отдельная директория (/home/pi/alert_state)  
# Если файл сигнализации присутствует - значит сигнализация должна слать алерты при срабатывании.
# Если файл отсутствует значит считаем что сигнализация выключена. Необходимо для перезагрузок (обесточевания)
# И других программ которые хотят знать что с сигнализацией 
water_id = "/home/pi/telegram/alert_state/w_on"
motion_id = "/home/pi/telegram/alert_state/m_on"
temper_id = "/home/pi/telegram/alert_state/t_on"

# Файл со значением минимального температурного порога срабатывания температурной сигналки
# файл должен существовать и необходимо внести в него значение температуры (целое число)
critical_temp = "/home/pi/telegram/alert_state/critical_temp"

# считывание температуры из скрипта для si7021
def temp_read():
	proc = Popen(['%s' %file_read_temp], shell=True, stdout=PIPE, stderr=PIPE)
	proc.wait()
	t = proc.stdout.read()
	t = float(t)
	return t

# считывание влажности из скрипта для si7021
def hum_read():
        proc = Popen(['%s' %file_read_hum], shell=True, stdout=PIPE, stderr=PIPE)
        proc.wait()
        H = proc.stdout.read()
        H = float(H)
        return H

# считывание значения с датчика воды
def water_read():
	proc = Popen(['%s' %file_read_water], shell=True, stdout=PIPE, stderr=PIPE)
	proc.wait()
	w = proc.communicate()[0]
	w = w.decode(encoding='utf-8')
	return w

# считывание состояния пина на котором висит реле
def relay_read():
	proc = Popen(['%s' %file_read_relay], shell=True, stdout=PIPE, stderr=PIPE)
	proc.wait()
	r = proc.communicate()[0]
	r = int(r)
	if r == 1:
		r='Реле включено'
	elif r==0:
		r='Реле обесточено'
	else: 
		r='Ошибка!'
	return r

# включение/выключение реле в зависимости от входящего параметра
def relay_execute(state):
	if state == 'on' and relay_read() == 'Реле обесточено':
		subprocess.call("%s" %file_relay_on, shell=True)
		text = "включаю реле"
	elif state == 'on' and relay_read() == 'Реле включено':
		text = "реле уже под напряжением"
	elif state == 'off' and relay_read() == 'Реле включено': 
		subprocess.call("%s" %file_relay_off, shell=True)
		text = "отключаю реле"
	elif state == 'off' and relay_read() == 'Реле обесточено':
		text = "реле уже обесточено"
	else:
		print("Ошибка!")
	return text

# управление сигнализациями alarm: on/off. file_id - айдишник сигнализации (см выше)
def alert_f(alarm, file_id):
	#сигнализация уже включена
	if alarm == 'on' and os.path.exists(file_id):
		text = "Сигнализация уже была включена"
	#была включена, теперь отключаем
	elif alarm == 'off' and os.path.exists(file_id):
		text = "Отключаю сигнализацию"
		subprocess.call("rm -f %s" %file_id, shell=True)
	#уже была выключена, выключать не надо
	elif alarm == 'off' and os.path.exists(file_id) == False:
		text = "Сигнализация уже была отключена"
	#выла выключена, теперь включаем
	elif  alarm == 'on' and os.path.exists(file_id) == False:	
		text = "Активирую сигнализацию"
		subprocess.call("touch %s" %file_id, shell=True)
	else:
		text = "err"
	return text

# текущее сотояние сигнализации. file_id - айдишник сигнализации (см выше)
def alert_info_f(file_id):
	if os.path.exists(file_id):
		text = "Сигнализация сейчас активна"
	else:
		text = "Сигнализация сейчас отключена"
	return text

# Текущее минимальное значение температуры
# считывание значения с датчика воды
def c_t_read():
	proc = Popen(['cat %s' %critical_temp], shell=True, stdout=PIPE, stderr=PIPE)
	proc.wait()
	c_t = proc.communicate()[0]
	c_t = c_t.decode(encoding='utf-8')
	c_t = "\nПорог срабатывания установлен на "+c_t+" градусов"
	return c_t



#################################
#Блоки дальше - тело самого бота#
#################################

message_with_inline_keyboard = None
id_write_critical_temper = 0

#эта функция отвечает за текстовые сообщения и "клавиатуру"
async def on_chat_message(msg):
	global id_write_critical_temper
	content_type, chat_type, chat_id = telepot.glance(msg)
	print('Chat:', content_type, chat_type)
	print("id отправителя сообщения: "+str(chat_id))
	if chat_id == chat_allow1 or chat_id == chat_allow2:
		if content_type != 'text':
			return
		else:
			ok=1
		command = msg['text'].lower()
		print(command)

		if command == '/start':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='инфо')],
			[dict(text='управление')],
			[dict(text='сигнализация')],
			])
			await bot.sendMessage(chat_id, 'чем воспользуешься?', reply_markup=markup)
		
		elif command == 'главное меню':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='инфо')],
			[dict(text='управление')],
			[dict(text='сигнализация')],
			])
			await bot.sendMessage(chat_id, 'выбери раздел', reply_markup=markup)
	
		elif command == u'инфо':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='вода'), dict(text='розетка')],
			[dict(text='температура'), dict(text='влажность')],
			[dict(text='главное меню')],
			])
			await bot.sendMessage(chat_id, 'выбери объект', reply_markup=markup)
		
		elif command == u'управление':
			markup = InlineKeyboardMarkup(inline_keyboard=[
			[dict(text='включить', callback_data='relay_on'), dict(text='отключить', callback_data='relay_off')],
			[dict(text='текущее состояние', callback_data='relay_info')],
			])
			global message_with_inline_keyboard
			message_with_inline_keyboard = await bot.sendMessage(chat_id, 'Что сделать с розеткой?', reply_markup=markup)
		
		elif command == u'сигнализация':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='контроль воды')],
			[dict(text='контроль движения')],
			[dict(text='контроль температуры')],
			[dict(text='главное меню')],
			])
			await bot.sendMessage(chat_id, 'какой раздел необходим?', reply_markup=markup)

		elif command == u'температура':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='вода'), dict(text='розетка')],
			[dict(text='температура'), dict(text='влажность')],
			[dict(text='главное меню')]
			])
			#считываем значение с датчика температуры
			t = str(temp_read())+'C°'
			await bot.sendMessage(chat_id, 'Текущая температура: %s' %t, reply_markup=markup)

		elif command == u'влажность':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='вода'), dict(text='розетка')],
			[dict(text='температура'), dict(text='влажность')],
			[dict(text='главное меню')]
			])
			#считываем значение с датчика влажности
			h = str(hum_read())+'%'
			await bot.sendMessage(chat_id, 'Текущая влажность: %s' %h, reply_markup=markup)

		elif command == u'вода':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='вода'), dict(text='розетка')],
			[dict(text='температура'), dict(text='влажность')],
			[dict(text='главное меню')]
			])
                        #считываем значение с датчика воды
			w = str(water_read())
			await bot.sendMessage(chat_id, 'Текущее состояние сенсора воды: %s' %w, reply_markup=markup)
		
		elif command == u'розетка':
			markup = ReplyKeyboardMarkup(keyboard=[
			[dict(text='вода'), dict(text='розетка')],
			[dict(text='температура'), dict(text='влажность')],
			[dict(text='главное меню')]
			])
			#считываем значение с пина, на который подключено реле
			R=str(relay_read())
			await bot.sendMessage(chat_id, 'Состояние розетки (реле): %s' %R, reply_markup=markup)

		elif command == u'контроль воды':
			markup = InlineKeyboardMarkup(inline_keyboard=[
			[dict(text='включить', callback_data='water_on'), dict(text='отключить', callback_data='water_off')],
			[dict(text='текущее состояние', callback_data='water_alert_info')],
			])
			message_with_inline_keyboard = await bot.sendMessage(chat_id, 'Опции сигнализации воды:', reply_markup=markup)

		elif command == u'контроль движения':
			markup = InlineKeyboardMarkup(inline_keyboard=[
			[dict(text='включить', callback_data='motion_on'), dict(text='отключить', callback_data='motion_off')],
			[dict(text='текущее состояние', callback_data='motion_alert_info')],
			])
			message_with_inline_keyboard = await bot.sendMessage(chat_id, 'Опции сигнализации движения:', reply_markup=markup)
		
		elif command == u'контроль температуры':
			markup = InlineKeyboardMarkup(inline_keyboard=[
			[dict(text='включить', callback_data='temp_on'), dict(text='отключить', callback_data='temp_off')],
			[dict(text='порог срабатывания', callback_data='temp_alert_min')],
			[dict(text='текущее состояние', callback_data='temp_alert_info')],
			])
			message_with_inline_keyboard = await bot.sendMessage(chat_id, 'Опции сигнализации температуры:', reply_markup=markup)

		else:
			if id_write_critical_temper == 1:
				#если происходит установка температуры срабатывания
				if command.isdigit():
					subprocess.call("echo %s > %s" %(command, critical_temp), shell=True)
					markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='главное меню')]])
					await bot.sendMessage(chat_id, str("Температурный минимум установлен в %s градусов. Ниже этой температуры будут приходить алерты") %command, reply_markup=markup)
					id_write_critical_temper = 0
				else:
					markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='главное меню')]])
					await bot.sendMessage(chat_id, str("%s - это не целое число. При необходимости пройдите настройку заново. Значение не установлено!") %command, reply_markup=markup)
					id_write_critical_temper = 0
			else:
				#если ввели текст, не соответствующий команде
				await bot.sendMessage(chat_id, str("начните чат с команды /start"))

	else:
		#если чат айди не соответствует разрешенному
		markup_protect = ReplyKeyboardMarkup(keyboard=[[dict(text='я очень тугой, еще раз можно?')]])
		await bot.sendMessage(chat_id, 'Вы не имеете доступа к этому боту! Обратитесь к владельцу за разрешением.', reply_markup=markup_protect)
		return

#эта функция отвечает за "волшебные полупрозрачные кнопки"
async def on_callback_query(msg):
	global id_write_critical_temper
	query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
	print('Callback query:', query_id, data)
	id_owner_callback=msg['from']['id']	
	print("id отправителя запроса: "+str(id_owner_callback))
	if id_owner_callback == chat_allow1 or id_owner_callback == chat_allow2:
		#управление реле (розеткой)
		if data == 'relay_on':
			R_inf = str(relay_execute('on'))
			await bot.answerCallbackQuery(query_id, text='%s' %R_inf, show_alert=True)
		elif data == 'relay_off':
			R_inf = str(relay_execute('off'))
			await bot.answerCallbackQuery(query_id, text='%s' %R_inf, show_alert=True)
		elif data == 'relay_info':
			R=str(relay_read())
			await bot.answerCallbackQuery(query_id, text='%s'%R, show_alert=True)

		#управление сигнализацией воды
		elif data == 'water_on':
			inf = str(alert_f('on', water_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'water_off':
			inf = str(alert_f('off', water_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'water_alert_info':
			inf = str(alert_info_f(water_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)

		#управление сигнализацией движения
		elif data == 'motion_on':
			inf = str(alert_f('on', motion_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'motion_off':
			inf = str(alert_f('off', motion_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'motion_alert_info':
			inf = str(alert_info_f(motion_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)

		#управление сигнализацией температуры
		elif data == 'temp_on':
			inf = str(alert_f('on', temper_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'temp_off':
			inf = str(alert_f('off', temper_id))
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'temp_alert_info':
			inf = str(alert_info_f(temper_id))
			info_c_t = str(c_t_read())
			inf = inf+info_c_t
			await bot.answerCallbackQuery(query_id, text='%s' %inf, show_alert=True)
		elif data == 'temp_alert_min':
			id_write_critical_temper = 1
			await bot.answerCallbackQuery(query_id, text='Установите min порог срабатывания температурной сигнализации. Введите целое число.', show_alert=True)
		else:
			next=1
	else:
		await bot.answerCallbackQuery(query_id, text='У вас нет доступа', show_alert=True)

#В TOKEN должен находиться ваш токен, полученый при создании бота!
#замените значение на свои данные!

with open('token', 'r') as file:
    TOKEN = file.read().replace('\n', '')

bot = telepot.aio.Bot(TOKEN)
loop = asyncio.get_event_loop()
#вызов списка ваших функций для работы с api
loop.create_task(bot.message_loop({'chat': on_chat_message,
                                   'callback_query': on_callback_query}))
#project: home-smart-home.ru
print('Listening Telegram...')
loop.run_forever()

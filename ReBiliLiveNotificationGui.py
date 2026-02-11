import tkinter as tk
import ttkbootstrap as ttk
import ttkbootstrap.dialogs.dialogs as tkmb
import tkinter.font as tkfont
import webbrowser
from retrying import retry
import time
import pystray
from pystray import MenuItem, Menu
from PIL import Image, ImageTk, ImageDraw
import threading
import requests
import re
import os
import sys
import json
import subprocess
import tempfile
import win32api
import win32con
import pythoncom
import win32com.client
import shlex

# 原作者 @yunhuanyx 
# 原项目 https://github.com/yunhuanyx/biliLiveNotification
# 原图标未打包进来 使用ai绘制新图标代替

# 全局变量
listen_button_flag = 0
pause_flag = False
stop_flag = False
notification_windows = {}

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

user_config_dir = os.path.join(os.path.expanduser('~'), '.ReBiliLiveNotification')
os.makedirs(user_config_dir, exist_ok=True)
config_path = os.path.join(user_config_dir, 'ReBLN.ini')

# UA
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"}

# 关于
def show_about_window():
    about_window = tk.Toplevel(root)
    about_window.title("关于")
    about_window.resizable(False, False)
    about_window.attributes('-topmost', True)
    
    window_width = 410
    window_height = 300
    screen_width = about_window.winfo_screenwidth()
    screen_height = about_window.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2) - 50
    about_window.geometry(f'{window_width}x{window_height}+{x}+{y}')
    
    about_window.iconphoto(True, ico_img)
    
    main_frame = ttk.Frame(about_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    title_label = ttk.Label(main_frame, text="关于 Re：B站开播提醒", 
                           font=("微软雅黑", 12, "bold"))
    title_label.pack(pady=(0, 15))
    
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    
    text_scrollbar = ttk.Scrollbar(text_frame, bootstyle="round")
    text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    about_text = tk.Text(text_frame, height=8, wrap=tk.WORD,
                        font=("微软雅黑", 9),
                        yscrollcommand=text_scrollbar.set,
                        relief=tk.FLAT, bd=2, bg="#f0f0f0")
    text_scrollbar.config(command=about_text.yview)
    
    about_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    about_content = f"""原作者 @yunhuanyx 
原项目 https://github.com/yunhuanyx/biliLiveNotification
配置文件位于 {config_path}
自动逻辑：关闭前如果没有手动停止检测，下次启动时将会自动开始检测，用于搭配开机自启，配置文件中使用autoStartListen=0/1控制
正常情况下请勿修改API
此为原项目基础上微改新增功能，侵权自删"""
    
    about_text.insert(tk.END, about_content)
    about_text.configure(state=tk.DISABLED)
    
    close_button = ttk.Button(main_frame, text="关闭", width=10,
                             command=about_window.destroy,
                             bootstyle="secondary")
    close_button.pack()
    
    about_window.bind('<Escape>', lambda e: about_window.destroy())
    
    about_window.focus_force()

# 计划任务自启动
def get_task_name():
    return 'ReBiliLiveNotification'

def get_app_path():
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        return exe_path
    else:
        script_path = os.path.abspath(__file__)
        return sys.executable

def set_autostart(enabled):
    try:
        task_name = get_task_name()
        
        pythoncom.CoInitialize()
        
        scheduler = win32com.client.Dispatch('Schedule.Service')
        scheduler.Connect()
        
        root_folder = scheduler.GetFolder('\\')
        
        if enabled:
            task_def = scheduler.NewTask(0)
            
            reg_info = task_def.RegistrationInfo
            reg_info.Description = 'Re：B站开播提醒开机自启动'
            reg_info.Author = 'ReBiliLiveNotification'
            
            trigger = task_def.Triggers.Create(9)
            trigger.Enabled = True
            
            action = task_def.Actions.Create(0)
            app_path = get_app_path()
            
            if getattr(sys, 'frozen', False):
                action.Path = app_path
                action.Arguments = '--minimized'
                action.WorkingDirectory = os.path.dirname(app_path)
            else:
                script_path = os.path.abspath(__file__)
                python_dir = os.path.dirname(sys.executable)
                pythonw_path = os.path.join(python_dir, 'pythonw.exe')
                
                if os.path.exists(pythonw_path):
                    action.Path = pythonw_path
                    action.WorkingDirectory = os.path.dirname(script_path)
                    action.Arguments = f'"{script_path}" --minimized'
                else:
                    action.Path = sys.executable
                    action.WorkingDirectory = os.path.dirname(script_path)
                    action.Arguments = f'"{script_path}" --minimized'
            
            settings = task_def.Settings
            settings.Enabled = True
            settings.Hidden = False
            settings.RunOnlyIfIdle = False
            settings.DisallowStartIfOnBatteries = False
            settings.StopIfGoingOnBatteries = False
            settings.StartWhenAvailable = False
            settings.AllowHardTerminate = True
            settings.WakeToRun = False
            settings.Priority = 7
            
            task_def.Principal.RunLevel = 1
            
            root_folder.RegisterTaskDefinition(
                task_name,
                task_def,
                6,
                None,
                None,
                3
            )
            
            print(f"已设置开机自启动计划任务: {task_name}")
            return True
            
        else:
            try:
                root_folder.DeleteTask(task_name, 0)
                print(f"已删除开机自启动计划任务: {task_name}")
                return True
            except Exception as e:
                if '80070002' in str(e):
                    print(f"计划任务 {task_name} 不存在，无需删除")
                    return True
                else:
                    raise
                    
    except Exception as e:
        print(f"设置开机自启动计划任务失败: {e}")
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def is_autostart_enabled():
    try:
        task_name = get_task_name()
        
        cmd = f'schtasks /Query /TN "{task_name}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
        else:
            return False

    except Exception as e:
        print(f"检查开机自启动状态失败: {e}")
        return False

def save_listen_state():
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('autoListen='):
                    new_lines.append(f'autoListen={1 if listen_button_flag == 1 else 0}')
                elif not line.startswith('autoListenTime='):
                    new_lines.append(line)
            
            if not any(line.startswith('autoListen=') for line in new_lines):
                new_lines.append(f'autoListen={1 if listen_button_flag == 1 else 0}')
            
            with open(config_path, 'w') as f:
                f.write('\n'.join(new_lines))
                
            print(f"保存检测状态: listen_button_flag={listen_button_flag}")
    except Exception as e:
        print(f"保存检测状态失败: {e}")

# 自动检测
def load_listen_state():
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            auto_start_listen_match = re.search(r'autoStartListen=(\d)', content)
            if auto_start_listen_match:
                auto_start_listen = auto_start_listen_match.group(1) == '1'
                if auto_start_listen:
                    room_match = re.search(r'roomID=(.*)', content)
                    if room_match:
                        room_id = room_match.group(1).strip()
                        if room_id and room_id != '':
                            print(f"检测到 autoStartListen=1，房间号已配置，将自动开始检测")
                            return True
                        else:
                            print("autoStartListen=1 但房间号为空，不自动开始检测")
                            return False
                    else:
                        print("未找到房间号配置")
                        return False
                else:
                    print("autoStartListen=0，不自动开始检测")
                    return False
            
            auto_listen_match = re.search(r'autoListen=(\d)', content)
            
            if auto_listen_match:
                auto_listen = auto_listen_match.group(1) == '1'
                
                if auto_listen:
                    room_match = re.search(r'roomID=(.*)', content)
                    if room_match:
                        room_id = room_match.group(1).strip()
                        if room_id and room_id != '':
                            print(f"自动检测状态启用，房间号已配置")
                            return True
                        else:
                            print("自动检测已启用但房间号为空，不自动开始检测")
                            return False
                    else:
                        print("未找到房间号配置")
                        return False
                else:
                    print("未启用自动检测")
            else:
                print("未找到自动检测配置")
    except Exception as e:
        print(f"加载检测状态失败: {e}")
    
    return False

def is_minimized_start():
    return '--minimized' in sys.argv

def auto_start_listening():
    print("尝试自动开始检测...")
    
    room_id_text = room_id_entry.get('1.0', tk.END).strip()
    room_id_text = room_id_text.replace('，', ',').replace('\n', '').replace(' ', '')
    
    if not room_id_text:
        print("房间号为空，不自动开始检测")
        
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END, time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   房间号为空，不自动开始检测\n')
        info_text.config(state=tk.DISABLED)
        info_text.see(tk.END)
        return
    
    print("程序启动...")
    
    stateStr.set("状态：检测中")
    
    listen.configure(text="暂停检测", bootstyle="warning-outline")
    
    global listen_button_flag
    listen_button_flag = 1
    
    stopl.configure(state="normal")
    
    info_text.config(state=tk.NORMAL)
    info_text.insert(tk.END, time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   程序启动...\n')
    info_text.config(state=tk.DISABLED)
    info_text.see(tk.END)
    
    root.after(1000, begin_listen_async)

def begin_listen_async():
    threading.Thread(target=begin_listen, name="auto_listen", daemon=True).start()

def center_window(w, h):
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (w/2) - 20
    y = (hs/2) - (h/2) - 20
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))

def show_window():
    root.deiconify()
    root.lift()
    root.focus_force()

def quit_window():
    save_listen_state()
    
    for rid, win in notification_windows.items():
        if win and win.winfo_exists():
            try:
                win.destroy()
            except:
                pass
    
    global stop_flag
    stop_flag = True
    if 'wait_event' in globals():
        wait_event.set()
    
    if 'lock_file' in globals():
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass
    
    root.destroy()

# 开始检测
def begin_listen():
    global listen_button_flag
    try:
        with open(config_path, 'r+') as fl:
            fl_text = fl.read()
        
        roomIdStr = re.search("roomID=(.*)", fl_text)
        if not roomIdStr or roomIdStr.group(1) == "":
            root.after(0, lambda: tkmb.Messagebox.show_error(title="错误", message="房间号为空，请保存设置后再开始！"))
            raise RuntimeError("房间号为空")
        
        roomIdStr = roomIdStr.group(1)
        roomID = roomIdStr.split(',')
        roomID_dic = dict()
        for rid in roomID:
            roomID_dic[rid] = False
        
        timeInterval = int(re.search("timeInterval=(.*)", fl_text).group(1))

        stateStr.set("状态：检测中")
        if 'listen' in globals():
            listen.configure(text="暂停检测", bootstyle="warning-outline")
        listen_button_flag = 1
        if 'stopl' in globals():
            stopl.configure(state="normal")
        
        try:
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            existing_config[key] = value
            
            existing_config['autoStartListen'] = '1'
            
            with open(config_path, 'w') as f:
                for key, value in existing_config.items():
                    f.write(f'{key}={value}\n')
            
            print("已设置 autoStartListen=1")
        except Exception as e:
            print(f"设置 autoStartListen 失败: {e}")
        
        try:
            listen_main(roomID, roomID_dic, timeInterval)
        except Exception as e:
            if 'listen' in globals():
                listen.configure(text='开始检测', bootstyle="outline")
            listen_button_flag = 0
            stateStr.set("状态：空闲中")
            global stop_flag
            stop_flag = False
            if 'wait_event' in globals():
                wait_event.clear()
            if 'info_text' in globals():
                info_text.config(state=tk.NORMAL)
                info_text.insert(tk.END,
                                 time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                 + str(e) + '\n')
                info_text.config(state=tk.DISABLED)
                info_text.see(tk.END)
            if 'stopl' in globals():
                stopl.configure(state="disabled")
    except OSError:
        root.after(0, lambda: tkmb.Messagebox.show_error(title="错误", message="未找到配置文件，请进行设置！"))
        raise OSError("未找到文件")

# 暂停检测
def listen_thread():
    global pause_flag, listen_button_flag
    
    if listen_button_flag == 0:
        threading.Thread(target=begin_listen, name="listen", daemon=True).start()
    elif listen_button_flag == 1:
        pause_flag = True
        pause_event.clear()
        wait_event.set()
        listen.configure(text="恢复检测", bootstyle="outline")
        stopl.configure(state="disabled")
        stateStr.set("状态：已暂停")
        listen_button_flag = 2
    else:
        pause_flag = False
        pause_event.set()
        listen.configure(text="暂停检测", bootstyle="warning-outline")
        stopl.configure(state="normal")
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END,
                         time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                         + "已恢复检测" + '\n')
        info_text.config(state=tk.DISABLED)
        info_text.see(tk.END)
        stateStr.set("状态：检测中")
        listen_button_flag = 1

def stop_close():
    quit_window()

def stop_listen():
    global stop_flag
    stop_flag = True
    wait_event.set()
    global listen_button_flag
    listen_button_flag = 0
    listen.configure(text='开始检测', bootstyle="outline")
    stopl.configure(state="disabled")
    stateStr.set("状态：空闲中")
    
    try:
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key] = value
        
        existing_config['autoStartListen'] = '0'
        
        with open(config_path, 'w') as f:
            for key, value in existing_config.items():
                f.write(f'{key}={value}\n')
        
        print("已设置 autoStartListen=0")
    except Exception as e:
        print(f"设置 autoStartListen 失败: {e}")
    
    save_listen_state()

# 打开直播间
@retry(stop_max_attempt_number=5)
def get_live_status(rid):
    url = api + rid
    response = requests.get(url, headers=headers)
    assert response.status_code == 200
    if response.json()['code'] != 0:
        raise RuntimeError(f'直播间 {rid} 不存在')
    live_json = response.json()
    return_dict = {
        'live_status': live_json['data']['live_status'],
        'uid': live_json['data']['uid']
    }
    return return_dict

@retry(stop_max_attempt_number=3)
def get_streamer_info(uid):
    url = "https://api.live.bilibili.com/live_user/v1/Master/info?uid=" + str(uid)
    response = requests.get(url, headers=headers)
    assert response.status_code == 200
    streamer_json = response.json()
    return_dict = {
        'uname': streamer_json['data']['info']['uname'],
        'face': streamer_json['data']['info']['face']
    }
    return return_dict

def open_live_url(rid):
    webbrowser.open(f"https://live.bilibili.com/{rid}")
    
    info_text.config(state=tk.NORMAL)
    info_text.insert(tk.END,
                     time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                     + f"已打开直播间 {rid}" + '\n')
    info_text.config(state=tk.DISABLED)
    info_text.see(tk.END)

def show_notification_window(rid, uname, uid):
    if rid in notification_windows and notification_windows[rid] and notification_windows[rid].winfo_exists():
        try:
            notification_windows[rid].destroy()
        except:
            pass
    
    # 通知窗口
    notification_window = tk.Toplevel(root)
    notification_window.title(f"{uname} 开播提醒")
    notification_window.resizable(False, False)
    notification_window.attributes('-topmost', True)
    
    screen_width = notification_window.winfo_screenwidth()
    screen_height = notification_window.winfo_screenheight()
    window_width = 300
    window_height = 180
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2) - 50
    notification_window.geometry(f'{window_width}x{window_height}+{x}+{y}')
    
    notification_window.iconphoto(True, ico_img)
    
    notification_window.focus_force()
    
    def on_key_press(event):
        if event.keysym == 'y' or event.keysym == 'Y':
            open_live_url(rid)
            notification_window.destroy()
        elif event.keysym == 'n' or event.keysym == 'N':
            notification_window.destroy()
    
    notification_window.bind('<KeyPress>', on_key_press)
    
    main_frame = ttk.Frame(notification_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    title_label = tk.Label(main_frame, text=f"{uname} 开播了！", 
                           font=("微软雅黑", 13, "bold"), fg="#00A1D6")
    title_label.pack(pady=(0, 10))
    
    room_label = tk.Label(main_frame, text=f"房间号: {rid}", 
                          font=("微软雅黑", 10))
    room_label.pack(pady=(0, 20))
    
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))
    
    button_center_frame = ttk.Frame(button_frame)
    button_center_frame.pack(expand=True)
    
    open_button = ttk.Button(button_center_frame, text="打开直播间 (Y)", width=12,
                            command=lambda: [open_live_url(rid), notification_window.destroy()],
                            bootstyle="success")
    open_button.pack(side=tk.LEFT, padx=(0, 10))
    
    ignore_button = ttk.Button(button_center_frame, text="忽略 (N)", width=12,
                              command=notification_window.destroy,
                              bootstyle="secondary")
    ignore_button.pack(side=tk.LEFT)
    
    notification_windows[rid] = notification_window
    
    def on_close():
        if rid in notification_windows:
            notification_windows[rid] = None
        notification_window.destroy()
    
    notification_window.protocol("WM_DELETE_WINDOW", on_close)
    
    # 10分钟后关闭
    def auto_close():
        if notification_window.winfo_exists():
            on_close()
    
    notification_window.after(600000, auto_close)

# 直播状态
def listen_main(roomID, roomID_dic, wait_time):
    i = 0
    ex = ""
    global stop_flag, pause_flag
    
    while True:
        if stop_flag:
            raise RuntimeError("停止检测")

        if pause_flag:
            info_text.config(state=tk.NORMAL)
            info_text.insert(tk.END,
                             time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                             + "已暂停检测" + '\n')
            info_text.config(state=tk.DISABLED)
            info_text.see(tk.END)
            wait_event.clear()
            pause_event.wait()

        for rid in roomID[::-1]:
            try:
                live_info_dict = get_live_status(rid)
                live_status = live_info_dict['live_status']
                uid = live_info_dict['uid']
                
                if live_status == 1:
                    if i == 0:
                        info_text.config(state=tk.NORMAL)
                        info_text.insert(tk.END,
                                         time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                         + "开始检测..." + '\n')
                        info_text.config(state=tk.DISABLED)
                        info_text.see(tk.END)
                    
                    if not roomID_dic[rid]:
                        uinfo_dict = get_streamer_info(uid)
                        uname = uinfo_dict['uname']
                        
                        update_table_row(rid, uname, "直播中")
                        
                        streamer_info[rid] = {
                            'uid': uid,
                            'uname': uname,
                        }
                        
                        if auto_jump_var.get():
                            open_live_url(rid)
                            info_text.config(state=tk.NORMAL)
                            info_text.insert(tk.END,
                                             time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                             + f"{uname}({rid})已开播，已自动跳转" + '\n')
                            info_text.config(state=tk.DISABLED)
                            info_text.see(tk.END)
                        else:
                            root.after(0, lambda r=rid, n=uname, u=uid: show_notification_window(r, n, u))
                            
                            info_text.config(state=tk.NORMAL)
                            info_text.insert(tk.END,
                                             time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                             + f"{uname}({rid})已开播，已显示通知窗口" + '\n')
                            info_text.config(state=tk.DISABLED)
                            info_text.see(tk.END)
                        
                        roomID_dic[rid] = True
                    
                    i += 1
                else:
                    if i == 0:
                        info_text.config(state=tk.NORMAL)
                        info_text.insert(tk.END,
                                         time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                         + "开始检测..." + '\n')
                        info_text.config(state=tk.DISABLED)
                        info_text.see(tk.END)
                    
                    if roomID_dic[rid]:
                        uinfo_dict = get_streamer_info(uid)
                        uname = uinfo_dict['uname']
                        
                        update_table_row(rid, uname, "未开播")
                        
                        if rid in notification_windows and notification_windows[rid] and notification_windows[rid].winfo_exists():
                            try:
                                notification_windows[rid].destroy()
                            except:
                                pass
                            notification_windows[rid] = None
                        
                        info_text.config(state=tk.NORMAL)
                        info_text.insert(tk.END,
                                         time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                                         + f"{uname}({rid})已下播" + '\n')
                        info_text.config(state=tk.DISABLED)
                        info_text.see(tk.END)
                        
                        roomID_dic[rid] = False
                    i += 1

            except Exception as e:
                ex = e
                info_text.config(state=tk.NORMAL)
                info_text.insert(tk.END, time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   ' + str(e) + '\n')
                info_text.config(state=tk.DISABLED)
                info_text.see(tk.END)

        if stop_flag:
            raise RuntimeError("停止检测")
        if ex != "":
            ex = ""
            wait_event.wait(5)
            continue
        wait_event.wait(wait_time)

# 输入检测
def save_settings():
    room_id_text = room_id_entry.get('1.0', tk.END).strip()
    room_id_text = room_id_text.replace('，', ',').replace('\n', '').replace(' ', '')
    
    time_interval = time_interval_var.get()
    api_url = api_var.get().strip()
    
    if room_id_text:
        room_ids = room_id_text.split(',')
        for rid in room_ids:
            if not rid.isdigit():
                tkmb.Messagebox.show_error(title="错误", message=f"房间号 {rid} 无效，必须为数字")
                return
    
    try:
        time_int = int(time_interval)
        if time_int < 10:
            tkmb.Messagebox.show_error(title="错误", message="检测间隔不能小于10秒")
            return
    except ValueError:
        tkmb.Messagebox.show_error(title="错误", message="检测间隔必须为数字")
        return
    
    if not api_url:
        tkmb.Messagebox.show_error(title="错误", message="API网址不能为空")
        return
    
    try:
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key] = value
        
        existing_config['api'] = api_url
        existing_config['roomID'] = room_id_text
        existing_config['timeInterval'] = str(time_int)
        existing_config['autoJump'] = '1' if auto_jump_var.get() else '0'
        existing_config['autoStartListen'] = '1' if listen_button_flag == 1 else '0'
        
        existing_config['autoStart'] = '1' if autostart_var.get() else '0'
        
        if 'autoListen' in existing_config:
            del existing_config['autoListen']
        
        with open(config_path, 'w') as f:
            for key, value in existing_config.items():
                f.write(f'{key}={value}\n')
        
        global api
        api = api_url
        
        if autostart_var.get():
            success = set_autostart(True)
            if success:
                tkmb.Messagebox.show_info(title="成功", message="设置已保存，开机自启已启用")
            else:
                tkmb.Messagebox.show_warning(title="提示", message="设置已保存，但修改开机自启请以管理员运行！")
        else:
            success = set_autostart(False)
            if success:
                tkmb.Messagebox.show_info(title="成功", message="设置已保存，开机自启已禁用")
            else:
                tkmb.Messagebox.show_warning(title="提示", message="设置已保存，但修改开机自启请以管理员运行！")
        
        load_table_data()
        
    except Exception as e:
        tkmb.Messagebox.show_error(title="错误", message=f"保存设置失败: {str(e)}")

# 配置文件
def load_settings():
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
            
            room_match = re.search(r"roomID=(.*)", content)
            if room_match:
                room_ids = room_match.group(1).strip()
                room_id_entry.delete('1.0', tk.END)
                room_id_entry.insert('1.0', room_ids)
            
            time_match = re.search(r"timeInterval=(.*)", content)
            if time_match:
                time_interval_var.set(time_match.group(1).strip())
            
            api_match = re.search(r"api=(.*)", content)
            if api_match:
                loaded_api = api_match.group(1).strip()
                api_var.set(loaded_api)
                global api
                api = loaded_api
            else:
                default_api = "https://api.live.bilibili.com/room/v1/Room/room_init?id="
                api_var.set(default_api)
                api = default_api
                
            auto_jump_match = re.search(r"autoJump=(\d)", content)
            if auto_jump_match:
                auto_jump_var.set(auto_jump_match.group(1) == '1')
            
            autostart_match = re.search(r"autoStart=(\d)", content)
            if autostart_match:
                autostart_var.set(autostart_match.group(1) == '1')
            else:
                autostart_var.set(is_autostart_enabled())
                
            auto_start_listen_match = re.search(r"autoStartListen=(\d)", content)
            if auto_start_listen_match:
                print(f"加载到 autoStartListen={auto_start_listen_match.group(1)}")
            else:
                print("未找到 autoStartListen 参数，将使用默认值0")
                
    except Exception as e:
        print(f"加载设置失败: {e}")

def update_table_row(rid, uname, status):
    for item in tree.get_children():
        tree.delete(item)
    
    global rowdata
    new_rowdata = []
    for row in rowdata:
        if row[1] == rid:
            new_rowdata.append((uname, rid, status))
        else:
            new_rowdata.append(row)
    rowdata = new_rowdata
    
    for row in rowdata:
        tree.insert("", "end", values=row)

# 直播状态
def load_table_data():
    global rowdata, streamer_info
    
    try:
        room_id_text = room_id_entry.get('1.0', tk.END).strip()
        room_id_text = room_id_text.replace('，', ',').replace('\n', '').replace(' ', '')
        
        for item in tree.get_children():
            tree.delete(item)
        
        if not room_id_text:
            rowdata = []
            return
        
        room_ids = room_id_text.split(',')
        rowdata = []
        streamer_info = {}
        
        for rid in room_ids:
            if rid and rid.isdigit():
                try:
                    live_rtn = get_live_status(rid)
                    uinfo_rtn = get_streamer_info(live_rtn['uid'])
                    
                    if live_rtn['live_status'] == 1:
                        live_stat = '直播中'
                    else:
                        live_stat = '未开播'
                    
                    rowdata.append((uinfo_rtn['uname'], rid, live_stat))
                    streamer_info[rid] = {
                        'uid': live_rtn['uid'],
                        'uname': uinfo_rtn['uname'],
                        'face': uinfo_rtn['face']
                    }
                except Exception as e:
                    rowdata.append(("获取失败", rid, "错误"))
        
        for row in rowdata:
            tree.insert("", "end", values=row)
            
    except Exception as e:
        print(f"加载表格数据失败: {e}")

def on_exit():
    save_listen_state()
    root.withdraw()

# 创建图标
def create_microphone_icon():
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = '#00A1D6'
    
    mic_w = 20
    mic_h = 34
    mic_x = (size - mic_w) // 2
    mic_y = 6
    draw.ellipse([mic_x, mic_y, mic_x + mic_w, mic_y + mic_w], fill=color)
    draw.ellipse([mic_x, mic_y + mic_h - mic_w, mic_x + mic_w, mic_y + mic_h], fill=color)
    draw.rectangle([mic_x, mic_y + mic_w//2, mic_x + mic_w, mic_y + mic_h - mic_w//2], fill=color)
    
    arc_padding = 7
    arc_thickness = 5

    arc_box = [
        mic_x - arc_padding, 
        mic_y + 16, 
        mic_x + mic_w + arc_padding, 
        mic_y + mic_h + 8
    ]
    
    draw.arc(arc_box, start=0, end=180, fill=color, width=arc_thickness)
    arc_cy = (arc_box[1] + arc_box[3]) / 2
    r_tip = arc_thickness / 2 - 0.5
    draw.ellipse([arc_box[0]-r_tip, arc_cy-r_tip, arc_box[0]+r_tip, arc_cy+r_tip], fill=color)
    draw.ellipse([arc_box[2]-r_tip, arc_cy-r_tip, arc_box[2]+r_tip, arc_cy+r_tip], fill=color)
    
    stem_h = 7
    stem_y_start = arc_box[3]
    draw.line([size//2, stem_y_start, size//2, stem_y_start + stem_h], fill=color, width=arc_thickness)
    
    base_y = stem_y_start + stem_h
    base_w = 24
    
    draw.line([size//2 - base_w//2, base_y, size//2 + base_w//2, base_y], fill=color, width=arc_thickness)
    draw.ellipse([size//2 - base_w//2 - r_tip, base_y - r_tip, size//2 - base_w//2 + r_tip, base_y + r_tip], fill=color)
    draw.ellipse([size//2 + base_w//2 - r_tip, base_y - r_tip, size//2 + base_w//2 + r_tip, base_y + r_tip], fill=color)
    
    return image

# 单实例检查
def check_single_instance():
    global lock_file
    lock_file = os.path.join(user_config_dir, 'ReBLN.lock')
    
    try:
        fd = os.open(lock_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        
        import atexit
        atexit.register(cleanup_lock_file)
        
        print(f"创建锁文件成功: {lock_file}")
        return True
        
    except FileExistsError:
        try:
            with open(lock_file, 'r') as f:
                pid_str = f.read().strip()
                
            if pid_str and pid_str.isdigit():
                pid = int(pid_str)
                
                if is_process_running(pid):
                    print(f"已有一个实例在运行 (PID: {pid})")
                    return False
                else:
                    print(f"锁文件中的进程 {pid} 已不存在，清理锁文件")
                    try:
                        os.remove(lock_file)
                    except:
                        pass
                    return check_single_instance()
            else:
                print("锁文件内容无效，清理锁文件")
                try:
                    os.remove(lock_file)
                except:
                    pass
                return check_single_instance()
                
        except Exception as e:
            print(f"检查锁文件失败: {e}")
            try:
                os.remove(lock_file)
            except:
                pass
            return check_single_instance()
            
    except Exception as e:
        print(f"创建锁文件失败: {e}")
        return True

def is_process_running(pid):
    try:
        if os.name == 'nt':
            result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                  capture_output=True, text=True, shell=True)
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.CalledProcessError):
        return False

def cleanup_lock_file():
    global lock_file
    try:
        if 'lock_file' in globals() and os.path.exists(lock_file):
            os.remove(lock_file)
            print(f"清理锁文件: {lock_file}")
    except:
        pass

# 延迟启动
def delayed_startup():
    should_minimize = is_minimized_start()
    should_auto_listen = load_listen_state()
    
    print(f"启动参数: sys.argv={sys.argv}")
    print(f"自动检测={should_auto_listen}, 最小化={should_minimize}")
    
    if should_minimize:
        print("开机自启动，以最小化状态启动...")
        root.after(500, root.withdraw)
    
    if should_auto_listen:
        print("检测到自动检测已启用，检查房间号...")
        root.after(1500, auto_start_listening)

# 主程序
if __name__ == "__main__":
    if not check_single_instance():
        print("程序已在运行，退出新实例")
        sys.exit(0)
    
    root = tk.Tk()
    root.title(f'Re：B站开播提醒')
    
    window_width = 360
    window_height = 520
    
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (window_width/2) - 20
    y = (hs/2) - (window_height/2) - 20
    root.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))
    
    root.resizable(False, False)
    
    # 图标
    icon_image = create_microphone_icon()
    ico_img = ImageTk.PhotoImage(icon_image)
    root.iconphoto(True, ico_img)
    
    # grid布局
    main_control_frame = ttk.Frame(root)
    main_control_frame.pack(fill=tk.X, padx=6, pady=6)
    
    for i in range(4):
        main_control_frame.grid_columnconfigure(i, weight=1, uniform="control_cols")
    
    # 第一行
    listen = ttk.Button(main_control_frame, text='开始检测', width=8, 
                        command=listen_thread, bootstyle="outline")
    listen.grid(row=0, column=0, padx=(0, 1), sticky="ew")
    
    stopl = ttk.Button(main_control_frame, text='停止检测', width=8, 
                       command=stop_listen, state="disabled", bootstyle="outline")
    stopl.grid(row=0, column=1, padx=1, sticky="ew")
    
    save_btn = ttk.Button(main_control_frame, text='保存设置', width=8, 
                          command=save_settings, bootstyle="outline")
    save_btn.grid(row=0, column=2, padx=1, sticky="ew")
    
    minimize_btn = ttk.Button(main_control_frame, text='回到托盘', width=8, 
                             command=on_exit, bootstyle="outline")
    minimize_btn.grid(row=0, column=3, padx=(1, 0), sticky="ew")
    
    # 第二行
    # 状态显示
    state_container = ttk.Frame(main_control_frame)
    state_container.grid(row=1, column=0, padx=(0, 1), pady=(4, 0), sticky="ew")
    state_container.grid_columnconfigure(0, weight=1)
    
    stateStr = tk.StringVar(value="状态：空闲中")
    state_label = tk.Label(state_container, textvariable=stateStr, font=("微软雅黑", 9))
    state_label.grid(row=0, column=0)
    
    # 检测间隔
    interval_container = ttk.Frame(main_control_frame)
    interval_container.grid(row=1, column=1, padx=1, pady=(4, 0), sticky="ew")
    interval_container.grid_columnconfigure(0, weight=1)
    
    interval_inner = ttk.Frame(interval_container)
    interval_inner.grid(row=0, column=0)
    
    time_interval_var = tk.StringVar(value="60")
    ttk.Label(interval_inner, text="间隔(s):").pack(side=tk.LEFT, padx=(0, 2))
    time_interval_entry = ttk.Entry(interval_inner, textvariable=time_interval_var, 
                                   width=4, justify='center')
    time_interval_entry.pack(side=tk.LEFT)
    
    # 开机自启
    autostart_container = ttk.Frame(main_control_frame)
    autostart_container.grid(row=1, column=2, padx=1, pady=(4, 0), sticky="ew")
    autostart_container.grid_columnconfigure(0, weight=1)
    
    autostart_var = tk.BooleanVar(value=is_autostart_enabled())
    autostart_check = ttk.Checkbutton(autostart_container, text="开机自启", 
                                       variable=autostart_var)
    autostart_check.grid(row=0, column=0)
    
    # 自动跳转
    auto_jump_container = ttk.Frame(main_control_frame)
    auto_jump_container.grid(row=1, column=3, padx=(1, 0), pady=(4, 0), sticky="ew")
    auto_jump_container.grid_columnconfigure(0, weight=1)
    
    auto_jump_var = tk.BooleanVar(value=False)
    auto_jump_check = ttk.Checkbutton(auto_jump_container, text="自动跳转", 
                                       variable=auto_jump_var)
    auto_jump_check.grid(row=0, column=0)
    
    # 检测设置
    room_settings_frame = ttk.LabelFrame(root, text="检测设置")
    room_settings_frame.pack(fill=tk.X, padx=6, pady=(0, 6))
    
    room_settings_inner = ttk.Frame(room_settings_frame)
    room_settings_inner.pack(padx=6, pady=6, fill=tk.BOTH, expand=True)
    
    room_id_frame = ttk.Frame(room_settings_inner)
    room_id_frame.pack(fill=tk.X)
    
    room_id_label = ttk.Label(room_id_frame, text="房间号(逗号隔开):")
    room_id_label.pack(side=tk.LEFT, anchor="w")
    
    room_id_entry = tk.Text(room_id_frame, height=1, width=25, relief=tk.SUNKEN, 
                            font=("微软雅黑", 9), wrap=tk.NONE)
    room_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
    
    # API设置
    api_frame = ttk.Frame(room_settings_inner)
    api_frame.pack(fill=tk.X, pady=(6, 0))
    
    api_label = ttk.Label(api_frame, text="API网址:")
    api_label.pack(side=tk.LEFT, anchor="w")
    
    api_var = tk.StringVar(value="https://api.live.bilibili.com/room/v1/Room/room_init?id=")
    api_entry = ttk.Entry(api_frame, textvariable=api_var, width=30, font=("微软雅黑", 9))
    api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
    
    def restore_default_api():
        default_api = "https://api.live.bilibili.com/room/v1/Room/room_init?id="
        api_var.set(default_api)
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END,
                         time.strftime("%m-%d %H:%M:%S", time.localtime()) + '   '
                         + "已恢复默认API网址" + '\n')
        info_text.config(state=tk.DISABLED)
        info_text.see(tk.END)
    
    restore_api_btn = ttk.Button(api_frame, text="默认", width=8,
                                command=restore_default_api, bootstyle="secondary-outline")
    restore_api_btn.pack(side=tk.RIGHT)
    
    # 直播间状态
    table_frame = ttk.LabelFrame(root, text="直播间状态")
    table_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
    
    table_inner = ttk.Frame(table_frame)
    table_inner.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)
    
    table_container = ttk.Frame(table_inner)
    table_container.pack(fill=tk.BOTH, expand=True)
    
    table_scrollbar = ttk.Scrollbar(table_container, bootstyle="round")
    table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    tree = ttk.Treeview(
        table_container,
        columns=('主播', '房间号', '直播状态'),
        show='headings',
        height=5,
        yscrollcommand=table_scrollbar.set,
        selectmode='none'
    )
    
    column_width = 105
    
    tree.column('主播', width=column_width, minwidth=column_width, stretch=False, anchor='center')
    tree.column('房间号', width=column_width, minwidth=column_width, stretch=False, anchor='center')
    tree.column('直播状态', width=column_width, minwidth=column_width, stretch=False, anchor='center')
    
    tree.heading('主播', text='主播', anchor='center')
    tree.heading('房间号', text='房间号', anchor='center')
    tree.heading('直播状态', text='直播状态', anchor='center')
    
    style = ttk.Style()
    style.configure("Treeview", 
                    rowheight=25,
                    borderwidth=1,
                    relief="solid")
    style.map('Treeview', background=[('selected', '#f0f0f0')], foreground=[('selected', 'black')])
    
    def disable_tree_resize(event):
        if tree.identify_region(event.x, event.y) == "separator":
            return "break"
    
    tree.bind('<Button-1>', disable_tree_resize)
    tree.bind('<B1-Motion>', disable_tree_resize)
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    table_scrollbar.config(command=tree.yview)
    
    tree.configure(xscrollcommand=None)
    
    rowdata = []
    streamer_info = {}
    api = "https://api.live.bilibili.com/room/v1/Room/room_init?id="
    
    # 运行日志
    log_frame = ttk.LabelFrame(root, text="运行日志")
    log_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 8))
    
    log_inner = ttk.Frame(log_frame)
    log_inner.pack(padx=2, pady=2, fill=tk.BOTH, expand=True)
    
    info_scr = ttk.Scrollbar(log_inner, bootstyle="round")
    info_text = tk.Text(log_inner, height=5, bd=1,
                        font=tkfont.Font(family="Microsoft YaHei", size=9),
                        yscrollcommand=info_scr.set, state=tk.DISABLED,
                        wrap=tk.WORD)
    info_scr.config(command=info_text.yview)
    info_scr.pack(side=tk.RIGHT, fill=tk.Y)
    info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    if not os.path.exists(config_path):
        default_config = """api=https://api.live.bilibili.com/room/v1/Room/room_init?id=
roomID=
timeInterval=60
autoJump=0
autoListen=0
autoStartListen=0
autoStart=0"""
        with open(config_path, 'w') as f:
            f.write(default_config)
    
    load_settings()
    load_table_data()
    
    # 托盘菜单
    menu = (MenuItem('显示', show_window, default=True), 
            MenuItem('关于', show_about_window),
            Menu.SEPARATOR, 
            MenuItem('退出', quit_window))
    icon = pystray.Icon("bili_live_notification", icon_image, "Re：B站开播提醒", menu)
    
    root.protocol('WM_DELETE_WINDOW', quit_window)
    threading.Thread(target=icon.run, name="stray", daemon=True).start()
    
    pause_event = threading.Event()
    wait_event = threading.Event()
    
    root.after(100, delayed_startup)
    
    root.mainloop()
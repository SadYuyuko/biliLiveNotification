# Re: BiliLiveNotification
## B站直播开播提醒 - 重制版
[exe单文件](https://github.com/SadYuyuko/biliLiveNotification/releases/download/v1.0/Re.BiliLiveNotification.exe)  

新增功能：  
1.使用计划任务开机自启  
2.自动跳转浏览器  
3.自动开始检测  
4.重置UI删除二级菜单，直播间状态上下滑动  
5.修改.ini配置文件至C:\Users\用户名\.ReBiliLiveNotification\ReBLN.ini  
6.直播通知改为弹窗提醒，弹窗10分钟后未点击自动关闭  
7.删除启动通知，因为系统原生推送会留下一长串通知记录...  
8.单实例启动  
9.自定义API（好像用不到...）  

自动检测逻辑：关闭前如果没有手动停止检测，下次启动时将会自动开始检测，用于搭配开机自启，配置文件中使用autoStartListen=0/1控制  

移动exe单文件位置后若无法启动，请删除配置文件目录下ReBLN.lock，此为单实例锁标记防止多开bug  

修改了关闭逻辑，现在点击X是直接关闭，退出按键改成了隐藏到托盘  
原图标打包不进来，用ai画了个新的（软件也是用ds 3.2手搓的XD）  

## 软件界面  
<img width="400" height="606" alt="sshot-2026-02-11-16-07-00" src="https://github.com/user-attachments/assets/e233c8e8-52d4-4d6c-b45d-a42a9756f865" />  

## 通知弹窗  
<img width="400" height="280" alt="sshot-2026-02-11-16-06-04" src="https://github.com/user-attachments/assets/cad2897a-b9de-4b7a-aec4-6e8032afb577" />  

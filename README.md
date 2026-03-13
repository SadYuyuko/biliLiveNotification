# Re: BiliLiveNotification
## B站直播开播提醒 - 重制版
[exe单文件](https://github.com/SadYuyuko/biliLiveNotification/releases/download/v1.1/Re.BiliLiveNotification.exe)  

修改内容：  
1.使用计划任务开机自启  
2.自动跳转浏览器  
3.自动开始检测  
4.删除二级菜单，直播间列表上下滑动  
5.将.ini配置文件存放至`C:\Users\用户名\.ReBiliLiveNotification\ReBLN.ini`  
6.交换关闭程序和隐藏到托盘    
7.删除启动通知，因为系统原生推送会留下一长串通知记录...  
8.单实例启动  
9.自定义API（好像用不到...）  

自动检测逻辑：程序关闭前如果没有手动停止检测，下次启动时将会自动开始检测，用于搭配开机自启，配置文件中使用autoStartListen=0/1控制    
原图标打包不进来，用ai画了个新的 

注意：  
1.设置开机自启需要以管理员运行，移动.exe位置后要重新设置开机自启  
2.若无法再次启动，删除配置目录下ReBLN.lock，此为单实例锁标记防止多开bug  
3.输入房间号后要保存设置才会加入检测  
4.直播通知弹窗默认10分钟后未点击自动关闭  

## 软件界面  
<img width="300" height="455" alt="sshot-2026-02-11-16-07-00" src="https://github.com/user-attachments/assets/e233c8e8-52d4-4d6c-b45d-a42a9756f865" />  

## 通知弹窗  
<img width="250" height="175" alt="sshot-2026-02-11-16-06-04" src="https://github.com/user-attachments/assets/cad2897a-b9de-4b7a-aec4-6e8032afb577" />  

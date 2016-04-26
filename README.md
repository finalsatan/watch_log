# watch_log
watch log at back-end, using websocket of tornado

后台日志的监控程序，使用了tornado的websocket，后台使用tail -f命令实时监控日志内容，并通过websocket推送到
前端。

也可以接受前台发送的消息，并解析命令，并执行

from threading import Thread
import bot
import slack_watcher
import clickup_monitor

if __name__ == "__main__":
    Thread(target=bot.bot.polling, kwargs={'none_stop': True}).start()
    Thread(target=slack_watcher.run).start()
    Thread(target=clickup_monitor.run).start()

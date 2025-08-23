import os
import time
import telebot
from google_logger import log_message
from notifier import send_startup_status
from storage import set_slack_oldest_days, set_slack_oldest_ts, set_clickup_since_days, set_clickup_since_ms, propose_cleanup, soft_delete_threads
from config import IMPORTANT_SLACK_CHANNEL_BUGS

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = None

PAGE_SIZE = 10


def _safe_text(message) -> str:
    try:
        return getattr(message, 'text', None) or getattr(message, 'caption', None) or ""
    except Exception:
        return ""


def _fmt_ts(tsf: float) -> str:
    try:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(tsf)))
    except Exception:
        return str(tsf)


def _unique_channels() -> list:
    props = propose_cleanup()
    chans = []
    for c in props.get('candidates', []):
        name = c.get('channel') or ''
        if name and name not in chans:
            chans.append(name)
    return chans


def _filter_candidates(channel_filter: str | None, rcmin: int | None):
    props = propose_cleanup()
    cands = props.get('candidates', [])
    if channel_filter and channel_filter != '*':
        cands = [c for c in cands if c.get('channel') == channel_filter]
    if rcmin is not None:
        try:
            rcmin_i = int(rcmin)
            cands = [c for c in cands if int(c.get('reply_count', 0)) >= rcmin_i]
        except Exception:
            pass
    return cands


def register_handlers(b: telebot.TeleBot) -> None:
    @b.message_handler(commands=['start'])
    def handle_start(message):
        try:
            b.reply_to(message, "Привет! Я готов работать.")
        except Exception as e:
            print(f"[bot] reply error /start: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error /start: {e}")

    @b.message_handler(commands=['ping'])
    def handle_ping(message):
        try:
            b.reply_to(message, "👋 Я здесь. Готов работать.")
        except Exception as e:
            print(f"[bot] reply error /ping: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error /ping: {e}")

    @b.message_handler(commands=['ingest'])
    def handle_ingest(message):
        try:
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup()
            kb.row_width = 2
            kb.add(
                InlineKeyboardButton(text="Slack: 1д", callback_data="ingest:slack:1"),
                InlineKeyboardButton(text="Slack: 3д", callback_data="ingest:slack:3"),
            )
            kb.add(
                InlineKeyboardButton(text="Slack: 7д", callback_data="ingest:slack:7"),
                InlineKeyboardButton(text="Slack: 30д", callback_data="ingest:slack:30"),
            )
            kb.add(
                InlineKeyboardButton(text="ClickUp: 7д", callback_data="ingest:clickup:7"),
                InlineKeyboardButton(text="ClickUp: 14д", callback_data="ingest:clickup:14"),
            )
            kb.add(
                InlineKeyboardButton(text="ClickUp: 30д", callback_data="ingest:clickup:30"),
                InlineKeyboardButton(text="Отмена", callback_data="ingest:cancel"),
            )
            b.send_message(message.chat.id, "Выберите период для чтения:", reply_markup=kb)
        except Exception as e:
            b.reply_to(message, f"Ошибка: {e}")

    @b.callback_query_handler(func=lambda c: c.data and c.data.startswith('ingest:'))
    def on_ingest_click(call):
        try:
            parts = call.data.split(':')
            action = parts[1]
            if action == 'cancel':
                b.answer_callback_query(call.id, "Отменено")
                b.edit_message_text("Отменено", chat_id=call.message.chat.id, message_id=call.message.message_id)
                return
            target = parts[1]
            days = int(parts[2])
            if target == 'slack':
                set_slack_oldest_days(days)
                b.answer_callback_query(call.id, f"Slack: {days}д")
            elif target == 'clickup':
                set_clickup_since_days(days)
                b.answer_callback_query(call.id, f"ClickUp: {days}д")
            b.edit_message_text(f"Период установлен: {target} {days} дней", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            b.answer_callback_query(call.id, f"Ошибка: {e}")

    @b.message_handler(commands=['cleanup'])
    def handle_cleanup(message):
        try:
            props = propose_cleanup()
            count = props.get('count', 0)
            if count == 0:
                b.reply_to(message, "Нет кандидатов на очистку")
                return
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(text="Удалить всё", callback_data="cleanup:all"))
            # preset filter to bugs channel
            kb.add(InlineKeyboardButton(text="Удалить выборочно", callback_data=f"cleanup:select:0:{IMPORTANT_SLACK_CHANNEL_BUGS}:0"))
            kb.add(InlineKeyboardButton(text="Отмена", callback_data="cleanup:cancel"))
            b.send_message(message.chat.id, f"Найдено кандидатов: {count}. Выберите действие:", reply_markup=kb)
        except Exception as e:
            b.reply_to(message, f"Ошибка: {e}")

    def _render_select_page(chat_id, message_id, page, chan_filter, rcmin):
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        props = propose_cleanup()
        cands = _filter_candidates(chan_filter, rcmin)
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = cands[start:end]
        kb = InlineKeyboardMarkup()
        # Filters row
        kb.add(InlineKeyboardButton(text=f"Канал: {chan_filter}", callback_data=f"cleanup:cyclechan:{page}:{chan_filter}:{rcmin}"))
        kb.add(InlineKeyboardButton(text=f"Мин. ответы: {rcmin}", callback_data=f"cleanup:cyclerc:{page}:{chan_filter}:{rcmin}"))
        # Items
        for c in page_items:
            # mark mentions with a dot
            mention_mark = " • @" if c.get('mention_count', 0) else ''
            label = f"#{c['channel']}{mention_mark} | {_fmt_ts(c['last_ts'])} | repl:{c.get('reply_count',0)} len:{c.get('thread_len',0)}"
            kb.add(InlineKeyboardButton(text=label, callback_data=f"cleanup:item:{c['channel_id']}:{c['thread_ts']}:{page}:{chan_filter}:{rcmin}"))
        # Nav
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cleanup:page:{page-1}:{chan_filter}:{rcmin}"))
        if end < len(cands):
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cleanup:page:{page+1}:{chan_filter}:{rcmin}"))
        if nav:
            kb.row(*nav)
        kb.add(InlineKeyboardButton(text="Готово", callback_data="cleanup:done"))
        kb.add(InlineKeyboardButton(text="Отмена", callback_data="cleanup:cancel"))
        b.edit_message_text("Выберите треды для удаления:", chat_id=chat_id, message_id=message_id, reply_markup=kb)

    @b.callback_query_handler(func=lambda c: c.data and c.data.startswith('cleanup:'))
    def on_cleanup_click(call):
        try:
            parts = call.data.split(':')
            action = parts[1]
            if action == 'all':
                props = propose_cleanup()
                keys = [{"thread_ts": c["thread_ts"], "channel_id": c["channel_id"]} for c in props.get('candidates', [])]
                soft_delete_threads(keys)
                b.answer_callback_query(call.id, "Удалено в архив")
                b.edit_message_text("✅ Перемещено в архив. Будет удалено через 7 дней.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            elif action == 'select':
                page = int(parts[2]) if len(parts) > 2 else 0
                chan_filter = parts[3] if len(parts) > 3 else '*'
                rcmin = int(parts[4]) if len(parts) > 4 else 0
                _render_select_page(call.message.chat.id, call.message.message_id, page, chan_filter, rcmin)
            elif action == 'page':
                page = int(parts[2])
                chan_filter = parts[3] if len(parts) > 3 else '*'
                rcmin = int(parts[4]) if len(parts) > 4 else 0
                _render_select_page(call.message.chat.id, call.message.message_id, page, chan_filter, rcmin)
            elif action == 'item':
                ch_id = parts[2]
                th_ts = parts[3]
                page = int(parts[4]) if len(parts) > 4 else 0
                chan_filter = parts[5] if len(parts) > 5 else '*'
                rcmin = int(parts[6]) if len(parts) > 6 else 0
                soft_delete_threads([{ "thread_ts": th_ts, "channel_id": ch_id }])
                b.answer_callback_query(call.id, "Удалено в архив")
                _render_select_page(call.message.chat.id, call.message.message_id, page, chan_filter, rcmin)
            elif action == 'cyclechan':
                page = int(parts[2])
                chan_filter = parts[3]
                rcmin = int(parts[4]) if len(parts) > 4 else 0
                chans = ['*'] + _unique_channels()
                try:
                    idx = chans.index(chan_filter)
                except ValueError:
                    idx = 0
                next_chan = chans[(idx + 1) % len(chans)] if chans else '*'
                _render_select_page(call.message.chat.id, call.message.message_id, page, next_chan, rcmin)
                b.answer_callback_query(call.id)
            elif action == 'cyclerc':
                page = int(parts[2])
                chan_filter = parts[3]
                rcmin = int(parts[4]) if len(parts) > 4 else 0
                options = [0, 1, 3, 5]
                try:
                    idx = options.index(rcmin)
                except ValueError:
                    idx = 0
                next_rc = options[(idx + 1) % len(options)]
                _render_select_page(call.message.chat.id, call.message.message_id, page, chan_filter, next_rc)
                b.answer_callback_query(call.id)
            elif action == 'done':
                b.answer_callback_query(call.id, "Готово")
                b.edit_message_text("✅ Выбранные треды перемещены в архив.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            elif action == 'cancel':
                b.answer_callback_query(call.id, "Отменено")
                b.edit_message_text("Отменено", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            b.answer_callback_query(call.id, f"Ошибка: {e}")

    @b.message_handler(func=lambda message: True)
    def echo_message(message):
        text = _safe_text(message)
        try:
            if text:
                b.reply_to(message, f"Ты сказал: {text}")
            else:
                b.reply_to(message, "Принял сообщение")
        except Exception as e:
            print(f"[bot] reply error echo: {e}")
        try:
            log_message(message)
        except Exception as e:
            print(f"[bot] log error echo: {e}")


def init_bot():
    global bot
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN не задан — Telegram бот отключён")
        bot = None
        return
    try:
        b = telebot.TeleBot(TELEGRAM_TOKEN)
        try:
            b.remove_webhook()
        except Exception:
            pass
        register_handlers(b)
        bot = b
    except Exception as e:
        print(f"Не удалось инициализировать Telegram бот: {e}")
        bot = None


def run_polling():
    if bot is None:
        print("Telegram бот не запущен (нет токена или ошибка инициализации)")
        return
    backoff_seconds = 5
    while True:
        try:
            print("Бот запущен...")
            send_startup_status()
            bot.polling(none_stop=True, interval=0, timeout=60)
            backoff_seconds = 5
        except Exception as e:
            is_api_exc = hasattr(telebot, 'apihelper') and isinstance(e, getattr(telebot.apihelper, 'ApiTelegramException', Exception))
            if is_api_exc and getattr(e, 'error_code', None) == 409:
                print("[Telegram] 409 Conflict: другой инстанс getUpdates. Ретраю позже...")
                time.sleep(min(backoff_seconds, 300))
                backoff_seconds = min(backoff_seconds * 2, 300)
                continue
            print(f"Ошибка в polling: {e}")
            time.sleep(min(backoff_seconds, 60))
            backoff_seconds = min(backoff_seconds * 2, 60)


init_bot()

if __name__ == "__main__":
    run_polling()
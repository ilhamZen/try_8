"""Neonize send/reply I/O primitives."""
import logging
import os
import time
from neonize.utils import build_jid
from neonize.utils.message import extract_text
import config
from core.utils import _strip_device, ensure_dir
def _ensure_jid_obj(value):
    try:
        from neonize.proto.Neonize_pb2 import JID
        if isinstance(value, JID):
            return value
        if isinstance(value, str):
            v = _strip_device(value)
            if "@" in v:
                user, srv = v.rsplit("@", 1)
                return JID(User=user, Server=srv, Device=0, RawAgent=0, Integrator=0, IsEmpty=False)
            return build_jid(v, "s.whatsapp.net")
        return value
    except Exception:
        return value
def safe_send_text(client, jid, text):
    try:
        return client.send_message(_ensure_jid_obj(jid), text=text)
    except Exception as e:
        logging.error(f"[TEXT] {e}")
        return None
def safe_reply(client, text, quoted, jid=None):
    try:
        return client.reply_message(text, quoted)
    except Exception as e:
        logging.error(f"[REPLY] {e}")
        if jid is not None:
            return safe_send_text(client, jid, text)
        return None
def safe_send_image(client, jid, path_or_bytes, caption=""):
    jo = _ensure_jid_obj(jid)
    try:
        data = bytes(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, "rb").read()
    except Exception:
        return None
    try:
        return client.send_message(jo, message=client.build_image_message(data, caption=caption))
    except TypeError:
        try:
            return client.send_message(jo, message=client.build_image_message(data))
        except Exception:
            pass
    except Exception:
        pass
    return None
def safe_send_sticker(client, jid, path_or_bytes):
    jo = _ensure_jid_obj(jid)
    try:
        if isinstance(path_or_bytes, (bytes, bytearray)):
            data = bytes(path_or_bytes)
        else:
            with open(path_or_bytes, "rb") as f:
                data = f.read()
    except Exception as e:
        logging.error(f"[STICKER] read: {e}")
        return None
    send_sticker = getattr(client, "send_sticker", None)
    if callable(send_sticker):
        try:
            if isinstance(path_or_bytes, str):
                return send_sticker(jo, path_or_bytes)
            ensure_dir(config.MEDIA_DIR)
            tmp = os.path.join(config.MEDIA_DIR, f"stk_{int(time.time()*1000)}.webp")
            with open(tmp, "wb") as f:
                f.write(data)
            return send_sticker(jo, tmp)
        except Exception as e:
            logging.warning(f"[STICKER] send_sticker fail: {e}")
    build_fn = getattr(client, "build_sticker_message", None)
    if callable(build_fn):
        try:
            msg = build_fn(data)
            return client.send_message(jo, message=msg)
        except TypeError:
            try:
                msg = build_fn(sticker=data)
                return client.send_message(jo, message=msg)
            except Exception as e:
                logging.warning(f"[STICKER] build_sticker fail: {e}")
        except Exception as e:
            logging.warning(f"[STICKER] build_sticker fail: {e}")
    logging.warning("[STICKER] fallback to image")
    return safe_send_image(client, jid, data)
def safe_send_audio(client, jid, path, caption="", ptt=False):
    jo = _ensure_jid_obj(jid)
    if not os.path.exists(path):
        return None
    if hasattr(client, "send_audio"):
        for _ in range(2):
            try:
                r = client.send_audio(jo, path)
                if r:
                    return r
            except Exception:
                time.sleep(0.3)
    return None
def safe_send_video(client, jid, path, caption=""):
    jo = _ensure_jid_obj(jid)
    try:
        data = open(path, "rb").read()
    except Exception:
        return None
    try:
        return client.send_message(jo, message=client.build_video_message(data, caption=caption))
    except TypeError:
        try:
            return client.send_message(jo, message=client.build_video_message(data))
        except Exception:
            pass
    except Exception:
        pass
    return None
def get_message_text(msg):
    try:
        t = extract_text(msg.Message)
    except Exception:
        t = ""
    return t or ""

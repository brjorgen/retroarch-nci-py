import socket
import time
from enum import Enum, auto


class NCICommand(Enum):
    VERSION = auto()
    GET_STATUS = auto()
    GET_CONFIG_PARAM = auto()
    SHOW_MESG = auto()
    SET_SHADER = auto()
    READ_CORE_MEMORY = auto()
    WRITE_CORE_MEMORY = auto()
    LOAD_STATE_SLOT = auto()
    PLAY_REPLAY_SLOT = auto()
    MENU_TOGGLE = auto()
    QUIT = auto()
    CLOSE_CONTENT = auto()
    RESET = auto()
    FAST_FORWARD = auto()
    FAST_FORWARD_HOLD = auto()
    SLOWMOTION = auto()
    SLOWMOTION_HOLD = auto()
    REWIND = auto()
    PAUSE_TOGGLE = auto()
    FRAMEADVANCE = auto()
    MUTE = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    LOAD_STATE = auto()
    SAVE_STATE = auto()
    STATE_SLOT_PLUS = auto()
    STATE_SLOT_MINUS = auto()
    PLAY_REPLAY = auto()
    RECORD_REPLAY = auto()
    HALT_REPLAY = auto()
    REPLAY_SLOT_PLUS = auto()
    REPLAY_SLOT_MINUS = auto()
    DISK_EJECT_TOGGLE = auto()
    DISK_NEXT = auto()
    DISK_PREV = auto()
    SHADER_TOGGLE = auto()
    SHADER_NEXT = auto()
    SHADER_PREV = auto()
    CHEAT_TOGGLE = auto()
    CHEAT_INDEX_PLUS = auto()
    CHEAT_INDEX_MINUS = auto()
    SCREENSHOT = auto()
    RECORDING_TOGGLE = auto()
    STREAMING_TOGGLE = auto()
    GRAB_MOUSE_TOGGLE = auto()
    GAME_FOCUS_TOGGLE = auto()
    FULLSCREEN_TOGGLE = auto()
    UI_COMPANION_TOGGLE = auto()
    VRR_RUNLOOP_TOGGLE = auto()
    RUNAHEAD_TOGGLE = auto()
    PREEMPT_TOGGLE = auto()
    FPS_TOGGLE = auto()
    STATISTICS_TOGGLE = auto()
    AI_SERVICE = auto()
    NETPLAY_PING_TOGGLE = auto()
    NETPLAY_HOST_TOGGLE = auto()
    NEPLAY_GAME_WATCH = auto()
    NETPLAY_PLAYER_CHAT = auto()
    NETPLAY_FADE_CHAT_TOGGLE = auto()
    MENU_UP = auto()
    MENU_DOWN = auto()
    MENU_LEFT = auto()
    MENU_RIGHT = auto()
    MENU_A = auto()
    MENU_B = auto()
    OVERLAY_NEXT = auto()
    OSK = auto()


class RetroArchNCI:
    """
    Class abstracting the retroarch NCI.
    Useful for bots, watchers, etc.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 55355, timeout: float = 1.0):
        """
        host: address of RetroArch NCI UDP server
        port: port (default 55355)
        timeout: socket recv timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    # =====================================
    # low-level UDP send/receive
    # =====================================
    def _send(self, msg: str, expect_response: bool = True):
        """
        Low-level UDP send. Encodes msg as ASCII and returns decoded response
        or None on timeout / error. Caller should pass full command string.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.sendto(msg.encode("ascii"), (self.host, self.port))

            if not expect_response:
                return None

            data, _ = sock.recvfrom(4096)
            return data.decode("ascii", errors="replace").strip()

        except socket.timeout:
            return None

        except Exception:
            return None

        finally:
            sock.close()

    # =====================================
    # public generic command helpers
    # =====================================
    def cmd(self, command: NCICommand, *args, expect_response: bool = True):
        """
        Build a command string from an NCICommand enum and optional args,
        then send via _send().
        Example: cmd(NCICommand.SHOW_MESG, "Hello", 2000)
        """
        cmd_name = command.name

        if args:
            full = f"{cmd_name} " + " ".join(map(str, args))

        else:
            full = cmd_name

        return self._send(full, expect_response=expect_response)

    def send_nci_command(self, cmd_or_str, *args, expect_response: bool = True):
        """
        Public wrapper that accepts either an NCICommand or a raw string command name.
        send_nci_command(NCICommand.VERSION)
        send_nci_command("VERSION")
        send_nci_command(NCICommand.SHOW_MESG, "Hello", 2000)
        """
        if isinstance(cmd_or_str, NCICommand):
            return self.cmd(cmd_or_str, *args, expect_response=expect_response)

        else:
            msg = str(cmd_or_str)

            if args:
                msg += " " + " ".join(map(str, args))

            return self._send(msg, expect_response=expect_response)

    # =====================================
    # wait for NCI to be ready
    # =====================================
    def wait_for_ready(self, timeout_sec: float = 10.0, poll_interval: float = 0.25) -> bool:
        """
        Polls VERSION until RetroArch NCI responds or timeout occurs.
        Returns True if ready, False if timed out.
        """
        start = time.time()
        while time.time() - start < timeout_sec:
            resp = self.send_nci_command(NCICommand.VERSION)

            if resp is not None:
                return True

            time.sleep(poll_interval)

        return False

    # =====================================
    # READ/WRITE memory helpers
    # =====================================
    def read_core_memory(self, address: int, size: int = 1):
        """
        Read memory using READ_CORE_MEMORY <address_hex> <size>
        - address: integer address
        - size: number of bytes to read
        Returns:
            little-endian integer composed from returned bytes, or None on error.
        RetroArch response on success:
            READ_CORE_MEMORY <address> <byte1> <byte2> ...
        On failure: READ_CORE_MEMORY <address> -1
        """
        # build address in uppercase hex without 0x
        cmd = f"READ_CORE_MEMORY {address:X} {size}"
        resp = self._send(cmd, expect_response=True)
        if resp is None:
            return None

        parts = resp.split()

        if len(parts) < 3:
            return None

        cmd_name, addr_str, *byte_parts = parts

        # check failure ("-1")
        if len(byte_parts) == 1 and byte_parts[0] == "-1":
            return None

        try:
            val = 0
            # assemble little-endian integer
            for i, b in enumerate(byte_parts):
                val |= int(b, 16) << (8 * i)
            return val

        except ValueError:
            return None

    def write_core_memory(self, address: int, bytes_list):
        """
        Write memory via: WRITE_CORE_MEMORY <address_hex> <byte1> <byte2> ...
        bytes_list may be iterable of ints (0-255).
        Returns response string or None on timeout/error.
        """
        hex_bytes = " ".join(f"{b:02X}" for b in bytes_list)
        cmd = f"WRITE_CORE_MEMORY {address:X} {hex_bytes}"
        return self._send(cmd, expect_response=True)

    # =====================================
    # Parameterized commands
    # =====================================
    def get_config_param(self, param: str):
        return self.cmd(NCICommand.GET_CONFIG_PARAM, param)

    def show_mesg(self, message: str, duration_ms: int = None):
        if duration_ms is not None:
            return self.cmd(NCICommand.SHOW_MESG, message, duration_ms)

        return self.cmd(NCICommand.SHOW_MESG, message)

    def set_shader(self, shader_path: str):
        return self.cmd(NCICommand.SET_SHADER, shader_path)

    def load_state_slot(self, slot: int):
        return self.cmd(NCICommand.LOAD_STATE_SLOT, slot)

    def play_replay_slot(self, slot: int):
        return self.cmd(NCICommand.PLAY_REPLAY_SLOT, slot)

    def netplay_player_chat(self, message: str):
        return self.cmd(NCICommand.NETPLAY_PLAYER_CHAT, message)

    # =====================================
    # Single-word command helpers
    # =====================================
    def version(self): return self.cmd(NCICommand.VERSION)
    def get_status(self): return self.cmd(NCICommand.GET_STATUS)
    def menu_toggle(self): return self.cmd(NCICommand.MENU_TOGGLE)
    def quit(self): return self.cmd(NCICommand.QUIT)
    def close_content(self): return self.cmd(NCICommand.CLOSE_CONTENT)
    def reset(self): return self.cmd(NCICommand.RESET)
    def fast_forward(self): return self.cmd(NCICommand.FAST_FORWARD)
    def fast_forward_hold(self): return self.cmd(NCICommand.FAST_FORWARD_HOLD)
    def slowmotion(self): return self.cmd(NCICommand.SLOWMOTION)
    def slowmotion_hold(self): return self.cmd(NCICommand.SLOWMOTION_HOLD)
    def rewind(self): return self.cmd(NCICommand.REWIND)
    def pause_toggle(self): return self.cmd(NCICommand.PAUSE_TOGGLE)
    def frameadvance(self): return self.cmd(NCICommand.FRAMEADVANCE)
    def mute(self): return self.cmd(NCICommand.MUTE)
    def volume_up(self): return self.cmd(NCICommand.VOLUME_UP)
    def volume_down(self): return self.cmd(NCICommand.VOLUME_DOWN)
    def load_state(self): return self.cmd(NCICommand.LOAD_STATE)
    def save_state(self): return self.cmd(NCICommand.SAVE_STATE)
    def state_slot_plus(self): return self.cmd(NCICommand.STATE_SLOT_PLUS)
    def state_slot_minus(self): return self.cmd(NCICommand.STATE_SLOT_MINUS)
    def play_replay(self): return self.cmd(NCICommand.PLAY_REPLAY)
    def record_replay(self): return self.cmd(NCICommand.RECORD_REPLAY)
    def halt_replay(self): return self.cmd(NCICommand.HALT_REPLAY)
    def replay_slot_plus(self): return self.cmd(NCICommand.REPLAY_SLOT_PLUS)
    def replay_slot_minus(self): return self.cmd(NCICommand.REPLAY_SLOT_MINUS)
    def disk_eject_toggle(self): return self.cmd(NCICommand.DISK_EJECT_TOGGLE)
    def disk_next(self): return self.cmd(NCICommand.DISK_NEXT)
    def disk_prev(self): return self.cmd(NCICommand.DISK_PREV)
    def shader_toggle(self): return self.cmd(NCICommand.SHADER_TOGGLE)
    def shader_next(self): return self.cmd(NCICommand.SHADER_NEXT)
    def shader_prev(self): return self.cmd(NCICommand.SHADER_PREV)
    def cheat_toggle(self): return self.cmd(NCICommand.CHEAT_TOGGLE)
    def cheat_index_plus(self): return self.cmd(NCICommand.CHEAT_INDEX_PLUS)
    def cheat_index_minus(self): return self.cmd(NCICommand.CHEAT_INDEX_MINUS)
    def screenshot(self): return self.cmd(NCICommand.SCREENSHOT)
    def recording_toggle(self): return self.cmd(NCICommand.RECORDING_TOGGLE)
    def streaming_toggle(self): return self.cmd(NCICommand.STREAMING_TOGGLE)
    def grab_mouse_toggle(self): return self.cmd(NCICommand.GRAB_MOUSE_TOGGLE)
    def game_focus_toggle(self): return self.cmd(NCICommand.GAME_FOCUS_TOGGLE)
    def fullscreen_toggle(self): return self.cmd(NCICommand.FULLSCREEN_TOGGLE)
    def ui_companion_toggle(self): return self.cmd(NCICommand.UI_COMPANION_TOGGLE)
    def vrr_runloop_toggle(self): return self.cmd(NCICommand.VRR_RUNLOOP_TOGGLE)
    def runahead_toggle(self): return self.cmd(NCICommand.RUNAHEAD_TOGGLE)
    def preempt_toggle(self): return self.cmd(NCICommand.PREEMPT_TOGGLE)
    def fps_toggle(self): return self.cmd(NCICommand.FPS_TOGGLE)
    def statistics_toggle(self): return self.cmd(NCICommand.STATISTICS_TOGGLE)
    def ai_service(self): return self.cmd(NCICommand.AI_SERVICE)
    def netplay_ping_toggle(self): return self.cmd(NCICommand.NETPLAY_PING_TOGGLE)
    def netplay_host_toggle(self): return self.cmd(NCICommand.NETPLAY_HOST_TOGGLE)
    def neplay_game_watch(self): return self.cmd(NCICommand.NEPLAY_GAME_WATCH)
    def netplay_fade_chat_toggle(self): return self.cmd(NCICommand.NETPLAY_FADE_CHAT_TOGGLE)
    def menu_up(self): return self.cmd(NCICommand.MENU_UP)
    def menu_down(self): return self.cmd(NCICommand.MENU_DOWN)
    def menu_left(self): return self.cmd(NCICommand.MENU_LEFT)
    def menu_right(self): return self.cmd(NCICommand.MENU_RIGHT)
    def menu_a(self): return self.cmd(NCICommand.MENU_A)
    def menu_b(self): return self.cmd(NCICommand.MENU_B)
    def overlay_next(self): return self.cmd(NCICommand.OVERLAY_NEXT)
    def osk(self): return self.cmd(NCICommand.OSK)

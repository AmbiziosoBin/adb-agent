"""Media control: play/pause, camera, gallery, audio recording."""

import time

from .connection import get_device
from .utils import output, error, ok, audit_log


def cmd_play_pause(args):
    """Toggle play/pause for current media."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")
    audit_log("media play-pause")
    ok("Media play/pause toggled")


def cmd_next(args):
    """Next track."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_MEDIA_NEXT")
    audit_log("media next")
    ok("Next track")


def cmd_prev(args):
    """Previous track."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_MEDIA_PREVIOUS")
    audit_log("media prev")
    ok("Previous track")


def cmd_stop(args):
    """Stop media playback."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_MEDIA_STOP")
    audit_log("media stop")
    ok("Media stopped")


def cmd_camera(args):
    """Open camera for photo or video."""
    device = get_device(getattr(args, "device", None))
    mode = args.mode  # photo or video

    if mode == "photo":
        device.shell("am start -a android.media.action.STILL_IMAGE_CAMERA")
        ok("Camera opened (photo mode)")
    elif mode == "video":
        device.shell("am start -a android.media.action.VIDEO_CAMERA")
        ok("Camera opened (video mode)")
    else:
        error("Mode must be 'photo' or 'video'")
    audit_log(f"media camera {mode}")


def cmd_gallery(args):
    """View gallery / recent photos info."""
    device = get_device(getattr(args, "device", None))
    recent_n = int(getattr(args, "recent", 5))

    # List recent photos
    out = device.shell(
        f"ls -lt /sdcard/DCIM/Camera/ 2>/dev/null | head -{recent_n + 1}"
    ).output

    if out.strip():
        output("Recent photos/videos:")
        output(out.strip())
    else:
        # Try alternative paths
        out = device.shell(
            f"find /sdcard/DCIM /sdcard/Pictures -name '*.jpg' -o -name '*.png' -o -name '*.mp4' 2>/dev/null | sort -r | head -{recent_n}"
        ).output
        if out.strip():
            output("Recent media files:")
            output(out.strip())
        else:
            output("(no media files found in DCIM/Pictures)")

    audit_log(f"media gallery --recent {recent_n}")


def cmd_record_audio_start(args):
    """Start audio recording."""
    device = get_device(getattr(args, "device", None))
    filename = getattr(args, "filename", None) or "recording.m4a"

    # Use am recorder intent as fallback, or direct recording
    device.shell(f"am start -a android.provider.MediaStore.RECORD_SOUND")
    audit_log(f"media record-audio start {filename}")
    ok("Sound recorder opened")
    output("Note: Press record button in the app to start recording")


def cmd_record_audio_stop(args):
    """Stop audio recording."""
    device = get_device(getattr(args, "device", None))
    # Send media stop key
    device.shell("input keyevent KEYCODE_MEDIA_STOP")
    audit_log("media record-audio stop")
    ok("Recording stop signal sent")

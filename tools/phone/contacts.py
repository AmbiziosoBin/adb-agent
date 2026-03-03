"""Communication: phone calls, SMS, contacts management."""

import re

from .connection import get_device
from .utils import output, error, ok, audit_log


def cmd_call(args):
    """Make a phone call."""
    device = get_device(getattr(args, "device", None))
    number = args.number
    device.shell(f"am start -a android.intent.action.CALL -d tel:{number}")
    audit_log(f"call {number}")
    ok(f"Calling {number}")


def cmd_call_end(args):
    """End/hang up phone call."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_ENDCALL")
    audit_log("call end")
    ok("Call ended")


def cmd_call_accept(args):
    """Accept incoming call."""
    device = get_device(getattr(args, "device", None))
    device.shell("input keyevent KEYCODE_CALL")
    audit_log("call accept")
    ok("Call accepted")


def cmd_sms_send(args):
    """Send SMS."""
    device = get_device(getattr(args, "device", None))
    number = args.number
    content = args.content

    # Use am to send SMS via intent
    device.shell(
        f'am start -a android.intent.action.SENDTO -d sms:{number} '
        f'--es sms_body "{content}" --ez exit_on_sent true'
    )

    audit_log(f'sms send {number} "{content[:20]}..."')
    ok(f"SMS compose opened for {number}")
    output("Note: You may need to tap 'Send' button to actually send the SMS")


def cmd_sms_read(args):
    """Read SMS messages."""
    device = get_device(getattr(args, "device", None))
    count = int(getattr(args, "count", 5))
    from_number = getattr(args, "from_number", None)

    cmd = f"content query --uri content://sms/inbox --projection address:body:date --sort 'date DESC' | head -{count}"
    out = device.shell(cmd).output

    if not out.strip() or "No result" in out:
        output("(no SMS messages found)")
        output("Note: SMS reading requires proper permissions on the device")
        return

    for line in out.strip().split("\n"):
        if from_number and from_number not in line:
            continue
        # Parse content provider output
        addr_match = re.search(r'address=([^,]+)', line)
        body_match = re.search(r'body=([^,]+)', line)
        if addr_match and body_match:
            addr = addr_match.group(1).strip()
            body = body_match.group(1).strip()
            output(f"From: {addr}")
            output(f"  {body}")
            output("")

    audit_log(f"sms read count={count}")


def cmd_contacts_list(args):
    """List contacts."""
    device = get_device(getattr(args, "device", None))
    search = getattr(args, "search", None)

    cmd = "content query --uri content://contacts/phones/ --projection display_name:number"
    if search:
        cmd += f" | grep -i '{search}'"
    cmd += " | head -20"

    out = device.shell(cmd).output

    if not out.strip() or "No result" in out:
        output("(no contacts found)")
        output("Note: Contact reading requires proper permissions")
        return

    for line in out.strip().split("\n"):
        name_match = re.search(r'display_name=([^,]+)', line)
        num_match = re.search(r'number=([^,]+)', line)
        if name_match:
            name = name_match.group(1).strip()
            num = num_match.group(1).strip() if num_match else "N/A"
            output(f"{name}: {num}")

    audit_log(f"contacts list {search or ''}")


def cmd_contacts_add(args):
    """Add a contact."""
    device = get_device(getattr(args, "device", None))
    name = args.name
    number = args.number
    email = getattr(args, "email", None)

    intent = (
        f'am start -a android.intent.action.INSERT '
        f'-t vnd.android.cursor.dir/contact '
        f'--es name "{name}" --es phone "{number}"'
    )
    if email:
        intent += f' --es email "{email}"'

    device.shell(intent)
    audit_log(f"contacts add {name} {number}")
    ok(f"Contact add dialog opened for {name}")
    output("Note: You may need to confirm saving the contact")


def cmd_contacts_delete(args):
    """Delete a contact (opens contact for manual deletion)."""
    device = get_device(getattr(args, "device", None))
    query = args.query  # name or number

    # Search for the contact first
    out = device.shell(
        f"content query --uri content://contacts/phones/ "
        f"--projection display_name:number | grep -i '{query}'"
    ).output

    if not out.strip():
        error(f'Contact "{query}" not found')

    output(f"Found contact matching '{query}':")
    output(out.strip())
    output("Note: Direct contact deletion requires root. Use the Contacts app to delete.")

    # Open contacts app with search
    device.shell(
        f'am start -a android.intent.action.SEARCH '
        f'-t vnd.android.cursor.dir/contact --es query "{query}"'
    )
    audit_log(f"contacts delete {query}")

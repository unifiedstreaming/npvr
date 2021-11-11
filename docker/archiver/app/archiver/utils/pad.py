def pad(b64):
    # pad the base64 string in case it isn't properly padded
    if len(b64) % 4:
        pad = len(b64) + 4 - len(b64) % 4
    else:
        pad = len(b64)
    return f"{b64:=<{pad}}"

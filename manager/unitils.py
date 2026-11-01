###############################
# unitils.py - perus työkalut #
###############################

CODE_KEYWORDS = ("string ", "int ", "double ", "float ", "system.out")
CODE_SITES = ("stack", "overflow", "w3schools", "jetbrains", "code", "java", "c#", "c++",
              "python", "javascript", "programming")
NETTIX_SITES = ("nettiauto", "nettimarkkina", "nettimoto", "nettivene", "nettikone",
                "nettivaraosa", "nettivuokraus", "nettimokki", "nettikaravaani")


def _links(msg):
    return [w for w in msg.lower().split() if w.startswith(("http://", "https://"))]


# Tarkistaa sisältääkö viestissä koodia.
def isCode(msg):
    msg = msg.lower()
    if "```" in msg:
        return True
    if any(k in msg for k in CODE_KEYWORDS):
        return True
    return any(site in link for link in _links(msg) for site in CODE_SITES)


# Tarkistaa sisältääkö viestissä Nettix OY linkkejä.
def isNettiauto(msg):
    return any(site in link for link in _links(msg) for site in NETTIX_SITES)


def formatDuration(ms):
    """Milliseconds -> '12h 5m' / '5m 3s' / '42s'."""
    seconds = int(ms) // 1000
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


# Backwards-compatible name (the old function also took milliseconds despite its name).
convertSeconds = formatDuration
